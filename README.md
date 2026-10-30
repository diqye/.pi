# pi-config

`~/.pi` 配置仓库：pi coding agent 的全局配置、扩展、技能，统一 git 管理与 bun 依赖。

## 快速开始

```bash
cd ~/.pi
bun install
```

依赖用途：
- `node-cron` — schedule-prompt 扩展运行时依赖
- `zod` — zhipu-tools 扩展响应校验
- `pi-coding-agent` / `pi-tui` / `typescript` — 扩展开发的类型提示与 `bunx tsc` 检查（与全局 pi 版本对齐，当前 1.0.x）

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
│   ├── auth.json         # 凭据：zai-coding-cn / minimax-cn，key 为 $VAR 引用，随仓库提交
│   ├── models.json       # 模型列表：自定义 provider（ark/ksyun/zmexing），apiKey 全为 $VAR 引用，随仓库提交
│   ├── mcp.json          # 内置 MCP server 配置（pi 1.0 原生支持，无敏感信息，随仓库提交）
│   ├── extensions/       # 自定义扩展
│   ├── prompts/          # 提示词模板
│   └── skills/           # 技能（SKILL.md + 配套文件）
```

## MCP（pi 1.0 内置）

- 配置：`agent/mcp.json`，工具命名 `mcp__<server>__<tool>`
- 默认 exposure `codemode`：工具不声明给模型，codemode 脚本按需调用，几乎零上下文成本
- 会话内 `/mcp` 可视化管理：连接状态、OAuth 登录、重连、启停、exposure
- 当前仅 `chrome-devtools`，`enabled: false`（用时在 `/mcp` 启用）

## 扩展

| 扩展 | 说明 |
|---|---|
| `model-alias.ts` | 模型别名 |
| `piko.ts` | piko 集成 |
| `privacy-guard.ts` | 隐私防护 |
| `tools.ts` | `/tools` 工具开关面板：session_start 保留默认 builtin，其余全关手动开（PI_TOOLS_ON 白名单） |
| `zhipu-tools.ts` | 智谱 REST 工具：`web_search`（search_pro 实时搜索）、`analyze_image`（GLM 视觉识图/OCR），凭证读 `ZHIPU_API_KEY` 环境变量；exposure=codemode（注册即始终可调，不占上下文，无需 /tools 开） |
| `image-gen.ts` | `gpt-image-2` CLI 封装：`generate_image`（生成/编辑，含 ref/mask）、`image_mask`（本地蒙版）；exposure=deferred（tool_search 按需声明后直接调） |
| `trim-context.ts` | context 裁剪：`/trim <n>` 轮次截断（落 compaction 检查点，会话文件保留全史，`/tree` 可回看）；`/trim tool <n>` 钉分界线裁剪 tool result（分界前替换为 `[Content removed]` 标记，之后及新增永久原文；状态以 turn=false 消息内嵌 session，重复执行以最后一条为准，加大 n 可放回）；`/trim show` 统计 tokens 占比与节省量 |
| `schedule-prompt` | cron 定时注入 prompt（exposure=codemode，`/schedule` 查看，进程内存态） |
| `session-chat` | 同机多 pi 实例互通（UDP 多播组）；`/peers` 上下线/描述/ping，`/msg <pid\|name> <text>` 直发；工具 `session_msg` 活跃随 `/peers` 上下线联动；`PI_SESSION_CHAT=1` 启动自动上线 |
| `show-system-prompt.ts` | `/system-prompt` 将当前生效的完整 system prompt 写入 `/tmp/pi-system-prompt.md`（附体积） |

## 技能

| 技能 | 说明 |
|---|---|
| `changelog` | CHANGELOG.md 段结构与冻结规则 |
| `code-philosophy` | 工程哲学与 TS/React 编码规范 |
| `conventional-commits` | 约定式提交规范 |
| `git-branch-workflow` | 分支协作与提测/上线/hotfix 流程 |
| `pi-paths` | pi 安装位置与配置路径速查 |
| `wenqi` | 以文气为核心的写作方法与文字修改 |

## 提示词模板

`agent/prompts/` 下通过 `/prompts` 调用：`feishu-publish`。

## 环境变量（凭证）

仓库内不含任何明文 key：`models.json` / `auth.json` 全部为 `$VAR` 引用，换机器只需在 shell 配置（如 `~/.zshrc`）导出：

| 变量 | 用途 |
|---|---|
| `ARK_API_KEY` | 火山方舟 ark（doubao-seed-evolving） |
| `KSYUN_API_KEY` | ksyun（Anthropic 网关，headers 同源） |
| `ZMEXING_API_KEY` / `ZMEXING_WSF_API_KEY` | zmexing 两套网关 |
| `ZHIPU_API_KEY` | 智谱开放平台：zai-coding-cn provider + web_search / analyze_image 工具 |
| `MINIMAX_API_KEY` | minimax-cn provider |

环境变量改动需重启 pi 生效；models.json 改动会话内重开 `/model` 即重载。

## 维护

```bash
bun install                    # 安装依赖
bunx tsc                       # 类型检查扩展
git add -A && git commit       # 提交配置变更（遵循 conventional commits）
```
