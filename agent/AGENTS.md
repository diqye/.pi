# 全局指令

## 运行时
- 优先 Bun runtime,不用 node/npm/npx/ts-node(细节见 bun skill)
- 优先Bun 写脚本。

## 系统工具
- 用户要求复制/读剪贴板时，用系统命令 `pbpaste`（读）、`echo 内容 | pbcopy`（写）
- 仅在直连失败时才加代理环境变量（避免走代理拖慢速度）：`export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890`

## 写代码
- 写/改/审查任何代码，或做架构设计前，先读 `code-philosophy` skill

## Skill 与记忆落盘
- skill/经验沉淀默认写项目级（`<项目>/.pi/skills/`），如非用户明确要求，不写全局 `~/.pi/agent/skills/`，不主动改全局 AGENTS.md

## 交流风格
- 针对用户当前场景,不枚举所有可能
- 缺关键信息先提问
- 极简:只给结论、原因、下一步,不展开背景
- **不要着急动手，等我确认再动手**：列计划 → 等回复 → 再执行
