/**
 * Session Chat Extension
 *
 * 同机多 pi 实例互通（UDP 多播，进程内存态 peer 表，退出即消失）。
 *
 * - /peers：上线开关 + desc 编辑 + 在线 peer 列表（basename / desc / cwd）；
 *   PI_SESSION_CHAT=1 环境变量启动时自动上线
 * - /msg <pid|basename> <text>：用户直发消息（pid 优先；basename 歧义时列候选提示用 pid）
 * - 工具 session_msg（活跃随 /peers 上下线自动增减）：send / list / set-desc
 *   （上线即可用，AI 可主动跨 session 发消息；下线自动移除，避免无效工具占位）
 * - 协议：hello / ack / bye / presence(2s 心跳, 5s 剔除) / msg / ping / pong
 *   全部走 UDP 多播组 239.255.0.7:50707（私有多播段，本机 loopback），
 *   消息按 toPid 定向，未上线实例收不到（未 addMembership 则内核不投递）
 *
 * 为什么不用 node:worker_threads 的 BroadcastChannel：pi 由 Node 运行，
 * Node 的 BroadcastChannel 是进程内注册表，不跨进程（Bun 实现才是跨进程的）。
 */

import dgram from "node:dgram";
import { basename } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { getSettingsListTheme } from "@earendil-works/pi-coding-agent";
import { Container, SettingsList, type SettingItem } from "@earendil-works/pi-tui";
import { StringEnum } from "@earendil-works/pi-ai";
import { Type } from "typebox";

const GROUP = "239.255.0.7"; // 私有多播段（类比 192.168.x.x），任意选
const PORT = 50707; // 未被注册服务占用的端口
const LOOPBACK = "127.0.0.1"; // 组成员与发送均固定走 lo0：不出网卡、不受 VPN/utun 默认路由影响，也不触发 macOS 本地网络权限弹窗
const TOOL = "session_msg";
const CUSTOM_TYPE = "session-chat";
const HEARTBEAT_MS = 2_000; // 心跳间隔，须显著小于 STALE_MS（错过 2 次才判死，容忍事件循环卡顿）
const STALE_MS = 5_000; // 超此时长无心跳即剔除

interface Peer {
  pid: number;
  cwd: string;
  desc: string;
  name: string; // basename(cwd)
  lastSeen: number;
}

type Wire =
  | { type: "hello"; pid: number; cwd: string; desc: string }
  | { type: "ack"; pid: number; cwd: string; desc: string }
  | { type: "bye"; pid: number }
  | { type: "presence"; pid: number; cwd: string; desc: string }
  | { type: "msg"; fromPid: number; fromCwd: string; fromRole: "user" | "agent"; toPid: number; text: string }
  | { type: "ping"; fromPid: number }
  | { type: "pong"; pid: number };

function truncate(s: string, max: number): string {
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}

export default function sessionChatExtension(pi: ExtensionAPI) {
  const peers = new Map<number, Peer>();
  const pings = new Map<number, number>(); // pid -> sentAt
  const hintedPeers = new Set<number>(); // 已发过完整协作指令的 peer，后续消息只带短引用

  let sock: dgram.Socket | undefined;
  let heartbeat: ReturnType<typeof setInterval> | undefined;
  let uiCtx: ExtensionContext | undefined;
  let myCwd = process.cwd();
  let myDesc = "";
  let descManual = false;
  let online = false;

  // ---------- 状态 ----------

  function refreshStatus() {
    uiCtx?.ui.setStatus("chat", online ? `🛰 peers:${peers.size}` : undefined);
  }

  function touch(pid: number): Peer | undefined {
    const p = peers.get(pid);
    if (p) p.lastSeen = Date.now();
    return p;
  }

  function upsert(pid: number, cwd: string, desc: string): Peer {
    let p = peers.get(pid);
    const isNew = !p;
    if (!p) {
      p = { pid, cwd, desc, name: basename(cwd), lastSeen: Date.now() };
      peers.set(pid, p);
    } else {
      p.cwd = cwd;
      p.name = basename(cwd);
      p.desc = desc;
      p.lastSeen = Date.now();
    }
    if (isNew) uiCtx?.ui.notify(`🛰 peer joined: ${p.name} (${truncate(p.desc, 40)})`, "info");
    refreshStatus();
    return p;
  }

  function drop(pid: number) {
    const p = peers.get(pid);
    if (p) {
      peers.delete(pid);
      uiCtx?.ui.notify(`🛰 peer left: ${p.name}`, "warning");
      refreshStatus();
    }
  }

  function peerListText(): string {
    if (!online) return "未上线（/peers 开启）";
    if (peers.size === 0) return "在线 peer：无";
    return (
      "在线 peer：\n" +
      [...peers.values()]
        .map((p) => `- ${p.name} (pid ${p.pid}, ${p.cwd}): ${truncate(p.desc, 40)}`)
        .join("\n")
    );
  }

  // ---------- 上下线 ----------

  function post(m: Wire) {
    // 发送失败静默（如网络栈异常），靠心跳自愈
    sock?.send(Buffer.from(JSON.stringify(m)), PORT, GROUP, () => {});
  }

  function activateTool(active: boolean) {
    const tools = new Set(pi.getActiveTools());
    if (active) tools.add(TOOL);
    else tools.delete(TOOL);
    pi.setActiveTools([...tools]);
  }

  function ensureOnline() {
    if (online) return;
    online = true;
    sock = dgram.createSocket({ type: "udp4", reuseAddr: true }); // reuseAddr：多 pi 进程共用同一端口
    sock.on("message", (buf) => {
      try {
        onWire(JSON.parse(buf.toString()) as Wire);
      } catch {
        /* 非 JSON 载荷，忽略（端口被其他程序占用发送时） */
      }
    });
    sock.bind(PORT, () => {
      sock?.addMembership(GROUP, LOOPBACK);
      sock?.setMulticastInterface(LOOPBACK);
      post({ type: "hello", pid: process.pid, cwd: myCwd, desc: myDesc });
    });
    sock.unref();
    heartbeat = setInterval(() => {
      post({ type: "presence", pid: process.pid, cwd: myCwd, desc: myDesc });
      const now = Date.now();
      for (const [pid, p] of peers) if (now - p.lastSeen > STALE_MS) drop(pid);
    }, HEARTBEAT_MS);
    heartbeat.unref();
    uiCtx?.ui.notify("🛰 已上线，广播 hello", "info");
    activateTool(true); // 工具随上线激活：send/list/set-desc 可用
    refreshStatus();
  }

  // async：等 bye 的 send 回调（包已交内核）后才 resolve。
  // session_shutdown handler 必须 await 本函数——否则 handler 同步返回后 pi 继续
  // process.exit，排在队列里的 sendto syscall 永远没机会执行，bye 静默丢失
  async function goOffline(): Promise<void> {
    if (!online) return;
    online = false;
    if (heartbeat) clearInterval(heartbeat);
    heartbeat = undefined;
    const s = sock;
    sock = undefined;
    peers.clear();
    hintedPeers.clear();
    activateTool(false);
    uiCtx?.ui.notify("🛰 已下线", "info");
    refreshStatus();
    if (!s) return;
    await new Promise<void>((resolve) => {
      try {
        s.send(
          Buffer.from(JSON.stringify({ type: "bye", pid: process.pid } satisfies Wire)),
          PORT,
          GROUP,
          () => resolve(), // send 出错也会回调，不区分
        );
      } catch {
        resolve(); /* socket already closed */
      }
    });
    try {
      s.close();
    } catch {
      /* socket already closed */
    }
  }

  function onWire(m: Wire) {
    // 多播回环：内核会把自己发的包也投回来（IP_MULTICAST_LOOP 默认开），按 pid 过滤
    const from = m.type === "msg" || m.type === "ping" ? m.fromPid : m.pid;
    if (from === process.pid) return;
    if (m.type === "hello") {
      upsert(m.pid, m.cwd, m.desc);
      post({ type: "ack", pid: process.pid, cwd: myCwd, desc: myDesc });
      return;
    }
    if (m.type === "ack" || m.type === "presence") {
      upsert(m.pid, m.cwd, m.desc);
      return;
    }
    if (m.type === "bye") {
      drop(m.pid);
      return;
    }
    if (m.type === "msg") {
      if (m.toPid !== process.pid) return;
      touch(m.fromPid);
      const from = peers.get(m.fromPid);
      const who = from ? `${from.name} (pid ${m.fromPid}, ${m.fromRole})` : `pid ${m.fromPid} (${m.fromRole})`;
      pi.sendMessage(
        {
          customType: CUSTOM_TYPE,
          content: `[msg from ${who}] ${m.text}\n${hintFor(m)}`,
          display: true,
        },
        { triggerTurn: true, deliverAs: "followUp" },
      );
      return;
    }
    if (m.type === "ping") {
      touch(m.fromPid);
      post({ type: "pong", pid: process.pid });
      return;
    }
    if (m.type === "pong") {
      const sentAt = pings.get(m.pid);
      if (sentAt !== undefined) {
        pings.delete(m.pid);
        const p = touch(m.pid);
        uiCtx?.ui.notify(`🏓 pong ${p?.name ?? m.pid}: ${Date.now() - sentAt}ms`, "info");
      }
      return;
    }
    // 穷尽检查：新增 Wire 成员而未处理时，此处编译报错
    m satisfies never;
  }

  // ---------- 发送 ----------

  // 收到 peer 消息后的行为提示：user 消息用工具回；agent 消息完全自主推进。
  // 完整指令只随每个 peer 的首条 agent 消息下发，后续带短引用——
  // 不能完全裸奔：compaction 会把旧消息里的指令文本摘要掉，裸消息会退化为停下来问用户
  function hintFor(m: Extract<Wire, { type: "msg" }>): string {
    if (m.fromRole === "user")
      return `(用 session_msg 的 send 回复对方，to 填 pid ${m.fromPid})`;
    if (!hintedPeers.has(m.fromPid)) {
      hintedPeers.add(m.fromPid);
      return `(可自主用 session_msg 的 send 回复对方推进协作，无需用户确认；对话目标达成或遇分歧时总结告知用户。此 peer 的后续消息均遵循本指令)`;
    }
    return `(同前指令：自主用 send 回复推进)`;
  }

  function resolveTarget(input: string): { ok: true; peer: Peer } | { ok: false; error: string } {
    if (/^\d+$/.test(input)) {
      const p = peers.get(Number(input));
      return p ? { ok: true, peer: p } : { ok: false, error: `无 pid=${input} 的 peer` };
    }
    const hits = [...peers.values()].filter((p) => p.name === input);
    if (hits.length === 1) return { ok: true, peer: hits[0] };
    if (hits.length === 0) return { ok: false, error: `无名为 "${input}" 的 peer。\n${peerListText()}` };
    return {
      ok: false,
      error:
        `多个 peer 名为 "${input}"，请用 pid：\n` +
        hits.map((p) => `  pid ${p.pid}  ${p.cwd}`).join("\n"),
    };
  }

  function sendTo(peer: Peer, text: string, role: "user" | "agent"): string {
    if (!online || !sock) return "ERROR: 未上线，请先在 /peers 中开启";
    post({ type: "msg", fromPid: process.pid, fromCwd: myCwd, fromRole: role, toPid: peer.pid, text });
    return `已发送 → ${peer.name} (pid ${peer.pid}): ${text}`;
  }

  function setDesc(desc: string, manual: boolean): string {
    myDesc = desc;
    if (manual) descManual = true;
    if (online) post({ type: "presence", pid: process.pid, cwd: myCwd, desc: myDesc });
    return `desc 已更新: ${desc}`;
  }

  // ---------- 工具（活跃随 /peers 上下线联动） ----------

  pi.registerTool({
    name: TOOL,
    label: "Session Msg",
    description:
      "与其他 pi 实例的 session 通信（需先在 /peers 上线）。" +
      "send 需要 to（pid 或 basename）和 text；set-desc 设置自己的一句自我描述（广播给所有 peer）；" +
      "list 列出在线 peer 及其描述。",
    promptSnippet: "Send messages to peer pi sessions on this machine (requires /peers online)",
    promptGuidelines: [
      "Use session_msg to talk with other live pi sessions when the user wants cross-session discussion; pick peers by their description in list output.",
    ],
    parameters: Type.Object({
      action: StringEnum(["send", "list", "set-desc"]),
      to: Type.Optional(Type.String({ description: "目标 peer：pid（唯一）或 basename，send 时必填" })),
      text: Type.Optional(Type.String({ description: "消息内容，send 时必填" })),
      desc: Type.Optional(Type.String({ description: "set-desc 时必填：一句话自我描述，会广播更新" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      if (params.action === "send") {
        if (!params.to || !params.text)
          return {
            content: [{ type: "text", text: "ERROR: send 需要 to 和 text" }],
            details: {},
            isError: true,
          };
        if (!online)
          return {
            content: [{ type: "text", text: "ERROR: 未上线，请让用户在 /peers 中开启" }],
            details: {},
            isError: true,
          };
        const r = resolveTarget(params.to);
        if (!r.ok)
          return { content: [{ type: "text", text: `ERROR: ${r.error}` }], details: {}, isError: true };
        return { content: [{ type: "text", text: sendTo(r.peer, params.text, "agent") }], details: {} };
      }
      if (params.action === "list")
        return { content: [{ type: "text", text: peerListText() }], details: { online } };
      if (params.action === "set-desc") {
        if (!params.desc)
          return {
            content: [{ type: "text", text: "ERROR: set-desc 需要 desc" }],
            details: {},
            isError: true,
          };
        return { content: [{ type: "text", text: setDesc(params.desc, true) }], details: {} };
      }
      return {
        content: [{ type: "text", text: `ERROR: 未知 action: ${params.action}` }],
        details: {},
        isError: true,
      };
    },
  });

  // ---------- 命令 ----------

  pi.registerCommand("msg", {
    description: "Send a message to a peer session: /msg <pid|basename> <text>",
    handler: async (args, ctx) => {
      const i = args.indexOf(" ");
      if (i < 0) {
        ctx.ui.notify("用法: /msg <pid|basename> <text>\n" + peerListText(), "warning");
        return;
      }
      if (!online) {
        ctx.ui.notify("未上线，请先 /peers 开启", "warning");
        return;
      }
      const r = resolveTarget(args.slice(0, i).trim());
      if (!r.ok) {
        ctx.ui.notify(r.error, "error");
        return;
      }
      const out = sendTo(r.peer, args.slice(i + 1).trim(), "user");
      ctx.ui.notify(out.startsWith("ERROR") ? out : `→ ${r.peer.name}: ${args.slice(i + 1).trim()}`, out.startsWith("ERROR") ? "error" : "info");
    },
  });

  pi.registerCommand("peers", {
    description: "Session chat: online toggle, description edit & peer list",
    handler: async (_args, ctx) => {
      if (ctx.mode !== "tui") {
        ctx.ui.notify("/peers requires TUI mode", "error");
        return;
      }
      await openPeersUI(ctx);
    },
  });

  async function openPeersUI(ctx: ExtensionContext) {
    let pending: "editDesc" | { peer: Peer } | undefined;

    const items: SettingItem[] = [
      {
        id: "__me",
        label: "me",
        currentValue: online ? "online" : "offline",
        values: ["online", "offline"],
      },
      {
        id: "__desc",
        label: `my description: ${truncate(myDesc, 30)}`,
        currentValue: "edit",
        values: ["edit"],
      },
      ...[...peers.values()].map((p) => ({
        id: String(p.pid),
        label: `${p.name}  ${truncate(p.desc, 30)}  ${p.cwd}`,
        currentValue: "ping",
        values: ["ping", "msg"],
      })),
    ];

    await ctx.ui.custom((_tui, theme, _kb, done) => {
      const container = new Container();
      container.addChild(
        new (class {
          render(_width: number) {
            return [theme.fg("accent", theme.bold(`Session Chat  (${process.pid})`)), ""];
          }
          invalidate() {}
        })(),
      );
      const list = new SettingsList(
        items,
        Math.min(items.length + 2, 15),
        getSettingsListTheme(),
        (id, newValue) => {
          if (id === "__me") {
            if (newValue === "online") ensureOnline();
            else goOffline();
            done(undefined); // 关闭后由外层重开刷新状态
          } else if (id === "__desc") {
            pending = "editDesc";
            done(undefined);
          } else {
            const peer = peers.get(Number(id));
            if (!peer) return;
            if (newValue === "ping") {
              pings.set(peer.pid, Date.now());
              post({ type: "ping", fromPid: process.pid });
            } else if (newValue === "msg") {
              pending = { peer };
              done(undefined);
            }
          }
        },
        () => done(undefined),
      );
      container.addChild(list);
      return {
        render: (w: number) => container.render(w),
        invalidate: () => container.invalidate(),
        handleInput: (data: string) => {
          list.handleInput?.(data);
        },
      };
    });

    if (pending === "editDesc") {
      const v = await ctx.ui.input("My description", myDesc);
      if (v != null && v.trim()) {
        uiCtx?.ui.notify(setDesc(v.trim(), true), "info");
        await openPeersUI(ctx); // 重开刷新
        return;
      }
      await openPeersUI(ctx);
      return;
    }
    if (pending && "peer" in pending) {
      const v = await ctx.ui.input(`msg → ${pending.peer.name} (pid ${pending.peer.pid})`, "");
      if (v && v.trim()) {
        const out = sendTo(pending.peer, v.trim(), "user");
        ctx.ui.notify(out, "info");
      }
    }
  }

  // ---------- 生命周期 ----------

  pi.on("session_start", (_event, ctx) => {
    uiCtx = ctx;
    myCwd = ctx.cwd;
    myDesc = pi.getSessionName() ?? basename(myCwd);
    // 默认 OFF：未上线时工具不可见，ensureOnline 时随状态激活；
    // PI_SESSION_CHAT=1 环境变量启动时自动上线（pi 不支持自定义 --flag，环境变量是唯一启动期开关）
    pi.setActiveTools(pi.getActiveTools().filter((n) => n !== TOOL));
    if (/^(1|true|on|yes)$/i.test(process.env.PI_SESSION_CHAT ?? "")) ensureOnline();
    refreshStatus();
  });

  pi.on("session_info_changed", (event, _ctx) => {
    // session 改名自动跟随 desc（用户/AI 未手动设置过时）
    if (!descManual && event.name) {
      myDesc = event.name;
      if (online) post({ type: "presence", pid: process.pid, cwd: myCwd, desc: myDesc });
    }
  });

  pi.on("session_shutdown", async () => {
    await goOffline(); // 必须等：bye 包交内核后才能让 pi 退出
    uiCtx = undefined;
  });
}
