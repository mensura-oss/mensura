# Mensura

Mensura is an open-source, local-first and self-hostable agentic development platform. It is intended to combine a desktop developer workspace, controlled agent execution, durable project memory, mandatory quality gates, and an open plugin ecosystem.

The repository is at the foundation stage. The current runnable component is `@mensura/shared-types`, which defines and tests the domain state transitions and plugin manifest validation that future Studio and service modules will share. Product behavior beyond those contracts is planned, not yet implemented.

## Repository map

- `packages/shared-types`: shared domain contracts, state machines, and runtime plugin manifest validation.
- `docs/agent_memory.md`: current architecture, audit, implementation journal, decisions, and ordered next tasks.
- `mensura_*.md`: product, architecture, API, module, roadmap, and setup source specifications.
- `LICENSE`: GNU AGPL v3.

Target directories such as `apps/studio` and `services/core` will be added when they contain runnable code. See `mensura_monorepo_structure.md` for the intended full layout.

## Prerequisites

- Node.js 22 or newer.
- pnpm 11 or newer.

The future Core service additionally requires Python 3.12+, and Studio will require the Rust toolchain and Tauri platform prerequisites.

## Start here

```sh
pnpm install
pnpm check
```

`pnpm check` typechecks, tests, and builds every implemented workspace package. A clean run is the current repository health check.

## Working principles

- Deliver one observable vertical slice at a time.
- Keep service boundaries explicit and shared contracts versioned.
- Record only working functionality as implemented.
- Update `docs/agent_memory.md` after every meaningful implementation step.
- Preserve human review, structured logs, and Guard checks in task completion flows.

## Next implementation target

Define the minimum versioned Core API contracts, then create a Python 3.12 FastAPI service with health and local workspace/task/run behavior. The service should consume the same domain state model represented by `@mensura/shared-types` rather than inventing an incompatible lifecycle.
