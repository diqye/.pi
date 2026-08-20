---
name: code-philosophy
description: 如何写代码的工程哲学与规范：架构演进、数据流（无事件总线）、复用与模块边界、TypeScript/React/注释规范。在编写、修改、审查 TypeScript 或 React 代码，或进行架构设计、代码审查、重构时使用。
---

# Code Philosophy

## Evolution

- Implement each feature in the context of the whole system: consider architecture, extensibility, and consistency, not only the immediate requirement.
- Global optimality is reached through iterative refinement: use each feature to reassess and improve prior decisions rather than treating them as fixed.

## Data Flow

- **Simple and direct, no event bus**: a single callback solves communication. No EventEmitter, no listener arrays. Pass only what's needed — a hook is just a function

## Reuse

- Reuse code with tool value: abstract, single-responsibility utilities (e.g., `map`) - this is what belongs in shared/common functions
- Share by **same business domain**, not by same code shape
- Entry source files serve as a clear logic overview
- Use the entry file to orchestrate sub-logic; sub-logic modules should not import one another.
- Imports specify where each piece of logic lives
- This structure is recursive (tree-shaped): when a sub-logic module grows complex, it becomes the entry for its own sub-logic, repeating the same rules at every level

## TypeScript

1. Use early returns for readable control flow
2. Never use switch-case
3. Leverage the type system for compile-time checks: `satisfies T[]` for inline literal validation, `x satisfies never` for exhaustiveness — zero runtime overhead
4. Validate external data with zod
5. **Type-driven, define once consume everywhere**: define a Zod schema once, export the TS type derived from the schema. Never duplicate interface and schema — eliminate definition drift
6. **Strictly validate external input**: external data (HTTP body, file content, IPC messages) must be parsed before use. Never trust raw JSON. Schema failure should fail fast
7. **Prefer `type` over `interface`**: use type aliases (`type Foo = { ... }`) by default; interface only when declaration merging or extending an external interface is genuinely needed

## Comments

1. Intuitive code needs no comments
2. Non-intuitive code must explain **why**, not what
3. Comment the intent behind hacks, trade-offs, edge cases, or counterintuitive writes — not a restatement of the code

## React

1. Prefer pure function components
2. For complex business logic, use hook injection pattern:
   - Each UI component has a corresponding hook (e.g., `UserList` ↔ `useUserList`)
   - Hooks are injected from outside via a `hook` prop
   - Hooks are composable with each other
