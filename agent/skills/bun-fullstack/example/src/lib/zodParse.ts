import { G } from "@diqye/gpress"
import z from "zod"

// gpress 零依赖不随包提供，app 层自持的校验组合子
export const zodParse = <S extends z.ZodType>(schema: S) =>
  (json: unknown): G<z.output<S>> => {
    const parsed = schema.safeParse(json)
    if (!parsed.success)
      throw G.error({ httpcode: 400, code: "VALIDATION", message: z.prettifyError(parsed.error) })
    return G.pure(parsed.data)
  }

// query string 版：searchParams → 对象后校验
export const zodQuery = <S extends z.ZodType>(schema: S) =>
  (url: URL): G<z.output<S>> => zodParse(schema)(Object.fromEntries(url.searchParams))
