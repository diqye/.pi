---
name: skill-placement
description: 安装、新增、下载或创建任何 skill 前，先向用户确认落位（项目级 / 全局 / stash 按需挂载），并说明各位置对应的加载与使用方式。Use when installing, adding, downloading, or creating a skill.
---

# Skill 落位决策

任何「装 skill」任务，动手前必须先问用户落位，不默认替用户选。

## 三种落位

| 落位 | 路径 | 可见性 |
|---|---|---|
| 项目级 | `<项目>/.pi/skills/` | 该项目每次会话自动发现 |
| 全局 | `~/.pi/agent/skills/`（`~/.agents/skills/` 同效） | 所有项目自动发现 |
| stash | `~/.pi/skills-stash/<name>/` | 默认不可见，按需挂载 |

「自动发现」= 只把 name + description 放进 system prompt，任务匹配时才读 SKILL.md 全文；`/skill:name` 强制加载。stash 落在 `~/.pi/skills-stash/`：pi 只扫 `~/.pi/agent/skills/`、`~/.agents/skills/` 和项目 `.pi/skills/`，`~/.pi` 其它子目录不会被扫描，所以默认不可见。

## stash 挂载命令

```bash
pi --skill ~/.pi/skills-stash/<name>              # 追加：默认发现 + 这个
pi --no-skills --skill ~/.pi/skills-stash/<name>  # 独占：只加载这个（--no-skills 只关发现，不影响 --skill）
pi --skill ~/.pi/skills-stash                     # 挂载 stash 下全部
```

`--skill` 是追加不是替换，可重复多次。用户选 stash 落位时，把对应挂载命令写入剪贴板。

## --skill 指向目录时的扫描规则

- 目录直接含 SKILL.md → 整个目录是一个 skill，截断，不再下钻
- 否则递归进子目录找 SKILL.md；顶层（仅顶层）散装 `.md` 每个也算独立 skill
- 跳过 `.` 开头条目、`node_modules`、命中 `.gitignore` / `.ignore` / `.fdignore` 的路径；symlink 跟进
- skill name 冲突时保留先发现者并告警

## 其他来源与选项

- package（npm / git / local）：走 `pi install [-l]`，资源启停用 `pi config` TUI（写回 settings）
- 只留手动命令、不参与自动路由：frontmatter 加 `disable-model-invocation: true`，`/skill:name` 仍可用

## 询问模板

> 这个 skill 装哪里？
> 1. 项目 `<项目>/.pi/skills/`（本项目每次会话自动可用）
> 2. 全局 `~/.pi/agent/skills/`（所有项目自动可用）
> 3. stash `~/.pi/skills-stash/<name>/`（默认不加载，`pi --skill` 按需挂载）
