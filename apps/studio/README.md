# Mensura Studio

Mensura Studio is the Tauri 2 desktop client for the local Mensura Core service. The current vertical slice supports selecting a workspace, inspecting local Git state, building and browsing a deterministic Vault inventory, selecting exact files into an immutable context pack, running configured Guard checks, creating a task and context-bound queued run, manually executing through Core's deterministic provider or one optional locally configured OpenAI BYOK adapter, and reviewing a separately persisted bounded change proposal. An approved proposal can additionally be verified in a temporary isolated Git worktree where Guard runs against the materialized suggestion. Proposal approval/rejection records review only, verification never touches the live branch, and applying changes to the live repository remains explicitly out of scope.

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
- Compact provider settings: deterministic availability plus write-only OpenAI key/model configuration and redacted status
- Workspace list, create form, selectable active workspace, and restored local selection
- Compact read-only repository summary for the active workspace: branch/detached state, clean/dirty badge, staged/unstaged/untracked counts, and up to eight changed-path metadata entries
- Manual Vault inventory build/refresh with included/excluded/text/binary counts, compact language summary, up to 200 deterministic file metadata entries, and a 16 KiB UTF-8 text preview inspector
- Context-pack builder with up to 500 selectable inventory entries, exact pre-creation path review, selected/preview-limit counters, immutable creation, process-local pack list, and read-only manifest inspection
- Manual Guard panel with latest-result loading, `Run checks`, pass/fail and blocking state, aggregate counts, compact lint/test cards, and collapsed bounded output
- Task creation for the active workspace plus task lookup by UUID
- Context-pack selection and preflight summary before queued run creation from created or looked-up tasks
- Run lookup/details showing the persisted immutable pack id, ownership/inventory identities, schema, file count, and byte summary
- Explicit deterministic/configured-OpenAI selection before manual execution, with visible running state, terminal status/timestamps, provider kind/adapter/model/`review.v2` identity, bounded structured result, and persisted structured failure
- Successful-run proposal creation/reopen, immutable lineage, collapsed bounded file suggestions and digest metadata, plus explicit approve/reject review actions that never apply repository changes
- Approved-proposal verification in a temporary isolated Git worktree, with sandbox/Guard/safe-diff results and explicit live-repository-untouched status
- RFC 9457 Problem Details and connection errors shown without losing server fields

The repository panel is independent from the rest of the shell. A missing path, non-Git root, or unsupported repository state is shown as RFC 9457 Problem Details without disabling workspace/task/run actions. It never renders patches or file contents and exposes no Git mutation controls.

The Guard panel is also independent. Before running it, review the workspace's `.mensura/guard.json`: a manual run executes its validated Ruff/pytest argv in the workspace through Core. The UI stays pending while the synchronous request runs, shows configuration/execution problems locally, and never auto-runs checks. Core keeps only the latest completed result in memory.

The Vault panel is manual and read-only. Build inventory traverses the current workspace root with Core's fixed exclusion rules and stores only the latest snapshot in memory. Selecting a text file loads at most 16 KiB; selecting a binary file shows metadata without making a preview request. Sensitive, generated, oversized, symlinked, missing, and unsafe paths are refused through RFC 9457 errors. This is deterministic metadata retrieval, not semantic search or a complete secret scanner.

The context-pack panel uses that latest inventory but has its own candidate query so it can expose up to the API's 500-file listing limit without colliding with the Vault inspector cache. Before creation it shows every selected path, text-preview versus binary-metadata policy, file count, and a conservative bounded-preview estimate. Core remains authoritative for validation. After creation Studio immediately opens the exact returned locked manifest and shows pack/inventory ids, counts, paths, capture/truncation metadata, and content digests; it intentionally does not dump captured preview bodies into the main shell.

Every task run action loads immutable packs using the task's own workspace id. The user must explicitly select one; Studio shows its full digest and compact file/byte evidence before enabling `Start run`. Core revalidates ownership and persists the binding. Created and looked-up run details make that exact immutable execution context visible; selection is preserved if creation returns Problem Details.

Queued run details expose a provider selector and separate `Execute run` action. Deterministic is the visible default and remains usable without provider discovery; OpenAI is disabled until Core reports it configured. The selected provider kind, prompt version, and model are visible before execution. While the synchronous request is pending, Studio shows running state and disables the action. Core remains authoritative: success replaces/refetches immediately, and failure also refetches because a terminal failed record may have been persisted before an RFC 9457 response. Runs observed in `running` poll once per second until terminal. Terminal runs never show the action again.

Execution review keeps input and output distinct. The immutable pack binding stays in base run details; execution shows provider/kind/adapter/version/model/prompt identity, duration, bounded task summary and interpreted intent, context aggregates/languages, warnings, recommended next steps, or the persisted safe failure. Studio does not render prompts, context preview bodies, raw provider responses/logs, credentials, patches, or repository contents.

Successful execution also exposes a distinct write-isolated proposal section. Studio first checks the workspace proposal collection so reopening a run restores its artifact; otherwise `Create proposal` materializes the run's already validated draft idempotently. The review shows proposal/run/context/provider/prompt lineage, summary and rationale, and file-level create/modify/delete metadata. Suggested text is collapsed by default, constrained to a scrollable region, and accompanied by before/after digests plus stored/original byte and truncation metadata. Approve and Reject are terminal artifact decisions. Neither action writes files or invokes Git, and the UI states that boundary before and after review.

Once a proposal is approved, a separate verification section appears so approval and verification remain distinct decisions. `Verify in isolated sandbox` asks Core to materialize the proposal inside a temporary detached Git worktree of `HEAD`, run the workspace's configured Guard checks there, and remove the sandbox. The latest artifact shows passed/failed status, a closed outcome (`sandbox_verified`, `guard_failed`, or `materialization_failed`), the verified commit and cleanup state, per-file applied/refused results with digests, safe diff aggregates, and collapsed Guard checks with bounded output excerpts—never raw patch dumps or full logs. The section states explicitly that the live branch and working tree are never written, and repeated verifications keep earlier attempt counts visible. Verification problems (unapproved proposal, non-Git workspace, truncated content, sandbox failure) appear as RFC 9457 details inside the section.

The Local BYOK panel sends a key only on explicit save. Core stores it in the OS credential backend and never returns it; Studio does not put it in localStorage or a config file, preserves it in the form only when save fails, and clears the field after success. The non-secret model ID is shown after redacted provider discovery. Saving does not validate the credential with a paid call; a rejected key is surfaced on selected execution. OpenAI network/model use is optional, and a failed real execution never silently switches providers.

The active workspace ID persists in localStorage, but Core data remains in memory. Restarting Core removes its workspaces/tasks/runs/proposals, and Studio clears a restored workspace selection when that ID no longer exists. Repository status is inspected live from the workspace `rootPath`; for this MVP the path itself must be a committed, non-bare Git worktree root.

The app does not start Core itself. Execution, proposal review, and verification are manual, synchronous, bounded, and live-repository-write isolated; OpenAI is the only optional real adapter and deterministic remains first-class. Additional vendors/models UX, arbitrary prompt editing, credential read-back, retry/cancellation, a worker/broker, streaming/SSE, orchestration, applying an approved proposal to the live branch, Monaco, terminals, full repository tree/navigation, file editing, semantic search/embeddings, full diff/patch editing, Git writes, task/run lists, Kanban, durable Vault/context-pack/run/proposal/verification history or watchers, the full Guard policy engine/history/config editor, Hub, plugins, and authentication are intentionally deferred.
