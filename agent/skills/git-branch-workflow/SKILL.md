---
name: git-branch-workflow
description: 分支协作与开发流程规范。在执行 git 分支操作（拉需求分支、提测合并、上线合并、hotfix）、处理合并冲突、或用户讨论分支协作方式时使用。适用于所有项目。
---

# 分支协作与开发流程规范

## 分支角色

| 分支 | 角色 | 规则 |
|---|---|---|
| `master` | 上线基线 | 只进已验证代码，禁止直接推送 |
| `test` | 测试环境 | 禁止直接推送改动，只接受需求分支合并，定期从 master 重建 |
| 需求分支 | 一个需求一个分支，短生命周期 | 从 master 最新拉出，分别合 test（提测）与 master（上线） |

## 分支命名

格式：`姓名拼音/需求名/日期`（日期为拉分支当日 YYYYMMDD）

```
qinzhenlong/scan-upload/20260915           # 需求分支
qinzhenlong/hotfix-exam-timeout/20260918   # 紧急修复分支
qinzhenlong/scan-upload-h5-page/20260916   # 多人协作的个人子分支（需求名-模块）
```

## 标准流程

1. 从 master 最新代码拉需求分支
2. 开发只在需求分支；周期超过一周的，每 2~3 天 merge master 进来，冲突自己解决
3. 提测：需求分支 → test
4. 测试 bug 回需求分支修，再合 test；不在 test 上直接改
5. 上线：需求分支 → master（不经 test → master）
6. 上线后删除分支；test 由值班人定期从 master 重建 + 在测需求重合

## 红线

1. ❌ 禁止 `name/dev` 式长期混需求分支
2. ❌ 禁止直接在 test / master 上提交代码
3. ❌ 禁止 test → master 合并（会把未验收需求带上线）
4. ❌ 禁止需求分支之间互相合并

## 执行要点（agent 操作时）

- 帮用户拉分支：按命名格式起名，从 master 最新拉出，不用 name/dev；用户未告知姓名时，先 `git config user.name` 查询取名，不要用默认名（如 qy）
- 帮用户合并：只做 需求分支→test 或 需求分支→master；用户要求 test→master 时先提醒红线，坚持则说明风险后执行
- 合 test 出现大量与本次改动无关的冲突：不硬合，`git merge --abort` 退出，向用户说明可能是分叉/直接改 test 导致，建议找责任人确认或重建 test
- 多人协作：需求主分支是唯一出口（唯一可合 test/master 的分支），个人子分支只向上合需求主分支（MR + 负责人 review）；同步 master 收敛到主分支一人执行
- 紧急修复：从 master 拉 `姓名拼音/hotfix-描述/日期`，修复后分别合 test（回归）与 master（上线），删分支
