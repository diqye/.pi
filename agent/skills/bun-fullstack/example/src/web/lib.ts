import { z } from "zod"
import { BASE_PATH } from "../const.ts"

// 前端边界：所有请求统一拼 BASE_PATH（代理挂在前缀下时根绝对路径会逃出代理范围）
async function request<S extends z.ZodType>(schema: S, path: string, init?: RequestInit): Promise<z.output<S>> {
  const res = await fetch(BASE_PATH + path, init)
  const body = await res.json()
  if (!res.ok || body.error != null || body.code != null) {
    throw new Error(body?.message ?? `request failed: ${res.status}`)
  }
  const parsed = schema.safeParse(body)
  if (!parsed.success) {
    throw new Error(`invalid response: ${z.prettifyError(parsed.error)}`)
  }
  return parsed.data
}

export function apiGet<S extends z.ZodType>(schema: S, path: string): Promise<z.output<S>> {
  return request(schema, path)
}

export function apiPost<S extends z.ZodType>(schema: S, path: string, body: unknown): Promise<z.output<S>> {
  return request(schema, path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  })
}
