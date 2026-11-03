import { z } from "zod"

// 应用挂载前缀（反向代理挂在 /app 下）：
// 浏览器侧所有引用（路由/接口/资产）带前缀；服务端统一剥掉后路由，代理剥或不剥前缀都能工作
// 唯一读取点，跟 .env 同步；改值后必须重新 build（前端 bundle 编译期固化）
export const BASE_PATH: string = process.env.APP_BASE_PATH ?? "/app"

// 唯一定义点。数据流向约定：
//   请求：前端构造 z.input → 后端 parse 后拿 z.output
//   响应：服务端构造 z.input → 前端 parse 后拿 z.output
// 响应 schema 必须保持无 transform/default（z.input === z.output），两端才可共用 z.infer；
// 一旦给响应 schema 加 transform，服务端构造端要用 z.input，前端解析端用 z.output，不能再共用

export const HelloQuery = z.object({
  name: z.string().trim().min(1, "name 不能为空").max(32, "name 最长 32 字符").default("World"),
})
export type HelloQueryInput = z.input<typeof HelloQuery>
export type HelloQueryOutput = z.output<typeof HelloQuery>

export const GreetBody = z.object({
  name: z.string().trim().min(1, "name 不能为空").max(32, "name 最长 32 字符"),
})
export type GreetBodyInput = z.input<typeof GreetBody>
export type GreetBodyOutput = z.output<typeof GreetBody>

export const HelloData = z.object({ message: z.string() })
export type HelloData = z.infer<typeof HelloData>

export const GreetData = z.object({ message: z.string() })
export type GreetData = z.infer<typeof GreetData>

export const AboutData = z.object({
  name: z.string(),
  description: z.string(),
  stack: z.string().array(),
})
export type AboutData = z.infer<typeof AboutData>

export const TimeData = z.object({
  now: z.string(),
  timezone: z.string(),
})
export type TimeData = z.infer<typeof TimeData>
