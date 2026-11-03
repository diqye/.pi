import { lazy, Suspense } from "react"
import { Route, Router, Switch, Link, useLocation } from "wouter"
import { Clock, Globe, Info, Sparkles } from "lucide-react"
import { BASE_PATH } from "../const.ts"

// code split：每个路由一个 chunk
const HelloPage = lazy(() => import("./pages/HelloPage.tsx"))
const AboutPage = lazy(() => import("./pages/AboutPage.tsx"))
const TimePage = lazy(() => import("./pages/TimePage.tsx"))

const NAV = [
  { path: "/", label: "Hello", icon: Sparkles },
  { path: "/about", label: "About", icon: Info },
  { path: "/time", label: "Time", icon: Clock },
] as const

function Nav() {
  const [location] = useLocation()
  return (
    <header className="sticky top-0 z-10 border-b border-white/10 bg-gray-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
        <span className="flex items-center gap-2 font-mono text-sm text-gray-400">
          <Globe className="size-4 text-emerald-400" />
          bun-fullsack
        </span>
        <nav className="flex gap-2">
          {NAV.map(({ path, label, icon: Icon }) => {
            const active = location === path
            return (
              <Link
                key={path}
                href={path}
                className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm transition-colors ${
                  active ? "bg-emerald-400 font-medium text-gray-950" : "text-gray-300 hover:bg-white/10"
                }`}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

export function App() {
  return (
    // base：浏览器地址栏带 BASE_PATH，Router 内部按剥掉前缀的路径匹配
    <Router base={BASE_PATH}>
      <div className="min-h-screen bg-gray-950 text-gray-100 [background-image:radial-gradient(ellipse_at_top,rgba(16,185,129,0.12),transparent_60%)]">
        <Nav />
        <main className="mx-auto max-w-3xl px-6 py-14">
          <Suspense
            fallback={
              <div className="flex justify-center py-20">
                <div className="size-6 animate-spin rounded-full border-2 border-gray-700 border-t-emerald-400" />
              </div>
            }
          >
            <Switch>
              <Route path="/" component={HelloPage} />
              <Route path="/about" component={AboutPage} />
              <Route path="/time" component={TimePage} />
              <Route>
                <p className="text-gray-400">404 not found</p>
              </Route>
            </Switch>
          </Suspense>
        </main>
        <footer className="pb-8 text-center font-mono text-xs text-gray-600">
          bun · react 19 · wouter 3 · gpress · tailwind 4 · zod 4
        </footer>
      </div>
    </Router>
  )
}
