import { apiTree } from "./server/api.ts"
import { BASE_PATH } from "./const.ts"
import html from "./index.html"
import { PORT } from "./server/const.ts"

// 部署形态：nginx 剥掉 BASE_PATH 后转发，服务端只见裸路径，走 /api/* 与 /*
// 本地直连：BASE_PATH 前缀路由剥掉前缀后经 fetch 重入上面的 routes
const server = Bun.serve({
  port: PORT,
  routes: {
    "/api/*": (req: Request) => apiTree.runWith404(req),
    [BASE_PATH + "/*"]: (req: Request) => {
      const url = new URL(req.url)
      url.pathname = url.pathname.slice(BASE_PATH.length)
      return fetch(url, { method: req.method, headers: req.headers, body: req.body })
    },
    "/*": html,
  },
})

console.log(`listening on http://localhost:${server.port}${BASE_PATH}`)
