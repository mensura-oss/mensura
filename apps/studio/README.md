# Mensura Studio

Mensura Studio is the Tauri 2 desktop client for the local Mensura Core service. The current vertical slice supports selecting a workspace, creating a task, and recording a queued placeholder run while keeping orchestration explicitly out of scope.

## Requirements

- Node.js 22 or newer
- pnpm 11 or newer
- Rust 1.77.2 or newer
- Mensura Core running on Python 3.12
- Tauri platform prerequisites for your operating system

Install workspace dependencies once from the repository root:

```sh
pnpm install
```

## Run Studio with Core

Start Core in one terminal:

```sh
cd services/core
.venv/bin/python -m uvicorn mensura_core.main:app --reload
```

Start the native Studio window from the repository root in another terminal:

```sh
pnpm studio:dev
```

Studio defaults to `http://127.0.0.1:8000`. The frontend base URL can be changed with `VITE_MENSURA_CORE_URL`, but the Tauri capability currently permits only `http://127.0.0.1:8000/**` and `http://localhost:8000/**`. Expanding that native allowlist is a deliberate security change, not a runtime wildcard.

## Checks and builds

From the repository root:

```sh
pnpm check
pnpm studio:build
```

`pnpm check` runs TypeScript checks, frontend/shared tests, production frontend builds, and `cargo check` for the native shell. `pnpm studio:build` creates the desktop bundle for the current platform.

## Current UI

- Static developer-tool shell with sidebar, top bar, and content grid
- Core liveness polling and manual refresh
- Workspace list, create form, selectable active workspace, and restored local selection
- Task creation for the active workspace plus task lookup by UUID
- Queued run creation from created or looked-up tasks plus run lookup by UUID
- RFC 9457 Problem Details and connection errors shown without losing server fields

The active workspace ID persists in localStorage, but Core data remains in memory. Restarting Core removes its workspaces/tasks/runs, and Studio clears a restored workspace selection when that ID no longer exists.

The app does not start Core itself. A created run remains `queued`; no worker consumes it. Monaco, terminals, repository navigation, task/run lists, live run events, Kanban, Vault, Guard, Hub, plugins, authentication, and settings are intentionally deferred.
