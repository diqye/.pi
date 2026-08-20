---
name: pi-paths
description: 查询 pi 安装位置、配置目录、命令软链、examples/docs 路径。用于定位 pi 的安装产物、修改全局配置或记忆、查找 examples 示例时使用。
---

# pi 路径与配置

## 安装位置(bun 全局)
- `/Users/diqye/.bun/install/global/node_modules/@earendil-works/pi-coding-agent`
- `pi` 命令软链 → 该目录 `dist/cli.js`
- examples / docs 都在此目录下(如 `examples/extensions/subagent/`)
- README 里的相对路径(如 `../pi-coding-agent/examples/...`)是相对 pi 源码仓库根,本机改用上面的绝对路径

## 配置目录:`~/.pi/agent`
- 全局记忆/指令:`AGENTS.md`
- 全局模型配置:`models.json`
- 认证:`auth.json`
