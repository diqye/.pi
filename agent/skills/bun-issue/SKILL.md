---
name: bun-issue
description: Bun 使用中遇到的坑记录。dev server 状态诡异（bun --hot 模块状态分裂、改动不生效、跨请求行为不一致）、EADDRINUSE 端口占用、bun 构建产物问题时使用。
---

# Bun 踩坑记录

## bun --hot 热重载 bug

遇到诡异问题,先重启 dev server,多数即好,不要花时间排查代码。

### 已知症状(都是 --hot 引起,重启即愈)

- **模块状态分裂**:模块级 `let` 变量 / `Map` / 单例在热重载后"分裂"——旧闭包(其他模块的 import)引用旧模块实例,新代码写新实例。表现为:A 接口能读到的状态,B 接口读不到;刚写入的数据下次请求就消失
- **改动不生效**:改了源码,部分 handler 仍跑旧逻辑(同上原因,旧闭包未更新)
- **跨请求行为不一致**:同一逻辑不同请求结果不同,稳定复现且代码审查无任何问题
- EADDRINUSE:旧进程未死透,`ps aux | grep src/index.ts` 确认后 `pkill`,稍等再启

### 排查顺序

1. 代码快速 review 一遍,逻辑确实没问题 → 直接重启,别深挖
2. 重启方式:
   ```bash
   pkill -f "bun --hot src/index.ts"; sleep 1; bun run dev
   ```
3. 重启后仍复现才是真 bug,正常排查

### 原理(简)

`--hot` 保留事件循环与已加载模块实例,热替换时新代码生成新模块实例,但引用旧模块的其他模块闭包未必同步更新 → 同一变量存在两份。`--watch` 是整进程重启,无此问题(但会丢全部内存状态,本来也应丢)。

真实案例(2025-09 lime):feishu.ts 模块级 `chatsError`,`POST /api/im/chats/refresh` 能读到、`GET /api/im/state` 恒 null,代码无任何问题,重启恢复。

内存态(token、缓存)重启即清,属预期行为,不算 bug。

## 构建产物问题

splitting + publicPath 坑(服务端 bundle 的 chunk 引用被 publicPath 前缀污染,启动即崩或冷启动去网络拉代码)的完整症状与解法见 bun-fullstack skill 的「publicPath」段。
