---
name: changelog
description: 维护 CHANGELOG.md。在用户要求写 changelog、记录变更、发布(release/冻结 Unreleased)时使用。确保段结构、条目格式、冻结规则正确。
---

# Changelog 维护

## 段结构

```
## [Unreleased]          ← 唯一可写区,新内容都进这里

## 2026-08-22            ← 已发布段,冻结不可改
## 2026-08-22-v2         ← 同天多次发布,-v2/-v3 递增

### New Features         ← 用户视角一句话概览,有新功能时才写,排在段首
### Added                ← 详细条目
### Changed
### Fixed
### Breaking Changes     ← 破坏性变更只写这一段,不重复进其他段
```

两层制：New Features 是概览(给用户扫一眼看点)，Added/Changed/Fixed 是详细条目(改动内容、原因、影响)。两层并存，New Features 在前；无新功能只有变更时省略 New Features。

两层对应：New Features 每条与 Added 里的详细条目一一对应，新增 Added 条目时同步补 New Features，不能漏。

## 条目写法

- 详细段(Added/Changed/Fixed)每条一行，格式：`标题 - 详细描述`
- New Features 用 `- ` 列表，每条一句：`- 标题 - 一句话看点`(裸行需双换行才渲染成段落，列表才能逐条换行)
- 详细描述写清楚：做了什么 + 为什么 + 影响；diff 能看出的细节不展开
- 用户可见的功能写用户视角(能干什么、入口在哪)，实现细节一句带过

## 维护规则

1. 新内容只写 `[Unreleased]`，不触碰下方任何已发布段
2. 已发布段（带日期标题）一经发布即冻结，禁止修改
3. 发布时：`[Unreleased]` 冻结为日期标题（当天已有则 -v2/-v3），顶部新建空 `[Unreleased]`
4. release 之后的改动(即便主题与发布内容相同)一律记新的 Unreleased 条目，不改冻结段

## Breaking Changes 判断

标准：有无**不在本次发布里、且无法同步更新**的调用方会坏(外部脚本依赖的 API 改路径、响应结构改字段、部署要求变化)。内部 web 页面路由/UI 调整、刚上线未被依赖的新路由变更都不算，避免段失去信噪度。
