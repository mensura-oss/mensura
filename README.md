# Mensura

Mensura is an open-source, local-first and self-hostable agentic development platform. It is intended to combine a desktop developer workspace, controlled agent execution, durable project memory, mandatory quality gates, and an open plugin ecosystem.

The repository is at the foundation stage. The current runnable components are `@mensura/shared-types`, the minimal Python 3.12 Mensura Core HTTP API, and the Tauri/React Mensura Studio shell. Studio can select a workspace, inspect local Git state, build a bounded Vault inventory and immutable context pack, run configured Guard checks, create a ready task and context-bound queued run, then manually execute through the credential-free deterministic provider or one optional locally configured OpenAI BYOK adapter. Execution records explicit `queued -> running -> succeeded | failed` state, provider kind/model, `review.v2` prompt identity, timestamps, and bounded schema-validated output. A successful run can materialize one separate write-isolated change proposal with immutable lineage, bounded file suggestions, and explicit approve/reject review state. Approval does not apply, stage, commit, or otherwise write changes; instead, an approved proposal can be verified in a temporary isolated Git worktree where Core materializes the suggestion, runs the configured Guard checks, and returns a separate verification artifact with sandbox, per-file, Guard, and safe-diff metadata before removing the sandbox. Verification never writes the live branch or working tree. A separately gated, explicit apply-to-live step then consumes an approved proposal plus a passing verification to write the exact digest-checked content to the live working tree—refusing before any write when a live file has drifted, staging atomic writes, re-running Guard against the result, and recording a separate auditable application artifact with per-file digests and undo metadata—while still never staging, committing, or pushing, and without any provider access. Repository and Vault access remain read-only, and provider execution receives only the persisted task plus immutable pack—not the live workspace path. OpenAI keys are write-only through Studio and stored by Core in the OS credential backend; only the model ID is saved in local user config. Core still stores workspaces, tasks, packs, runs, proposals, verifications, and applications only in process memory; apart from the explicit apply-to-live write it does not modify the repository, and it never commits, stages, pushes, orchestrates agents, or persists history across restarts.

## Repository map

- `packages/shared-types`: shared domain, execution, change-proposal, verification, application, state-machine, and runtime plugin contracts.
- `apps/studio`: Tauri 2/React desktop shell and typed Core client.
- `services/core`: versioned FastAPI contracts, RFC 9457 errors, read-only Git/Vault adapters, immutable context-pack assembly, bounded Guard runner, deterministic plus optional OpenAI BYOK execution adapters, write-isolated proposal review, temporary Git-worktree verification sandboxes, explicit digest-checked apply-to-live with atomic writes and audit artifacts, local credential/config boundaries, in-memory resource storage, and API tests.
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
