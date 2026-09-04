/**
 * MCP Bridge Extension for pi
 *
 * 读取 ~/.pi/agent/mcp.ts（导出 mcpServers 的 TypeScript 配置），session_start 时
 * 自动连接所有非 lazy 的 MCP server，把工具注册成 pi 工具（由 /tools 统一开关）。
 *
 * 命令：
 * - /mcp         TUI 交互式开关面板（SettingsList 原地 toggle）；非 TUI 显示只读状态面板
 * - /mcp on|off <name> 命令式开关（兼容旧用法 /mcp <name> 等价于 on）
 * - off = 断开 client + 把该 server 的工具移出活跃集（pi.setActiveTools）
 * - 重新 on 时工具重新激活；无持久化，重启进程后恢复默认
 *
 * 支持 transport：stdio / http（Streamable HTTP）/ sse。
 * lazy: true 的 server 默认不启动，需手动开启。
 * lazyTools: true | string[] 工具级 lazy：工具正常注册但不进活跃集（模型不可见），
 *   用 /tools 手动开启。true = 该 server 全部工具；string[] = 仅列表中的
 *   （支持裸名或 server__tool 全名）。不配置则维持连接后全部 ON。
 * MCP_DEBUG=true pi --no-session 开启 Debug log
 */

import type { AgentToolResult, ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { getSettingsListTheme } from "@earendil-works/pi-coding-agent";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Box, Container, type SettingItem, SettingsList, Text } from "@earendil-works/pi-tui";

type AnySchema = Record<string, unknown>;
type Notify = (message: string, type?: "info" | "warning" | "error") => void;

interface McpServerConfig {
  type?: "stdio" | "http" | "sse";
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
  /** 默认 false: session 启动时不自动连接,通过 /mcp 手动开启 */
  lazy?: boolean;
  /** 工具级 lazy: true=全部工具默认 OFF; string[]=仅列表中的默认 OFF(裸名或 server__全名)。注册但不在活跃集,/tools 可开 */
  lazyTools?: boolean | string[];
}

interface McpConfig {
  mcpServers?: Record<string, McpServerConfig>;
}

const clients = new Map<string, Client>();
const registeredTools = new Set<string>();
/** 每个 server 注册的工具名列表（`${server}__${tool}`），off 时用于移出活跃集 */
const serverTools = new Map<string, string[]>();
type ConnectionStatus =
  | { state: "pending" }
  | { state: "connected"; tools: string[] }
  | { state: "failed"; error: string };
const connectionStatuses = new Map<string, ConnectionStatus>();
// 工具成功注册后默认显示 success；实际调用返回错误或抛异常后显示 fail。
const toolStatuses = new Map<string, "success" | "fail">();
const DEBUG_LOG = process.env.MCP_DEBUG === "true";
const log = (msg: string, ...args: unknown[]) => {
  if (DEBUG_LOG) console.log(`[mcp-bridge] ${msg}`, ...args);
};
const baseDir = dirname(fileURLToPath(import.meta.url));

const CONNECT_TIMEOUT_MS = 8000;
const LIST_TOOLS_TIMEOUT_MS = 8000;

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${label} 超时 (${ms}ms)`)), ms);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

function createTransport(cfg: McpServerConfig) {
  const type = cfg.type ?? (cfg.command ? "stdio" : "http");

  log("createTransport", {
    type,
    hasCommand: Boolean(cfg.command),
    hasUrl: Boolean(cfg.url),
    args: cfg.args ?? [],
  });

  if (type === "stdio") {
    if (!cfg.command) throw new Error("stdio server 缺少 command");
    // 合并关键环境变量，保证 bunx / node 等可被找到
    const env: Record<string, string> = {
      PATH: process.env.PATH ?? "",
      HOME: process.env.HOME ?? "",
      USER: process.env.USER ?? "",
      ...cfg.env,
    };
    return new StdioClientTransport({ command: cfg.command, args: cfg.args ?? [], env, stderr: "pipe" });
  }

  if (!cfg.url) throw new Error(`${type} server 缺少 url`);
  const url = new URL(cfg.url);
  const requestInit: RequestInit = cfg.headers ? { headers: cfg.headers } : {};

  if (type === "sse") return new SSEClientTransport(url, { requestInit });
  return new StreamableHTTPClientTransport(url, { requestInit });
}

/** 把 MCP 返回的 content 转成 pi 的 content 格式 */
function toPiContent(raw: unknown[]): AgentToolResult<{ isError: boolean }>["content"] {
  return raw.map((item): AgentToolResult<{ isError: boolean }>["content"][number] => {
    const c = item as Record<string, unknown>;
    switch (c.type) {
      case "text":
        return { type: "text", text: String(c.text ?? "") };
      case "image":
        return {
          type: "image",
          mimeType: String(c.mimeType ?? "image/*"),
          data: String(c.data ?? ""),
        };
      case "resource": {
        const res = (c.resource ?? {}) as Record<string, unknown>;
        return { type: "text", text: typeof res.text === "string" ? res.text : JSON.stringify(res) };
      }
      default:
        return { type: "text", text: JSON.stringify(c) };
    }
  });
}

/** 计算 server 应默认 OFF(注册但不进活跃集)的工具名集合 */
function resolveLazyTools(server: string, cfg: McpServerConfig | undefined): Set<string> {
  const conf = cfg?.lazyTools;
  if (!conf) return new Set<string>();
  const all = serverTools.get(server) ?? [];
  if (conf === true) return new Set(all);
  const wanted = new Set(conf.map((n) => (n.startsWith(`${server}__`) ? n : `${server}__${n}`)));
  return new Set(all.filter((n) => wanted.has(n)));
}

async function connectServer(pi: ExtensionAPI, name: string, cfg: McpServerConfig) {
  const existing = clients.get(name);
  if (existing) {
    log(`reuse existing client: ${name}`);
    return existing;
  }

  connectionStatuses.set(name, { state: "pending" });
  log(`connecting server: ${name}`, {
    type: cfg.type ?? (cfg.command ? "stdio" : "http"),
    command: cfg.command,
    args: cfg.args ?? [],
    url: cfg.url,
  });

  const client = new Client({ name: "pi-mcp-bridge", version: "1.0.0" }, { capabilities: {} });
  const transport = createTransport(cfg);

  if (transport instanceof StdioClientTransport) {
    transport.stderr?.on("data", (chunk) => {
      if (DEBUG_LOG) {
        const text = chunk.toString().trim();
        if (text) console.log(`[mcp-bridge:${name}:stderr] ${text}`);
      }
    });
  }

  await withTimeout(client.connect(transport), CONNECT_TIMEOUT_MS, `${name} connect`);
  log(`connected server: ${name}`);
  clients.set(name, client);

  const { tools } = await withTimeout(client.listTools(), LIST_TOOLS_TIMEOUT_MS, `${name} listTools`);
  log(`listTools success: ${name}`, { count: tools.length, tools: tools.map((tool) => tool.name) });

  serverTools.set(
    name,
    tools.map((tool) => `${name}__${tool.name}`),
  );
  for (const tool of tools) {
    const toolName = `${name}__${tool.name}`;
    if (registeredTools.has(toolName)) {
      // off 后重新 on：工具仍注册在 pi 中，跳过重复注册，激活由 enableServer 处理
      log(`skip duplicate tool: ${toolName}`);
      continue;
    }
    registeredTools.add(toolName);
    toolStatuses.set(toolName, "success");

    const schema: AnySchema = (tool.inputSchema as AnySchema) ?? { type: "object", properties: {} };

    log(`register tool: ${toolName}`);
    pi.registerTool({
      name: toolName,
      label: `${name}.${tool.name}`,
      description: `[${name}] ${tool.description ?? tool.name}`,
      // MCP inputSchema 本身就是 JSON Schema，与 typebox schema 运行时同构
      parameters: schema as never,
      async execute(_id, params) {
        log(`execute tool: ${toolName}`, { params });
        try {
          const result = await client.callTool({
            name: tool.name,
            arguments: (params ?? {}) as Record<string, unknown>,
          });
          const isError = Boolean(result.isError);
          toolStatuses.set(toolName, isError ? "fail" : "success");
          log(`tool result: ${toolName}`, { isError });
          const content = toPiContent((result.content as unknown[]) ?? []);
          return { content, details: { isError } };
        } catch (error) {
          toolStatuses.set(toolName, "fail");
          throw error;
        }
      },
    });
  }
  // 工具级 lazy: 注册后默认在活跃集,这里把 lazyTools 对应工具移出(模型不可见,/tools 可开)
  const lazySet = resolveLazyTools(name, cfg);
  if (lazySet.size > 0) {
    const currentActive = pi.getActiveTools();
    const next = currentActive.filter((n) => !lazySet.has(n));
    if (next.length !== currentActive.length) pi.setActiveTools(next);
    log(`lazyTools applied: ${name}`, { lazy: [...lazySet] });
  }
  connectionStatuses.set(name, { state: "connected", tools: tools.map((tool) => tool.name) });
  log(`✓ ${name}: 注册 ${tools.length} 个工具`);
  return client;
}

export default async function (pi: ExtensionAPI) {
  // 贡献本扩展自带的 skill,让 agent 在被问及 pi 的 MCP 实现时知道去哪找信息
  pi.on("resources_discover", () => ({
    skillPaths: [join(baseDir, "SKILL.md")],
  }));

  const configPath = join(homedir(), ".pi", "agent", "mcp.ts");

  log("extension loaded", {
    configPath,
    cwd: process.cwd(),
    mcpDebug: process.env.MCP_DEBUG,
  });

  let config: McpConfig;
  try {
    // Pi 运行在 Bun 中，动态导入会直接编译此 TypeScript 配置文件。
    const module = await import(pathToFileURL(configPath).href);
    config = (module.default ?? module) as McpConfig;
    log("config file loaded");
  } catch (error) {
    log(`未找到或无法解析 ${configPath}，跳过`, error);
    return;
  }

  const servers = Object.entries(config.mcpServers ?? {});
  for (const [name] of servers) connectionStatuses.set(name, { state: "pending" });
  log("parsed servers", { count: servers.length, names: servers.map(([name]) => name) });
  if (servers.length === 0) {
    log("mcp.ts 中没有配置任何 server");
    return;
  }

  // lazy server 启动标记: 开启前不连接; 通过 /mcp 交互面板或 /mcp on <name> 激活
  const active = new Set(servers.filter(([, cfg]) => !cfg.lazy).map(([name]) => name));
  let initPromise: Promise<void> | null = null;

  const ensureInitialized = (opts?: { only?: string; notify?: Notify }) => {
    const targets = opts?.only ? [opts.only] : servers.filter(([name]) => active.has(name)).map(([name]) => name);
    const pending = targets.filter((name) => !clients.has(name));
    if (initPromise && pending.length === 0) {
      log("ensureInitialized reuse existing promise");
      return initPromise;
    }
    log("ensureInitialized start", { targets, pending });
    const run = (async () => {
      for (const name of targets) {
        const cfg = servers.find(([n]) => n === name)?.[1];
        if (!cfg) continue;
        try {
          await connectServer(pi, name, cfg);
        } catch (err) {
          const error = err instanceof Error ? err.message : String(err);
          connectionStatuses.set(name, { state: "failed", error });
          const message = `✗ ${name} 连接失败`;
          log(`${message}: ${error}`, err);
          opts?.notify?.(message, "warning");
        }
      }
      log("ensureInitialized done");
    })();
    if (!initPromise || pending.length > 0) initPromise = run;
    return run;
  };

  /** 关闭 server: 断开 client 并把它的工具移出活跃集 */
  const disableServer = (name: string) => {
    clients.get(name)?.close().catch(() => {});
    clients.delete(name);
    active.delete(name);
    const tools = serverTools.get(name) ?? [...registeredTools].filter((n) => n.startsWith(`${name}__`));
    if (tools.length > 0) {
      const currentActive = pi.getActiveTools();
      pi.setActiveTools(currentActive.filter((n) => !tools.includes(n)));
    }
    connectionStatuses.set(name, { state: "pending" });
    log(`disabled server: ${name}`, { removedTools: tools.length });
  };

  /** 开启 server: 连接并把它的工具(重新)加入活跃集 */
  const enableServer = async (name: string, notify?: Notify) => {
    const cfg = servers.find(([n]) => n === name)?.[1];
    if (!cfg) {
      notify?.(`未配置 server: ${name}`, "warning");
      return;
    }
    if (clients.has(name)) {
      notify?.(`${name} 已连接`);
      return;
    }
    active.add(name);
    connectionStatuses.set(name, { state: "pending" });
    await ensureInitialized({ only: name, notify });
    const status = connectionStatuses.get(name);
    if (status?.state === "connected") {
      // off 后重新 on 的场景: 工具已注册但不在活跃集,需要补回(lazyTools 的除外)
      const lazySet = resolveLazyTools(name, cfg);
      const toolNames = serverTools.get(name) ?? [];
      const currentActive = pi.getActiveTools();
      const missing = toolNames.filter((n) => !currentActive.includes(n) && !lazySet.has(n));
      if (missing.length > 0) pi.setActiveTools([...currentActive, ...missing]);
      notify?.(`✓ ${name} 已连接,${status.tools.length} 个工具可用`);
    } else if (status?.state === "failed") {
      notify?.(`✗ ${name} 连接失败: ${status.error}`, "error");
    }
  };

  // session_start 时自动连接所有非 lazy 的 server，异步进行不阻塞 session 启动
  pi.on("session_start", () => {
    ensureInitialized();
  });

  type McpStatusEntry = {
    servers: Array<{
      name: string;
      status: ConnectionStatus;
      lazy: boolean;
      active: boolean;
      tools: Array<{ name: string; status: "success" | "fail"; lazy: boolean }>;
    }>;
  };

  const renderStatusPanel = () => {
    pi.appendEntry<McpStatusEntry>("mcp", {
      servers: servers.map(([name]) => {
        const status = connectionStatuses.get(name) ?? { state: "pending" as const };
        const cfg = servers.find(([n]) => n === name)?.[1];
        const lazyToolSet = resolveLazyTools(name, cfg);
        return {
          name,
          status,
          lazy: Boolean(cfg?.lazy),
          active: active.has(name) || clients.has(name),
          tools: (status.state === "connected" ? status.tools : []).map((tool) => ({
            name: tool,
            status: toolStatuses.get(`${name}__${tool}`) ?? "success",
            lazy: lazyToolSet.has(`${name}__${tool}`),
          })),
        };
      }),
    });
  };

  pi.registerEntryRenderer<McpStatusEntry>("mcp", (entry, _options, theme) => {
    const box = new Box(1, 1);
    const truncate = (s: string, n: number) => (s.length > n ? `${s.slice(0, n)}…` : s);
    for (const { name, status, lazy, active: on, tools } of entry.data?.servers ?? []) {
      const tag = on ? (lazy ? " [on·lazy]" : " [on]") : lazy ? " [off·lazy]" : " [off]";
      box.addChild(new Text(theme.fg(on ? "accent" : "dim", `${name}${tag}:`), 0, 0));
      if (status.state === "failed") {
        box.addChild(new Text(theme.fg("error", "  连接失败"), 0, 0));
        if (status.error) box.addChild(new Text(theme.fg("dim", `  ${truncate(status.error, 100)}`), 0, 0));
      } else if (status.state === "pending") {
        if (!on) {
          box.addChild(new Text(theme.fg("dim", `  未开启, /mcp on ${name} 或 /mcp 交互切换`), 0, 0));
        } else {
          box.addChild(new Text(theme.fg("warning", "  连接中..."), 0, 0));
        }
      } else {
        if (tools.length === 0) {
          box.addChild(new Text(theme.fg("dim", "  (no tools)"), 0, 0));
        }
        for (const tool of tools) {
          const failTag = tool.status === "fail" ? " (fail)" : "";
          const lazyTag = tool.lazy ? " (lazy)" : "";
          const color = tool.status === "fail" ? "error" : "dim";
          box.addChild(new Text(theme.fg(color, `  ${tool.name}${lazyTag}${failTag}`), 0, 0));
        }
      }
    }
    box.addChild(new Text(theme.fg("dim", "开关: /mcp (交互) · /mcp on|off <name> · 工具级: /tools"), 0, 0));
    return box;
  });

  pi.registerCommand("mcp", {
    description: "MCP server 开关面板; /mcp on|off <name> 单独切换",
    handler: async (args, ctx) => {
      const notify: Notify | undefined = ctx.hasUI
        ? (message: string, type = "info") => ctx.ui.notify(message, type)
        : undefined;
      const [action, target] = args.trim().split(/\s+/).filter(Boolean);

      if (action === "off" && target) {
        if (!clients.has(target) && !active.has(target)) {
          ctx.ui.notify(`server ${target} 未开启`, "warning");
          return;
        }
        disableServer(target);
        notify?.(`已关闭 ${target}`);
        return;
      }

      if (action === "on" && target) {
        await enableServer(target, notify);
        return;
      }

      // 兼容旧用法: /mcp <name> 等价于 /mcp on <name>
      if (action && !action.startsWith("-") && !target && action !== "on" && action !== "off") {
        await enableServer(action, notify);
        return;
      }

      if (servers.length === 0) {
        ctx.ui.notify("未配置 MCP server", "warning");
        return;
      }
      await ensureInitialized({ notify });

      // TUI 模式: SettingsList 原地 toggle,可连续切换多个 server
      if (ctx.mode === "tui") {
        const items: SettingItem[] = servers.map(([name, cfg]) => ({
          id: name,
          label: cfg.lazy ? `${name} (lazy)` : name,
          currentValue: clients.has(name) ? "on" : "off",
          values: ["on", "off"],
        }));

        await ctx.ui.custom((_tui, theme, _kb, done) => {
          const container = new Container();
          container.addChild(
            new (class {
              render(_width: number) {
                return [theme.fg("accent", theme.bold("MCP Servers")), ""];
              }
              invalidate() {}
            })(),
          );

          const settingsList = new SettingsList(
            items,
            Math.min(items.length + 2, 15),
            getSettingsListTheme(),
            (id, newValue) => {
              if (newValue === "on") {
                void enableServer(id, notify);
              } else {
                disableServer(id);
                notify?.(`已关闭 ${id}`);
              }
            },
            () => done(undefined),
          );

          container.addChild(settingsList);

          return {
            render: (w: number) => container.render(w),
            invalidate: () => container.invalidate(),
            handleInput: (data: string) => {
              settingsList.handleInput?.(data);
            },
          };
        });
      }

      // 非 TUI 直接显示面板; TUI 退出交互后也渲染一份最终状态
      renderStatusPanel();
    },
  });

  pi.on("session_shutdown", () => {
    log("event: session_shutdown", { clientCount: clients.size });
    for (const c of clients.values()) c.close().catch(() => {});
    clients.clear();
    registeredTools.clear();
    serverTools.clear();
    for (const [name] of servers) connectionStatuses.set(name, { state: "pending" });
    initPromise = null;
    log("all clients cleared");
  });
}
