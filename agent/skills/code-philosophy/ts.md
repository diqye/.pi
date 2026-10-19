# TypeScript 规范

## Entry & CLI

1. **Active code concentrates in `main()`**: top level of an entry file should be nothing but `await main()` — reading the file gives an immediate logic overview. Resources (sockets, handles) are cleaned up in `try/finally`
2. **CLI args use `parseArgs` from `node:util`** — never hand-roll `process.argv` slicing
3. **Model CLI/domain commands as a union type + dispatch table**: `type Command = "status" | "on" | ...`, narrow with a type guard at the entry, then `Record<Command, Handler>` for dispatch. Adding a new command without a handler is a compile error — exhaustiveness without switch-case
4. **Validate args early and fail fast**: error messages tell the user the legal values, not just "invalid"

## Verification Loop

- **Every change must pass both checks**: `bunx tsc --noEmit` (project tsconfig, strict) AND an actual run. Type check alone can miss runtime/protocol issues; running alone misses type regressions
- Run `tsc` without passing file names — passing a file makes tsc ignore the project tsconfig and fall back to ES5 defaults, producing false errors

## TypeScript

1. Use early returns for readable control flow
2. Never use switch-case
3. Leverage the type system for compile-time checks: `satisfies T[]` for inline literal validation, `x satisfies never` for exhaustiveness — zero runtime overhead
4. External data (files, API, LLM output) crosses zod once at the boundary (see SKILL.md "Data Modeling"; `z.discriminatedUnion` + `z.infer` keeps schema and type one declaration); internal data is plain `type` definitions — no runtime re-validation, no defensive `?? fallback` downstream of the boundary
5. **Type-driven, define once consume everywhere**: define a Zod schema once, export the TS type derived from the schema. Never duplicate interface and schema — eliminate definition drift
6. **Strictly validate external input**: external data (HTTP body, file content, IPC messages) must be parsed before use. Never trust raw JSON. Schema failure should fail fast
7. **Prefer `type` over `interface`**: use type aliases (`type Foo = { ... }`) by default; interface only when declaration merging or extending an external interface is genuinely needed
