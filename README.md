# pi-config

`~/.pi` 配置仓库：pi coding agent 的全局配置、扩展、技能、子代理与提示词模板，统一 git 管理与 bun 依赖。

## 快速开始

```bash
cd ~/.pi
bun install
```

依赖用途：
- `@modelcontextprotocol/sdk` — mcp-bridge 扩展运行时依赖
- `pi-coding-agent` / `pi-tui` / `typescript` — 扩展开发的类型提示与 `bunx tsc` 检查

## 目录结构

```
~/.pi/
├── package.json          # 依赖与工具链
├── tsconfig.json         # 扩展 TS 配置
├── agent/
│   ├── AGENTS.md         # 全局指令（运行时、交流风格）
│   ├── settings.json     # 主题、默认模型、thinking level、packages
│   ├── keybindings.json  # 快捷键
│   ├── auth.json         # 凭证（gitignore，从 auth.json.example 复制）
│   ├── models.json       # 模型列表（gitignore，从 models.json.example 复制）
│   ├── mcp.ts            # MCP server 配置（gitignore，从 mcp.ts.example 复制）
│   ├── agents/           # 子代理定义（planner / reviewer / scout / worker）
│   ├── extensions/       # 自定义扩展
│   ├── prompts/          # 提示词模板
│   └── skills/           # 技能（SKILL.md + 配套文件）
```

## 扩展

| 扩展 | 说明 |
|---|---|
| `mcp-bridge` | pi 的 MCP 客户端，`/mcp` 支持交互式 server 开关 |
| `subagent` | 子代理框架（配合 `agents/` 使用） |
| `model-alias.ts` | 模型别名 |
| `piko.ts` | piko 集成 |
| `privacy-guard.ts` | 隐私防护 |
| `tools.ts` | 自定义工具 |

## 技能

| 技能 | 说明 |
|---|---|
| `code-philosophy` | 工程哲学与 TS/React 编码规范 |
| `conventional-commits` | 约定式提交规范 |
| `pi-paths` | pi 安装位置与配置路径速查 |

## 提示词模板

`agent/prompts/` 下通过 `/prompts` 调用：`implement`、`implement-and-review`、`scout-and-plan`、`feishu-publish`、`gpt-image-2`、`study-en`。

## 敏感配置

`auth.json` / `mcp.ts` / `models.json` 已 gitignore，换机器时从对应 `*.example` 复制并填入真实 key。

## 维护

```bash
bun install                    # 安装依赖
bunx tsc                       # 类型检查扩展
git add -A && git commit       # 提交配置变更（遵循 conventional commits）
```
