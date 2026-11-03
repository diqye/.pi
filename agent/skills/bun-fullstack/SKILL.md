---
name: bun-fullstack
description: Bun 单进程全栈项目(gpress + wouter + lucide-react + tailwind + zod)。新建全栈项目、接 gpress、写 build/dev 脚本、排查 tailwind/splitting/publicPath/BASE_PATH 问题时使用。以 example/ 完整可跑项目为模板。
---

# Bun 全栈项目(模板驱动)

**核心方法：先看 example/，再读本文件的踩坑结论。** example/ 是一个完整可跑的最小实现(三页面 + API + code split + BASE_PATH 挂载)，本文件只讲"为什么"——规范没有例子会腐烂，例子没有结论会看不懂。

```
example/
  bunfig.toml        # dev server 的 tailwind 插件 + env 注入声明
  build.ts           # 单次 Bun.build + html 资产前缀改写
  tsconfig.json
  package.json       # dev / build / start / typecheck
  .env               # APP_BASE_PATH=/app
  src/
    index.ts         # Bun.serve 路由表(3 条,全站入口)
    index.html       # 前端壳,<script src="./web/frontend.tsx">
    const.ts         # 前后端共享:zod schema + BASE_PATH(唯一读取点)
    server/api.ts    # gpress handler 纯函数 + 组合树
    server/const.ts  # 仅服务端常量(PORT)
    lib/zodParse.ts  # gpress 零依赖,校验组合子自持
    web/frontend.tsx # createRoot 入口(--hot 防重复挂载)
    web/App.tsx      # wouter Router base + lazy code split
    web/lib.ts       # fetch 封装(边界 safeParse + 错误识别)
    web/pages/       # 页面(每个一个 lazy chunk)
```

## 快速开始

```
cp -R <skill目录>/example/ <新项目>/
bun install && bun run dev     # http://localhost:3000/app
bun run build && bun run start # 生产
```

## 架构一句话

单进程 `Bun.serve`，`import html from "./index.html"` 让 Bun 原生接管前端打包(dev 自动重写为 `/_bun/*`，无需 vite)；`/api/*` 走 gpress；其余路径返回 html 壳，页面路由交给浏览器端 wouter。

## 踩坑结论(全部实证过，按主题)

### tailwind v4
- dev：`bunfig.toml` 里 `[serve.static] plugins = ["bun-plugin-tailwind"]`。**preload 无效**(插件默认导出是 BunPlugin 对象，preload 只 import 不注册，且 dev server 打包不吃 runtime preload)
- build：`Bun.build` 的 `plugins: [tailwind]`。两个注册点独立，缺一个就有一端无样式
- 不需要 `@source`：自动扫描覆盖 tsx。若 CSS 产物里 `@theme` 是原文未展开、无 utilities，说明编译没跑，先查注册点

### code split
- `splitting: true` 必须显式，默认不拆动态 import

### publicPath(最深的坑)
- **锁死 `"./"`**。服务端入口 import html 会把前端图拉进服务端 bundle，共享 chunk(zod 等)的 import 标识符按 publicPath 生成；`"/"` 或 `"/app/"` 会变成 `import{F}from"/app/chunk-x.js"`——运行时当文件系统绝对路径，**启动即崩**，cwd 都救不了
- 浏览器侧需求相反：html 内嵌引用须是绝对路径(`"./chunk"` 在深层路由 `/app/about` 下解析成 `/app/about/chunk-x` → 404)
- 解法：`publicPath: "./"` + **构建后改写** index.html 的 `"./chunk` → `` `${BASE_PATH}/chunk ``。chunk 之间的 import 是模块相对，不受影响
- **上 CDN = 换改写目标**(`https://cdn.x.com${BASE_PATH}/chunk`)，改写规则是唯一开关

### cwd 约束
- HTMLBundle 资产清单(`{"files":[{"path":"./chunk..."}]}`)按 **cwd** 解析(注意：与静态 import 的模块相对解析是两套机制)，所以 start 必须是 `cd dist && bun index.js`

### BASE_PATH(反向代理挂在子路径)
- 单一读取点 `src/const.ts`：`process.env.APP_BASE_PATH ?? "/app"`
- 浏览器没有 process.env，注入靠 APP_ 前缀机制：dev 用 `bunfig env = "APP_*"`，build 用 `Bun.build env: "APP_*"`——**前缀声明在两处，改要同步**
- 服务端路由表三条(dev/生产同形态，nginx 剥或不剥前缀都能路由)：
  ```ts
  routes: {
    "/api/*": (req: Request) => apiTree.runWith404(req),
    [BASE_PATH + "/*"]: (req: Request) => { /* 剥前缀后 fetch 重入 */ },
    "/*": html,
  }
  ```
- **routes 优先于 fetch**：`/*` 会吞掉所有路径，前缀改写放 fetch 里永远执行不到
- HTMLBundle **只能经 routes 服务**，`new Response(html)` 得到 `[object HTMLBundle]`
- nginx：`location /app/ { proxy_pass http://127.0.0.1:3000/; }`(结尾斜杠 = 剥前缀)

### 版本分裂
- `bun run <script>` 里嵌套的 `bun` 解析到 `node_modules/bun`(peer 自动安装)，可能与全局 bun 版本不一致；build 打印 `Bun.version` 便于发现

### import.meta.hot
- `.data` 只能**直接成员访问**，经变量中转报 "cannot be used indirectly"；TS 侧用 `import.meta.hot!` 断言

### gpress
- 组合子形态：`G.path("/api").semiBind(G.alts(G.ePath("/x").get().requestUrl().bind(fn).map(d => Response.json(d)), ...))`——`get()/post()` 无参，业务全在 bind
- `runWith404(req)` 恒返回 Response(HttpError→{code,message}+httpcode，其余 500，continue→404)，调用方不用判空
- 校验组合子自持：`zodParse`(body)/`zodQuery`(searchParams)在 `src/lib/zodParse.ts`，几行的事
- 注意包名：`@diqye/gpress`(npm 裸名 `gpress` 是占位包)

### zod schema 约定(前后端协议层)
- 单一定义点 `src/const.ts`，类型全部推导，**禁止手写平行 interface**
- 数据流向：请求 = 前端构造 `z.input` → 后端 parse 后拿 `z.output`；响应 = 服务端构造 → 前端边界 `safeParse` 后拿 `z.output`
- 响应 schema 必须无 transform/default(`z.input === z.output`)两端才能共用 `z.infer`；请求 schema 的 `.default()/.trim()` 正是 input/output 差异点(input 侧可缺省，output 侧必有且已 trim)
- 前端引 schema 值(响应要 parse)，zod 运行时进前端 chunk 是预期成本；请求类型用 `import type` 拿 `z.input` 不带运行时
- 请求 body schema 放共享层后记得两端同步，否则 zod 静默剥掉未知字段，下游 undefined 无报错

### fetch 封装
- 统一识别 `!res.ok || body.error != null || body.code != null`，gpress 错误体带 code/message，不能只看状态码

## 反面案例(别重蹈)

- **双 build 方案**(前端 html 入口独立 build + 服务端去 html import + 自写静态服务)：publicPath 确实只作用前端，但 dev/prod 双代码路径、动态 import 命名空间坑、自写静态服务，复杂度全部转移到运行期。被否——单 build 的 replaceAll hack 集中在 build.ts 一处，更清爽
- `publicPath: "/"` 或 `` `${BASE_PATH}/` ``：启动即崩(见上)
- `external: ["./index.html"]`：拦不住 bundler 跟进动态 import
- 手写 interface 复制 zod 类型：两份独立编译，静默漂移

## example 未覆盖、来自 lime 的补充

- **内嵌 pi agent**：`createAgentSession` + `SessionManager.open`；build 必须 external `@earendil-works/pi-coding-agent` 与 `pi-ai`，版本写进 dist/package.json，目标机 `bun install --production`
- **部署**(scripts/deploy.ts，仅用户手工执行)：本地 build → rsync `-az --delete --exclude=node_modules dist/ host:dir/` → 远端 pm2。ssh 命令整条作为单参数过 `Bun.$`，远端每条命令前置 `export PATH="$HOME/.bun/bin:$PATH"`；pm2 存在性用 `pm2 jlist | grep -q '"name":"xxx"'`
- **WS 鉴权**：见包内 README「WebSocket 复用鉴权」，authInfoOf 纯函数为核心，open 起 10s 未认证断开
- **配置落盘**：配置根唯一落点 server/const 的 `CONFIG_ROOT`，启动读一次进内存，写操作改内存+落盘
- **--hot 状态分裂坑**：改了 server 代码行为不变时，先整个重启再排查
