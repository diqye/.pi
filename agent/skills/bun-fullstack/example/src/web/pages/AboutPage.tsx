import { useEffect, useState } from "react"
import { Layers } from "lucide-react"
import { AboutData } from "../../const.ts"
import { apiGet } from "../lib.ts"

export default function AboutPage() {
  const [data, setData] = useState<AboutData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet(AboutData, "/api/about").then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <p className="rounded-lg bg-red-500/10 px-4 py-2 text-red-400">{error}</p>
  if (!data) return <p className="text-gray-500">loading…</p>

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-10">
        <h1 className="mb-3 font-mono text-3xl font-bold text-emerald-300">{data.name}</h1>
        <p className="text-gray-300">{data.description}</p>
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-gray-400">
          <Layers className="size-4" />
          Tech Stack
        </h2>
        <div className="flex flex-wrap gap-2">
          {data.stack.map((s) => (
            <span
              key={s}
              className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3.5 py-1.5 font-mono text-sm text-emerald-300"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
