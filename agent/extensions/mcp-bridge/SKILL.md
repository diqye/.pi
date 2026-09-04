---
name: pi-mcp-bridge
description: pi 的 MCP 客户端实现(mcp-bridge 扩展)。用于查找 pi 如何连接 MCP server、工具命名规则、配置文件位置、structuredContent 处理、连接调试。当用户问起 pi 的 MCP 支持、mcp-bridge、MCP 工具连不上、工具名带 __ 前缀时使用。
---

# pi MCP Bridge

pi 通过 `~/.pi/agent/extensions/mcp-bridge/` 扩展实现 MCP 客户端,把外部 MCP server 的工具桥接成 pi 原生工具。

## 关键文件
- 扩展实现:`~/.pi/agent/extensions/mcp-bridge/index.ts`
- MCP server 配置:`~/.pi/agent/mcp.ts`(导出 `mcpServers`)

## 工作机制
1. `session_start` 时自动读取 `~/.pi/agent/mcp.ts`,连接所有配置的 server(默认全部连接,异步不阻塞)
2. `client.listTools()` 拿到工具,注册成 pi 工具
3. 注册后默认留在活跃名单(默认 ON),由 `/tools` 命令统一开关
4. 工具名格式:`${server}__${tool}`(双下划线分隔)
5. 工具描述前缀 `[server]`,label 格式 `server.tool`

## 工具级 lazy（lazyTools）
server 配置项 `lazyTools: boolean | string[]`：
- `true`：该 server 全部工具正常注册但默认不进活跃集（模型看不到），用 `/tools` 手动开启
- `["webSearchPro"]`：仅列表中的工具默认 OFF，其余照常 ON；可写裸名或 `server__tool` 全名
- 不配置：维持默认，连接后全部 ON
- `/mcp off → on` 会重跑过滤：手动开启过的 lazy 工具会被重置回 OFF
- 与 server 级 `lazy: true`（默认不连接）互不冲突，可叠加

## transport 支持
- `stdio`(有 command 时默认):StdioClientTransport
- `http`(有 url 时默认):StreamableHTTPClientTransport
- `sse`:SSEClientTransport

## ⚠️ structuredContent 被丢弃
`toPiContent` 只读 `result.content` 数组(text/image/resource),**完全忽略 `result.structuredContent`**。
通过 mcp-bridge 暴露的 MCP 工具,模型拿不到结构化数据。若 MCP server 依赖 structuredContent 传递信息,必须同时把信息放进 content 数组(如序列化成 text)。

## 命令
- `/mcp`:TUI 下弹交互式开关面板（SettingsList 原地 toggle，可连续切换多个 server，Esc 退出）；非 TUI 显示只读状态面板
- `/mcp on <name>` / `/mcp off <name>`:命令式开关（旧写法 `/mcp <name>` 等价于 on）
- `off` = 断开 client + `pi.setActiveTools()` 把该 server 全部工具移出活跃集，一步到位
- 重新 `on` 时工具重新激活（已注册的工具跳过重复注册）；无持久化，重启进程恢复默认
- 工具级开关仍用 `/tools`（tools.ts 扩展）

## 调试
- `MCP_DEBUG=true pi --no-session` 开启详细日志(连接、listTools、注册、执行)
- 连接超时 8s,listTools 超时 8s
- 类型检查:`cd ~/.pi && bunx tsc`(根 package.json 统一管理依赖,`bun install` 一次全装)

## 配置示例(~/.pi/agent/mcp.ts)
```ts
export default {
  mcpServers: {
    bizplug: {
      type: "http",
      url: "http://localhost:3100/mcp",
    },
    // stdio 示例:
    // some: { command: "bunx", args: ["some-mcp-server"] },
  },
};
```
