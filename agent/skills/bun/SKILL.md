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

## 构建已知问题

### 未修:Bun.build splitting + publicPath 污染服务端运行时 import

`splitting: true` + `publicPath` 会给**所有** chunk 引用加前缀,包括 target:"bun" 服务端入口 bundle 里的运行时 import。文档定义 publicPath 就是加在全部导入路径上,不区分浏览器/服务端语义 → 按文档算 by design;1.3.14 实测未修,1.4.x release notes 也无相关修复。

- `publicPath="/"` → 产物含 `import("/chunk-x.js")`,运行时按文件系统解析绝对路径 → 启动即崩
- `publicPath="https://cdn…/"` → 产物含 `import("https://…/chunk-x.js")`,Bun 支持 https import 不会崩,但服务端冷启动去网络拉自己的代码(CDN 挂 = 服务挂,极隐蔽)

行为细节(1.3.14 实测):

- **chunk 引用 chunk 是常态**:共享依赖抽成公共 chunk 后,引用方(含动态 import 产物,字面量 `import("/chunk-x.js")`)直接引它,同样带前缀
- 服务端可达闭包(入口 → chunk → chunk)里任何一处带前缀引用都会出事;好在产物里 chunk 引用全是明文字符串,文本扫描可完整枚举

目前仅 dogdog.work 有项目级缓解(2026-10:build 后把 dist/index.js 里 `"/chunk-` 文本替换回 `"./`),成立前提是服务端可达 chunk 无内部引用——恰好成立,非结构保证;CDN 形态该替换匹配不到。通用方案未定,勿照抄。
