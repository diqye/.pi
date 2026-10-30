---
name: bun-fullstack
description: Bun 单进程全栈项目规范(gpress + wouter + lucide-react + tailwind + 内嵌 pi agent)与构建部署模式。新建全栈项目、接 gpress、嵌入 pi、写 build/deploy 脚本时使用,基于 lime 项目沉淀。
---

# Bun 全栈项目规范(lime 模式)

单进程全栈:server 与前端同仓同进程,Bun 原生 HTML import,无 vite/独立前端 dev server。

## 目录骨架

```
src/
  index.ts          # 入口:serve() 路由表(WS 升级 / "/api/*" / "/*" SPA fallback)
  index.html        # 前端壳:<script type="module" src="./web/frontend.tsx">
  server/           # 后端:handler 纯函数 + 组合树;config/data 内存态 + 落盘
  web/              # 前端:frontend.tsx 入口、App.tsx 路由、components/ hooks/ lib/
  lib/gpress/       # vendored:gpress 仓库原样拷贝,保持纯上游
  lib/zodParse.ts   # zod 校验组合子(上游为零依赖移除了 zodParse)
build.ts            # 产出 dist/(minified bundle + 外置依赖 package.json)
scripts/deploy.ts   # 一键部署(仅用户手工执行)
```

## 三个 const.ts 的分工(归属判据:谁引用谁持有)

- `src/const.ts`:前后端共享的类型与常量(API 协议层:实体 State、权限位、工具 id 等);改协议两端同步看
- `src/server/const.ts`:仅后端引用的常量与 zod schema(CONFIG_ROOT、安全等级全集、请求 schema)
- `src/web/const.ts`:仅前端引用的常量与类型(localStorage 键、UI 展示定义/图标 key)
- 请求 body 的 zod schema 放 server/const,但**改字段必须同步对应 schema**,否则 zod 静默剥掉未知字段,下游永远 undefined(无报错极难排查)

## 依赖选型

react 19 + react-dom / **wouter 3**(SPA 路由)/ **lucide-react**(图标,按需 import)/ tailwindcss 4 + bun-plugin-tailwind / zod 4 / @earendil-works/pi-coding-agent + @earendil-works/pi-ai(内嵌 agent)。
注意包名是 lucide-react 与 wouter,没有 react-lucide / wroute。

## gpress 接入

- vendored 拷贝 gpress 仓库 `src/Gpress.ts` → `src/lib/gpress/`,**零本地改动**;上游更新 = 直接覆盖拷贝
- body 校验:`G.requestJson().bind(zodParse(Schema))`;失败 throw G.error,runWith404 统一转 400 JSON
- 业务错误直接 `throw G.error({ httpcode, code, message })`,任意深度的普通函数都能抛;未捕获异常 runWith404 兜底 500,handler 不写 try/catch
- 组合树分层:handler 纯函数(body/url 自取);路由 + method 集中组合树一处,就近注释
- 路由通配 / 前缀:`G.path("/api")` 嵌 `G.path("/pub")` 即 `/api/pub/*`
- **WS 鉴权分层**(详见 vendored README「WebSocket 复用鉴权」):`authInfoOf`(token→鉴权信息)是领域核心纯函数;`authed` guard 是它的 HTTP 适配层;WS 升级不走路由,首帧直连核心(不造 Request、不解析 Response)。两道防护必备:open 起 10s 计时器,未完成首帧认证则断开(防裸连堆积);认证前只认 auth 帧,业务帧一律丢弃。只有要复用一整串不可拆的 guard 组合(限流+鉴权+租户)才造 Request 跑 `guard.runWith404(req)`

## 前端

- wouter:`Route/Switch`;通配路由用 `*rest` 语法(`:rest*` 是 regexparam 旧写法,只匹配单段,子目录全 404)
- tailwind v4:`index.css` 首行 `@import "tailwindcss"`,无 tailwind.config
- `--hot` 下 createRoot 挂 `import.meta.hot.data`( `(import.meta.hot.data.root ??= createRoot(elem)).render(app)`)防重复挂载
- fetch 封装统一识别 `!res.ok || body.error != null || body.code != null`,别只看状态码(gpress 错误体带 code/message)

## 内嵌 pi agent

- `createAgentSession({...})` + `SessionManager.open(sessionFile, undefined, cwd)`;会话 jsonl 持久化于 `~/.config/<app>/session/<key>.jsonl`,存在则续聊
- 工具开关走 `setActiveToolsByName` 即时生效,不靠会话重建;自定义工具写 ToolDefinition
- **build 必须 external** `@earendil-works/pi-coding-agent` 与 `pi-ai`(运行时动态加载多:技能扫描/provider/模板,打进 bundle 风险大);版本从根 package.json 读出写进 `dist/package.json`,目标机 `bun install --production` 后运行

## 构建 build.ts

- `Bun.build({ entrypoints:["./src/index.ts"], target:"bun", minify:true, sourcemap:"none", plugins:[tailwind], external:[pi 两个], define:{ "process.env.NODE_ENV": JSON.stringify("production") } })`
- **publicPath 必须 "/"**:SPA 深层路由下相对路径资产被解析进路由路径,SPA fallback 返 HTML 报 MIME 错(实踩)
- 运行时读盘的资源(pre-skills/、CHANGELOG.md 等)`cp` 进 dist,目标机从 dist 起 cwd 优先解析
- 产物只有 `index.js + package.json + 静态资源`,不带源码;sourcemap "none"(linked 模式的 .map 即原始源码)

## 部署 scripts/deploy.ts(仅用户手工执行,AI 只改脚本不运行)

模式:本地 build → rsync dist → 远端 bun install → pm2。两个 ssh 坑(勿回退):

1. 不套 `ssh host bash -lc "..."` —— 引号经远端重新分词会丢,命令只剩第一个词且检测永远 exit 0;整条命令作为单参数过 `Bun.$`ssh host ${cmd}``,由远端 shell 自己分词
2. 远端 profile 常无 `~/.bun/bin`,每条命令前置 `export PATH="$HOME/.bun/bin:$PATH"`

- rsync:`-az --delete --exclude=node_modules dist/ host:dir/`(node_modules 远端生成,被 --delete 会每次全量重装)
- pm2 存在性判断用 `pm2 jlist | grep -q '"name":"xxx"'`(`pm2 pid` 对不存在的名字也 exit 0)
- restart 失败("Process N not found",元数据在、运行表无)→ `pm2 delete` + `start` 重建
- `pm2 start <bun绝对路径> --name x --max-memory-restart 4G -- run index.js`(绝对路径落库,restart 不依赖 daemon PATH);收尾 `pm2 save`
- **运行时数据(`~/.config/<app>/`)不经部署链路**,更新部署不影响配置与会话

## 配置与数据落盘

- 配置根唯一落点:`src/server/const.ts` 的 `CONFIG_ROOT = ~/.config/<app>`,禁止各处写死
- 启动读一次进内存,写操作改内存 + persist 落盘,经 `withFileLock` 单进程串行化
- 直接手改配置文件会被运行中进程的下次落盘覆盖;手改后必须重启(先停再改更稳)

## Dev 工作流

- `bun --hot src/index.ts` 起服务;**--hot 有状态分裂坑**(内存单例/config 单例读到旧实例,代码明明改了行为不变),先重启再排查
- 类型检查 `bunx tsc --noEmit`;改 server 代码由用户自己重启验证
