import { G } from "@diqye/gpress"
import { z } from "zod"
import { zodParse, zodQuery } from "../lib/zodParse.ts"
import { AboutData, GreetBody, GreetData, HelloData, HelloQuery, TimeData } from "../const.ts"

// handler 纯函数：输入是 parse 后的 z.output，输出满足响应 schema
function hello({ name }: z.output<typeof HelloQuery>): HelloData {
  return { message: `Hello, ${name}!` }
}

function greet({ name }: z.output<typeof GreetBody>): GreetData {
  return { message: `Greetings, ${name}. Welcome to bun-fullsack.` }
}

function about(): AboutData {
  return {
    name: "bun-fullsack",
    description: "Bun 单进程全栈 hello world：React + wouter + gpress + tailwind",
    stack: ["Bun", "React 19", "wouter 3", "gpress", "Tailwind 4", "zod 4"],
  }
}

function time(): TimeData {
  return { now: new Date().toISOString(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }
}

// 路由 + method 组合树，一处集中
export const apiTree = G.path("/api").semiBind(G.alts(
  G.ePath("/hello").get().requestUrl().bind(zodQuery(HelloQuery)).map(hello).map(Response.json),
  G.ePath("/greet").post().requestJson().bind(zodParse(GreetBody)).map(greet).map(Response.json),
  G.ePath("/about").get().map(about).map(Response.json),
  G.ePath("/time").get().map(time).map(Response.json),
))
