# ~/.pi 仓库指令

## 扩展开发

- 扩展的 npm 依赖统一装在仓库根：`cd ~/.pi && bun add <pkg>`。禁止在 `agent/extensions/<name>/` 内创建 package.json / node_modules / bun.lock / tsconfig.json——扩展目录只放源码，node_modules 靠向上解析命中仓库根
- 类型检查直接 `cd ~/.pi && bunx tsc`，根 tsconfig 已 include `agent/extensions/**`，无需在扩展目录另建配置
- 带后台资源的扩展：资源（timer/watcher/连接）在 `session_start` 启动、`session_shutdown` 销毁，不在 factory 里启动
- 自定义工具默认 OFF：`session_start` 里 `setActiveTools` 移除自己，由用户在 `/tools` 手动开启（同 mcp-bridge、schedule-prompt 模式）
