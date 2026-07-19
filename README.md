# Mensura

Mensura is an open-source, local-first and self-hostable agentic development platform. It is intended to combine a desktop developer workspace, controlled agent execution, durable project memory, mandatory quality gates, and an open plugin ecosystem.

The repository is at the foundation stage. The current runnable components are `@mensura/shared-types` and the minimal Python 3.12 Mensura Core HTTP API. Core currently stores workspaces, tasks, and queued placeholder runs in process memory; it does not orchestrate agents or persist data across restarts.

## Repository map

- `packages/shared-types`: shared domain contracts, state machines, and runtime plugin manifest validation.
- `services/core`: versioned FastAPI resource contracts, RFC 9457 errors, in-memory repositories, and API tests.
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

`pnpm check` typechecks, tests, and builds the JavaScript workspace. Core has a separate Python 3.12 environment and check documented in `services/core/README.md`.

## Working principles

- Deliver one observable vertical slice at a time.
- Keep service boundaries explicit and shared contracts versioned.
- Record only working functionality as implemented.
- Update `docs/agent_memory.md` after every meaningful implementation step.
- Preserve human review, structured logs, and Guard checks in task completion flows.

## Core API

See `services/core/README.md` for Python 3.12 setup, tests, run commands, implemented endpoints, and the current in-memory limitation.
