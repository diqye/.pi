import { useEffect, useState } from "react"
import { Hand, Send } from "lucide-react"
import type { GreetBodyInput, HelloQueryInput } from "../../const.ts"
import { GreetData, HelloData } from "../../const.ts"
import { apiGet, apiPost } from "../lib.ts"

export default function HelloPage() {
  // HelloQueryInput.name 因 .default() 可缺省，这里手动维护为 string
  const [name, setName] = useState("")
  const [data, setData] = useState<HelloData | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      const query: HelloQueryInput = name ? { name } : {}
      setData(await apiGet(HelloData, `/api/hello${query.name ? `?name=${encodeURIComponent(query.name)}` : ""}`))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  async function greet() {
    try {
      const body: GreetBodyInput = { name: name || "World" }
      setData(await apiPost(GreetData, "/api/greet", body))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-10 text-center shadow-2xl">
        <Hand className="mx-auto mb-4 size-10 text-emerald-400" />
        <h1 className="text-4xl font-bold tracking-tight">
          {data ? <span className="text-emerald-300">{data.message}</span> : "loading…"}
        </h1>
        {error && <p className="mt-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400">{error}</p>}
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-6 sm:flex-row">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="输入名字（zod 查询参数校验）"
          className="flex-1 rounded-lg border border-white/10 bg-gray-900 px-4 py-2.5 text-gray-100 placeholder:text-gray-600 focus:border-emerald-400/60 focus:outline-none"
        />
        <button
          onClick={load}
          className="rounded-lg bg-emerald-400 px-5 py-2.5 font-medium text-gray-950 transition-colors hover:bg-emerald-300"
        >
          GET /hello
        </button>
        <button
          onClick={greet}
          className="flex items-center justify-center gap-2 rounded-lg border border-white/15 px-5 py-2.5 font-medium text-gray-200 transition-colors hover:bg-white/10"
        >
          <Send className="size-4" />
          POST /greet
        </button>
      </div>
    </section>
  )
}
