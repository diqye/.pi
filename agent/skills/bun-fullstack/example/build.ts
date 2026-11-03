/**
 * 构建产物:dist/(服务端单文件 + 前端 chunk + 编译后的 css + index.html)
 * 运行:cd dist && bun index.js(静态资产按 cwd 解析,必须以 dist 为 cwd)
 */

import tailwind from "bun-plugin-tailwind"
import { rm } from "node:fs/promises"
import path from "node:path"
import { BASE_PATH } from "./src/const.ts"

const outdir = path.join(process.cwd(), "dist")
await rm(outdir, { recursive: true, force: true })

console.log(`bun v${Bun.version}`)

const result = await Bun.build({
  entrypoints: ["./src/index.ts"],
  outdir,
  plugins: [tailwind],
  // APP_* 前缀的环境变量编译期注入浏览器端 bundle（与 bunfig.toml 的 env 保持同一前缀）
  env: "APP_*",
  splitting: true,
  minify: true,
  target: "bun",
  sourcemap: "none",
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  // publicPath 必须 "./"（"/" 或 "/app/" 会让服务端按文件系统绝对路径找 chunk 直接崩）。
  // 浏览器侧需求不同：html 内嵌引用须是带 BASE_PATH 的绝对路径（"./chunk" 在深层路由
  // /app/about 下会解析成 /app/about/chunk-xxx 导致 404），故构建后统一改写。
  // chunk 之间的 import 是模块相对，不受页面路由影响，无需处理。
  // 上 CDN 时把改写目标换成 CDN 域名即可，改写规则是唯一开关
  publicPath: "./",
})

if (!result.success) {
  console.error(result.logs)
  process.exit(1)
}

const indexPath = path.join(outdir, "index.html")
const html = await Bun.file(indexPath).text()
await Bun.write(indexPath, html.replaceAll('"./chunk', `"${BASE_PATH}/chunk`))

console.log(result.outputs.map((o) => o.path).join("\n"))
