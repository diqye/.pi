# ~/.pi 仓库指令

## 扩展开发

- 扩展的 npm 依赖统一装在仓库根：`cd ~/.pi && bun add <pkg>`。禁止在 `agent/extensions/<name>/` 内创建 package.json / node_modules / bun.lock / tsconfig.json——扩展目录只放源码，node_modules 靠向上解析命中仓库根
- 类型检查直接 `cd ~/.pi && bunx tsc`，根 tsconfig 已 include `agent/extensions/**`，无需在扩展目录另建配置
- 带后台资源的扩展：资源（timer/watcher/连接）在 `session_start` 启动、`session_shutdown` 销毁，不在 factory 里启动
- 自定义工具默认 OFF：统一由 tools.ts 的默认策略处理（见下方「工具默认策略」），各扩展无需自行 inactive 自己的工具

## 工具默认策略（收口在 tools.ts）

- 默认规则唯一来源是 tools.ts 的 session_start：保留 builtin，其余全关，用户经 /tools 手动开启
- 启动期例外唯一入口是 `PI_TOOLS_ON` 环境变量（冒号分隔工具名，如 `PI_TOOLS_ON=web_search:session_msg pi --no-session`；解析在 `agent/util/tools-env.ts`，共享引用）
- 扩展需要「默认激活工具」或「随启动初始化」时：解析同一个 env 判断，禁止读 getActiveTools 推断意图、禁止扩展间靠加载顺序传递状态
