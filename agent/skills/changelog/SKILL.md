---
name: changelog
description: 维护 CHANGELOG.md 与发布流程。在用户要求写 changelog、记录变更、发布(release/记版本/冻结 Unreleased/打 tag)时使用。确保段结构、条目格式、冻结规则正确,发布时冻结版本段、提交本地并打 tag。
---

# Changelog 维护与发布

## 段结构

```
## [Unreleased]          ← 唯一可写区,新内容都进这里

## v0.2.0 (2026-09-14)   ← 已发布段,冻结不可改

### New Features         ← 用户视角一句话概览,有新功能时才写,排在段首
### Added                ← 详细条目
### Changed
### Fixed
### Breaking Changes     ← 破坏性变更只写这一段,不重复进其他段
```

项目已有 CHANGELOG.md 时,沿用其现有段标题格式(日期/版本号等)自行推导,不强行改版式;全新项目用版本号标题 `vX.Y.Z (YYYY-MM-DD)`。

两层制：New Features 是概览(给用户扫一眼看点)，Added/Changed/Fixed 是详细条目(改动内容、原因、影响)。两层并存，New Features 在前；无新功能只有变更时省略 New Features。

两层对应：New Features 每条与 Added 里的详细条目一一对应，新增 Added 条目时同步补 New Features，不能漏。

## 条目写法

- 详细段(Added/Changed/Fixed)每条一行，格式：`标题 - 详细描述`
- New Features 用 `- ` 列表，每条一句：`- 标题 - 一句话看点`(裸行需双换行才渲染成段落，列表才能逐条换行)
- 详细描述写清楚：做了什么 + 为什么 + 影响；diff 能看出的细节不展开
- 用户可见的功能写用户视角(能干什么、入口在哪)，实现细节一句带过

## 维护规则

1. 新内容只写 `[Unreleased]`，不触碰下方任何已发布段
2. 已发布段一经发布即冻结，禁止修改
3. **git add 不要带 CHANGELOG.md**：写完条目后让它在工作区保持未提交，只提交代码文件；仅当用户明确说 release/发布时才由下面的发布流程把 changelog 一起提交
4. 发布之后的改动(即便主题与发布内容相同)一律记新的 Unreleased 条目，不改冻结段

## 发布流程(release)

发布 = 冻结 changelog + 提交本地 + 打 tag。默认不 push。

### 版本号规则

- 格式 `vX.Y.Z`(semver);0.x 阶段默认 **minor +1**(每次发布基本都含新功能)
- 用户明确指定版本号时用指定的;含 Breaking Changes 且用户要求大版本时 major +1
- 下一版本 = CHANGELOG 中现有最大版本号推算;全新项目首个版本 v0.1.0
- 项目已有自己的版本规则时沿用其规则

### 前置校验

1. **分支校验**:`git branch --show-current` ∈ {main, master} 才可发布;不在主分支则终止并提醒用户切到主分支
2. 读仓库根 `CHANGELOG.md`,`[Unreleased]` 段(标题到下一个 `##` 之间)没有任何条目 →
   报告"Unreleased 为空,无可发布内容",流程终止

### 第一步:冻结 changelog

1. 确定版本号与日期,段标题格式:`## v0.2.0 (2026-09-10)`(版本号唯一,无同日 -v2 规则)
2. `## [Unreleased]` 标题改写为该版本段标题,段内条目原样保留(冻结后永不修改)
3. 在 `# Changelog` 主标题之后插入新的空段,保持结构:

   ```markdown
   # Changelog

   ## [Unreleased]

   ## v0.2.0 (2026-09-10)
   ```

4. 项目根有 package.json(或其他版本声明文件)时,`version` 同步为该版本(不带 v 前缀)

### 第二步:提交到本地

1. `git status` 查看工作区:
   - 有 CHANGELOG/版本声明文件之外的未提交改动 → 按 conventional commits 规范拆分提交,
     **先列出拆分与 message 计划,等用户确认再执行**
   - 无其他改动 → 直接进下一步
2. 冻结改动单独提交(含 CHANGELOG.md 与版本声明文件):

   ```
   chore(release): 锁定 v0.2.0
   ```

3. 在该 release commit 上打 tag:`git tag vX.Y.Z`(lightweight,不 push)

### 汇报

发布完成后报告:版本段标题、各 commit 的 hash 与 message、tag 名;项目若有实时读
CHANGELOG.md 的页面(如 lime 的 /changelog),无需其他动作即对外可见。

## Breaking Changes 判断

标准：有无**不在本次发布里、且无法同步更新**的调用方会坏(外部脚本依赖的 API 改路径、响应结构改字段、部署要求变化)。内部 web 页面路由/UI 调整、刚上线未被依赖的新路由变更都不算，避免段失去信噪度。
