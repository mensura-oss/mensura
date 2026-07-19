# Mensura

Mensura is an open-source, local-first and self-hostable agentic development platform. It is intended to combine a desktop developer workspace, controlled agent execution, durable project memory, mandatory quality gates, and an open plugin ecosystem.

The repository is at the foundation stage. The current runnable components are `@mensura/shared-types`, the minimal Python 3.12 Mensura Core HTTP API, and the Tauri/React Mensura Studio shell. Studio can select a workspace, inspect its local Git status, build a deterministic Vault file inventory with bounded text previews, select inventoried files into an immutable context pack, manually run configured Ruff/pytest Guard checks, create a ready task, and create a queued placeholder run. Repository and Vault access are read-only. Core still stores workspace/task/run/Guard/Vault/context-pack resources only in process memory; it does not orchestrate agents or persist data across restarts.

## Repository map

- `packages/shared-types`: shared domain contracts, state machines, and runtime plugin manifest validation.
- `apps/studio`: Tauri 2/React desktop shell and typed Core client.
- `services/core`: versioned FastAPI resource contracts, RFC 9457 errors, read-only Git/Vault adapters, immutable context-pack assembly, bounded Guard runner, in-memory resource storage, and API tests.
- `docs/agent_memory.md`: current architecture, audit, implementation journal, decisions, and ordered next tasks.
- `mensura_*.md`: product, architecture, API, module, roadmap, and setup source specifications.
- `LICENSE`: GNU AGPL v3.

Runtime directories are added only when they contain runnable code. See `mensura_monorepo_structure.md` for the intended full layout.

## Prerequisites

- Node.js 22 or newer.
- pnpm 11 or newer.
- Rust 1.77.2 or newer plus Tauri platform prerequisites.
- Python 3.12 or newer for Core.

## Start here

```sh
pnpm install
pnpm check
```

`pnpm check` typechecks, tests, and builds the JavaScript workspace, then checks the Studio Rust shell. Core has a separate Python 3.12 environment and check documented in `services/core/README.md`.

To run the current local slice, start Core and Studio in separate terminals:

```sh
cd services/core
.venv/bin/python -m uvicorn mensura_core.main:app --reload
```

```sh
pnpm studio:dev
```

See `apps/studio/README.md` for desktop configuration and native builds.

## Working principles

- Deliver one observable vertical slice at a time.
- Keep service boundaries explicit and shared contracts versioned.
- Record only working functionality as implemented.
- Update `docs/agent_memory.md` after every meaningful implementation step.
- Preserve human review, structured logs, and Guard checks in task completion flows.

## Core API

See `services/core/README.md` for Python 3.12 setup, tests, run commands, implemented endpoints, and the current in-memory limitation.
