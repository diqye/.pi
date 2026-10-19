---
name: code-philosophy
description: 如何写代码的工程哲学与规范：架构演进、数据流、数据建模、复用与模块边界、注释规范。在编写、修改、审查任何代码，或进行架构设计、代码审查、重构时使用。
---

# Code Philosophy

语言无关的通用规范。TS 专属规范见 [ts.md](ts.md)，React 专属规范见 [react.md](react.md)。

## Evolution

- Implement each feature in the context of the whole system: consider architecture, extensibility, and consistency, not only the immediate requirement.
- Global optimality is reached through iterative refinement: use each feature to reassess and improve prior decisions rather than treating them as fixed.

## Data Flow

- **Simple and direct, no event bus**: a single callback solves communication. No EventEmitter, no listener arrays. Pass only what's needed — a hook is just a function

## Data Modeling

- **Distinct business cases get distinct types — one entry per case**: model the variants of a domain as a union where each scenario is a self-sufficient variant with its own discriminant entry. Field types are reusable across variants, but the **entries are not**: never collapse scenarios into one loose shape with optional fields or implicit defaults — that hides business semantics in field-combination matrices and forces every consumer to guess
- Exhaustiveness at consumption: every consumer branches on the discriminant, so adding a variant without updating all consumers is a compile/test error, not a runtime surprise
- **External data validates once at the boundary; internal data trusts its type**: data crossing a system boundary (files, API, LLM output) is parsed/validated exactly once, and the validation result becomes the single source of truth for its shape. After the boundary, plain type definitions — no runtime re-validation, no defensive fallbacks

## Reuse

- Reuse code with tool value: abstract, single-responsibility utilities (e.g., `map`) - this is what belongs in shared/common functions
- **Prefer runtime built-ins before adding dependencies**: check Bun/Node/browser/Web-standard APIs first (e.g., `Bun.YAML.parse` vs the `yaml` package, `node:fs` renameSync vs a library). Verify on the actual runtime version — stale memory about what's "built-in" causes needless dependencies
- Share by **same business domain**, not by same code shape
- Entry source files serve as a clear logic overview
- Use the entry file to orchestrate sub-logic; sub-logic modules should not import one another.
- Sibling reuse goes through **injection**: the parent passes shared functions/interfaces into sub-logic modules, which call the injected code directly — never sideways imports
- Imports specify where each piece of logic lives
- This structure is recursive (tree-shaped): when a sub-logic module grows complex, it becomes the entry for its own sub-logic, repeating the same rules at every level

## Comments

1. Intuitive code needs no comments
2. Non-intuitive code must explain **why**, not what
3. Comment the intent behind hacks, trade-offs, edge cases, or counterintuitive writes — not a restatement of the code
4. **Comments live next to the code they describe (single source of truth)**: structural inventories maintained in a distant header comment (route tables, file lists, API summaries) WILL drift from reality — put per-item comments at the point of registration/definition instead. Drop comments that merely duplicate the nearby one; keep only those carrying independent information
