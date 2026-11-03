import { useEffect, useState } from "react"
import { Clock3, RefreshCw, Timer, MapPin } from "lucide-react"
import { TimeData } from "../../const.ts"
import { apiGet } from "../lib.ts"

export default function TimePage() {
  const [data, setData] = useState<TimeData | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setData(await apiGet(TimeData, "/api/time"))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-10 text-center shadow-2xl">
        <Clock3 className="mx-auto mb-4 size-10 text-emerald-400" />
        {data ? (
          <p className="font-mono text-2xl font-bold tracking-tight text-emerald-300">{data.now}</p>
        ) : (
          <p className="text-gray-500">loading…</p>
        )}
        {error && <p className="mt-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400">{error}</p>}
      </div>

      {data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-5">
            <Timer className="size-5 shrink-0 text-gray-400" />
            <div>
              <dt className="text-xs uppercase tracking-wider text-gray-500">ISO Time</dt>
              <dd className="font-mono text-sm text-gray-200">{data.now}</dd>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-5">
            <MapPin className="size-5 shrink-0 text-gray-400" />
            <div>
              <dt className="text-xs uppercase tracking-wider text-gray-500">Timezone</dt>
              <dd className="font-mono text-sm text-gray-200">{data.timezone}</dd>
            </div>
          </div>
        </div>
      )}

      <div className="text-center">
        <button
          onClick={load}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-5 py-2.5 font-medium text-gray-950 transition-colors hover:bg-emerald-300"
        >
          <RefreshCw className="size-4" />
          刷新
        </button>
      </div>
    </section>
  )
}
