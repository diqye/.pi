import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { App } from "./App.tsx"
import "./index.css"

const elem = document.getElementById("root")!
// --hot 下防重复挂载；import.meta.hot.data 只能直接成员访问（Bun 限制），不能经变量间接引用
const root = import.meta.hot
  ? ((import.meta.hot!.data.root ??= createRoot(elem)) as ReturnType<typeof createRoot>)
  : createRoot(elem)
root.render(
  <StrictMode>
    <App />
  </StrictMode>,
)
