# pi-config

`~/.pi` 配置仓库：pi coding agent 的全局配置、扩展、技能，统一 git 管理与 bun 依赖。

## 快速开始

```bash
cd ~/.pi
bun install
```

依赖用途：
- `@modelcontextprotocol/sdk` — mcp-bridge 扩展运行时依赖
- `node-cron` — schedule-prompt 扩展运行时依赖
- `pi-coding-agent` / `pi-tui` / `typescript` — 扩展开发的类型提示与 `bunx tsc` 检查

## 目录结构

```
~/.pi/
├── AGENTS.md             # 仓库指令（扩展开发规范）
├── package.json          # 依赖与工具链
├── tsconfig.json         # 扩展 TS 配置
├── agent/
│   ├── AGENTS.md         # 全局指令（运行时、系统工具、交流风格）
│   ├── settings.json     # 主题、默认模型、thinking level、packages
│   ├── keybindings.json  # 快捷键
│   ├── auth.json         # 凭证（gitignore，从 auth.json.example 复制）
│   ├── models.json       # 模型列表（gitignore，从 models.json.example 复制）
│   ├── mcp.ts            # MCP server 配置（gitignore，从 mcp.ts.example 复制）
│   ├── extensions/       # 自定义扩展
│   ├── prompts/          # 提示词模板
│   └── skills/           # 技能（SKILL.md + 配套文件）
```

## 扩展

| 扩展 | 说明 |
|---|---|
| `mcp-bridge` | pi 的 MCP 客户端，`/mcp` 支持交互式 server 开关 |
| `model-alias.ts` | 模型别名 |
| `piko.ts` | piko 集成 |
| `privacy-guard.ts` | 隐私防护 |
| `tools.ts` | 自定义工具 |
| `schedule-prompt` | cron 定时注入 prompt（默认 OFF，`/tools` 开启，`/schedule` 查看，进程内存态） |
| `session-chat` | 同机多 pi 实例互通（UDP 多播组）；`/peers` 上下线/描述/ping，`/msg <pid\|name> <text>` 直发；工具 `session_msg` 活跃随 `/peers` 上下线联动；`PI_SESSION_CHAT=1` 启动自动上线 |

## 技能

| 技能 | 说明 |
|---|---|
| `changelog` | CHANGELOG.md 段结构与冻结规则 |
| `code-philosophy` | 工程哲学与 TS/React 编码规范 |
| `conventional-commits` | 约定式提交规范 |
| `pi-paths` | pi 安装位置与配置路径速查 |
| `pi-mcp-bridge` | pi MCP 客户端实现速查（随 mcp-bridge 扩展分发） |
| `wenqi` | 以文气为核心的写作方法与文字修改 |

## 提示词模板

`agent/prompts/` 下通过 `/prompts` 调用：`feishu-publish`、`gpt-image-2`。

## 敏感配置

`auth.json` / `mcp.ts` / `models.json` 已 gitignore，换机器时从对应 `*.example` 复制并填入真实 key。

## 维护

```bash
bun install                    # 安装依赖
bunx tsc                       # 类型检查扩展
git add -A && git commit       # 提交配置变更（遵循 conventional commits）
```
