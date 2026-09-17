---
name: bun
description: Bun 运行时规范与问题排查。跑脚本/服务、包管理、测试、类型检查、写 Bun API 代码、选依赖、遇到 bun --hot 热重载状态诡异等问题时使用。
---

# Bun

## 运行时规范

优先 Bun,不用 node/npm/npx/ts-node:
- 跑脚本/服务 `bun`,包执行 `bunx`,测试 `bun test`,类型检查 `bunx tsc`
- 包路径 `bun pm ls -g` / `require.resolve`
- 文件 `Bun.file()`,SQLite `bun:sqlite`,HTTP `Bun.serve()`
- 仅 Bun 不支持时 fallback node

## 内建优先

加依赖前先查运行时内建:Bun / Node / Web 标准 API(如 `Bun.YAML.parse` vs `yaml` 包,`node:fs` renameSync vs 第三方库)。以当前版本实际验证为准——过时记忆里"不是内建"的东西可能已经内建,无谓引依赖。

## 问题排查

**bun --hot 热重载有 bug。遇到诡异问题,先重启 dev server,多数即好,不要花时间排查代码。**

### 已知症状(都是 --hot 引起,重启即愈)

- **模块状态分裂**:模块级 `let` 变量 / `Map` / 单例在热重载后"分裂"——旧闭包(其他模块的 import)引用旧模块实例,新代码写新实例。表现为:A 接口能读到的状态,B 接口读不到;刚写入的数据下次请求就消失
- **改动不生效**:改了源码,部分 handler 仍跑旧逻辑(同上原因,旧闭包未更新)
- **跨请求行为不一致**:同一逻辑不同请求结果不同,稳定复现且代码审查无任何问题
- EADDRINUSE:旧进程未死透,`pkill` 后稍等再启

### 排查顺序

1. 代码快速 review 一遍,逻辑确实没问题 → 直接重启,别深挖
2. 重启方式:
   ```bash
   pkill -f "bun --hot src/index.ts"; sleep 1; bun run dev
   ```
3. 重启后仍复现才是真 bug,正常排查

### 原理(简)

`--hot` 保留事件循环与已加载模块实例,热替换时新代码生成新模块实例,但引用旧模块的其他模块闭包未必同步更新 → 同一变量存在两份。`--watch` 是整进程重启,无此问题(但会丢全部内存状态,本来也应丢)。

### 真实案例

2025-09 lime 项目:feishu.ts 模块级 `chatsError`,`POST /api/im/chats/refresh` 能读到、`GET /api/im/state` 读不到(恒 null),稳定复现;代码无任何问题,重启后恢复正常。

### 附带经验

- 服务端口占用报错先 `ps aux | grep src/index.ts` 确认旧进程
- 内存态(token、缓存)重启即清,属预期行为,不算 bug
