---
name: conventional-commits
description: 约定式提交规范。在执行 git commit、编写 commit message、或用户要求提交代码时使用。确保每次提交都符合 Conventional Commits 标准。
---

# Conventional Commits

提交代码时，commit message 必须遵循约定式提交规范。

## 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

- header（第一行）必填，body 和 footer 可选
- subject 用中文，简明描述"做了什么"，不用句号结尾
- 一次提交只做一件事；混合改动拆成多个提交

## type 取值

| type | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(publish): 新增上传到九霄功能` |
| `fix` | bug 修复 | `fix(ws): 修复 WebSocket 断线不重连` |
| `refactor` | 重构，不改行为 | `refactor(agent): 系统提示词移至 AGENTS.md` |
| `perf` | 性能优化 | `perf(preview): 减少不必要的 iframe 重载` |
| `style` | 格式调整，不影响逻辑 | `style(css): 调整主题色变量命名` |
| `docs` | 文档 | `docs(skill): 更新 math-courseware SKILL.md` |
| `test` | 测试 | `test(tts): 补充语音合成单元测试` |
| `chore` | 构建、依赖、配置等杂项 | `chore(docker): 添加 build-base 依赖` |
| `ci` | CI/CD | `ci: 配置自动部署流水线` |
| `build` | 构建系统 | `build(bun): 升级到 1.3.14` |
| `revert` | 回滚 | `revert: 撤销 problem_source 字段` |

## scope（可选）

表示改动范围，用模块/文件/功能名。项目常见 scope：

- 组件/hooks 名：`editor`、`chat`、`player`、`ws`
- 模块名：`agent`、`tts`、`import`、`publish`
- 配置：`docker`、`css`、`theme`
- 通用层：`const`、`types`

不确定时省略 scope，不要硬编。

## 破坏性变更

在 type 后加 `!` 或在 footer 写 `BREAKING CHANGE:`：

```
feat(api)!: 课件接口返回结构变更

BREAKING CHANGE: courseware.nodes 改为按 flow 分组返回
```

## 规则

1. **中文 subject**：`feat(ws): 新增 WebSocket 自动重连`
2. **一个提交一件事**：如果同时改了 bug 和加了功能，拆两个提交
3. **用 `git add <file>` 精确暂存**，不用 `git add -A`，避免混入无关文件
4. **body 写"为什么"**，不写"改了什么"——diff 已经说明了改了什么
5. **不要在 commit message 里放文件路径列表**，这是噪音
