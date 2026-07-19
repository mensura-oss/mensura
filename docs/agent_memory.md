# Agent Memory

## Project Summary

- Mensura is an AGPL-3.0 open-source, local-first and self-hostable agentic development platform for professional developers and teams.
- It combines a desktop workspace (Studio), orchestration (Core), project memory (Vault), quality and policy gates (Guard), extensions (Hub), and optional voice control (Voice).
- The product emphasizes reproducible agent runs, visible diffs and logs, human approval, mandatory checks, open MCP interoperability, and user-managed model providers.
- Current implementation status: the repository has a runnable pnpm workspace, tested shared contracts, a verified minimal Mensura Core FastAPI service, and a verified Tauri/React Studio flow for workspace selection -> ready task -> queued run. Durable server persistence and agent execution remain unimplemented.

## Source Documents Read

### `mensura_master_spec.md`

- Defines the product vision, module responsibilities, deployment modes, entities, technology candidates, and MVP/V1/V2 scope.
- Positions Mensura as engineering-controlled and self-host-first, with MCP-based interoperability and BYOK providers.
- Defines the target end-to-end task flow: context retrieval, agent execution, isolated changes, Guard checks, diff review, and human approval.

### `mensura_prd.md`

- Makes repository connection, persisted run history, semantic retrieval, pre-completion checks, MCP compatibility, and local/Docker deployment functional requirements.
- Defines the MVP as Studio, basic indexing, one orchestration path, diff review, lint/test integration, and BYOK.
- The central acceptance criterion is a working repo-to-agent-to-diff-to-checks-to-approval flow.

### `mensura_architecture.md`

- Establishes Studio -> Core as the primary boundary; Core coordinates Vault, Guard, provider, Git, queue, and runner adapters.
- Recommends Tauri/React for Studio and FastAPI/LangGraph for Core, with PostgreSQL, Redis, vector search, and Docker in the scaling path.
- Requires sandboxed execution where possible and durable audit records for approvals, tool calls, and risky changes.

### `mensura_roadmap.md`

- Orders delivery from monorepo and standards through Studio, Core, Vault, Guard, team mode, Hub, and advanced features.
- Keeps multi-agent swarms, Voice, remote runners, and scheduled automation out of the early MVP path.
- Treats package boundaries and coding standards as Phase 0 prerequisites.

### `mensura_agent_specs.md`

- Defines architect, research, coder, test, reviewer, security, DevOps, and docs roles.
- Requires every agent result to include summary, actions, files, rationale, risks, and next step.
- Describes role contracts, not an implementation framework or wire protocol.

### `mensura_api_outline.md`

- Lists REST boundaries for workspaces, projects, tasks, runs, Vault, Guard, and Hub.
- Lists WebSocket channels for run, task, and project events.
- Leaves request/response schemas, pagination, error envelopes, versioning, and authentication open.

### `mensura_guard_spec.md`

- Defines an ordered check pipeline from format and lint through tests, secrets, dependency checks, risk scoring, and approval.
- Requires failed tests and detected secrets to block completion.
- Requires protected paths and plugin network access to trigger explicit policy handling.

### `mensura_plugin_sdk_spec.md`

- Defines tool, MCP connector, agent, prompt, UI, and template plugin categories.
- Requires versioned manifests, explicit permissions, compatibility declarations, install review, and credential isolation.
- Names `@mensura/sdk`, `@mensura/mcp`, and `@mensura/shared-types` as public packages.

### `mensura_monorepo_structure.md`

- Defines `apps`, `services`, `packages`, `infra`, `examples`, `scripts`, and `docs` boundaries.
- Places Studio in `apps/studio` and Core/Vault/Guard/Hub/Voice in independent service directories.
- Includes shared config, SDK, MCP, prompts, types, UI, and test utilities as packages.

### `mensura_setup_guide.md`

- Declares Rust, Node LTS, pnpm, Python 3.12+, Docker Compose, and Git prerequisites.
- Describes a future setup sequence using PostgreSQL/Redis, migrations, Core, Studio, repository connection, and indexing.
- Defines the first demo as architecture summary -> small task -> coder diff -> Guard checks -> approval.

### `LICENSE`

- The repository is already licensed under GNU AGPL v3, matching the master specification's open hosted-derivative recommendation.

## Planned Architecture

### Studio

- Tauri 2 desktop shell with a React/TypeScript UI.
- Owns workspace presentation: repository tree, editor, terminal, task board, agent chat, diff review, logs, and session restoration.
- Communicates with Core through versioned HTTP contracts and WebSocket events; it should not embed orchestration or policy rules in UI code.

### Core

- FastAPI service and orchestration authority for tasks, runs, agent dispatch, context assembly, model routing, approvals, retries, and logs.
- Uses adapters for providers, Git, execution runners, Vault, and Guard so local MVP implementations can later be replaced by team-scale services.
- Starts with one explicit sequential workflow; graph orchestration and parallel agents follow only after that flow is observable and reliable.

### Vault

- Owns repository/document ingestion, chunk metadata, retrieval, project decisions, and task/run-linked memory.
- Starts with deterministic file indexing and queryable metadata; embeddings and graph relationships are added behind stable interfaces.
- Must be branch-aware before shared team memory is treated as authoritative.

### Guard

- Owns check definitions, ordered execution, structured results, blocking policy decisions, protected paths, risk signals, approvals, and audit events.
- Core requests evaluations but does not override a blocking Guard result.
- The MVP begins with configurable format/lint/test commands and explicit pass/fail/error states.

### Hub

- Owns plugin manifests, compatibility, permissions, installation metadata, signatures, connectors, templates, and agent packs.
- Post-MVP marketplace work follows a smaller local plugin loader with reviewable manifests and deny-by-default permissions.

### Voice

- Optional post-MVP adapter for local/cloud transcription and command parsing.
- Feeds normal Studio/Core commands and does not create a separate privileged execution path.

### Shared packages

- `shared-types`: versioned API entities, state machines, event payloads, errors, Guard results, and plugin manifest contracts.
- `config`: shared TypeScript, lint, formatting, and build conventions.
- `sdk`: supported plugin-facing client APIs; `mcp`: MCP adapters; `ui`: reusable Studio components; `prompts`: versioned prompt assets; `test-utils`: shared fixtures.
- Cross-service contracts remain explicit and dependency-light; services do not import each other's internal modules.

### Infra

- Local-first development scripts, Docker Compose for shared dependencies, and CI checks land before Kubernetes or Terraform.
- PostgreSQL/Redis/vector infrastructure is introduced when a working slice needs it, not as empty deployment boilerplate.
- Observability begins with structured logs and stable run IDs, then expands to OpenTelemetry and metrics.

## Current Status

- Work cycle 5 is implementation- and verification-complete: Core exposes replaceable read-only local Git inspection and Studio shows the active workspace repository summary. Git writes, patch content, and repository tree UI remain absent.
- Core v1 now includes a tested replaceable read-only Git inspection adapter and repository endpoint in addition to versioned resource routes, predictable errors, replaceable in-memory storage, and OpenAPI. Final cycle-wide/live verification is still pending.
- Git history: the initial license commit plus the committed foundation from work cycle 1; no product implementation history is deep enough for meaningful code hotspots yet.
- Documentation: ten project specifications, the root README, and this execution journal are tracked.
- Code at audit time: no applications, services, packages, tests, dependency manifests, CI, or local run scripts existed.
- Code now: pnpm workspace commands, strict shared TypeScript configuration, and `@mensura/shared-types` with domain contracts, guarded task/run transitions, plugin permissions, and runtime manifest validation.
- Toolchain observed locally: Node 22.23.1, pnpm 11.13.1, Rust 1.97.1, Docker 29.6.1, and Docker Compose 5.3.0.
- The default `python3` is 3.9.6, but Homebrew Python 3.12 is available at `/opt/homebrew/bin/python3.12`; FastAPI is not installed globally and Core will use a service-local virtual environment.
- Repository risk history is too small for meaningful hotspot or bug-magnet analysis; current risk is specification breadth and premature scaffolding.

## Completed Work Log

### 2026-07-19 15:41 MSK — Start work cycle 5: read-only repository summary

- Files changed: `docs/agent_memory.md`.
- Audit: confirmed a clean worktree at `abddbfa`; re-read the current workspace/shared API models, Core service/repository/error/router boundaries, Studio client/query/active-workspace flow, current READMEs, and the five-commit Git history. History is too small for meaningful defect trends; `docs/agent_memory.md`, root documentation, and shared contracts are the expected integration hotspots.
- Contract boundary before implementation: retain `Workspace.rootPath` as the local repository candidate; add isolated repository-inspection types with branch nullable for detached HEAD, aggregate counts, and path/change metadata only. Expose one workspace-scoped `GET /api/v1/workspaces/{workspace_id}/repository` endpoint; do not add a raw diff endpoint or any patch/body field.
- Adapter boundary before implementation: define a read-only protocol consumed by `CoreService` and implement it with GitPython. The adapter may read repository/index/worktree metadata only and must not expose GitPython objects outside its module.
- Error boundary before implementation: a missing workspace remains the existing resource-not-found problem; a nonexistent or non-directory root and a non-Git root receive distinct stable RFC 9457 problems; unexpected Git inspection failures stay sanitized by the global handler.
- Studio boundary before implementation: one compact panel keyed by the active workspace ID, queried independently so failure cannot disable workspace/task/run controls. No repository tree, patch viewer, Git writes, routing, global state, Vault, Guard, auth, or worker behavior is introduced.
- Follow-up: define and test the shared transport model first, then journal that stable contract before adding Core implementation.

### 2026-07-19 — Define the repository inspection transport contract

- Files changed: `packages/shared-types/src/{repository,index}.ts` and `docs/agent_memory.md`.
- Defined: isolated `RepositorySummary` and `RepositoryDiffMetadata` contracts with a stable change-type vocabulary, nullable branch for detached HEAD, aggregate staged/unstaged/untracked/unique-path counts, and metadata limited to path, change type, staged flag, and optional old path.
- Safety property: the shared response has no patch, hunk, line, blob, file-content, command, remote URL, credential, or write-operation field. A successful summary has literal `isRepository: true`; invalid/missing roots are represented by RFC 9457 errors rather than a partially successful object.
- Compatibility choice: `typeChanged` follows the existing camelCase JSON convention. One path may appear twice when it has both staged and unstaged changes; category counts are unique within their category and `changedPathsCount` is unique across all categories.
- Follow-up: add the GitPython-backed protocol implementation, domain problems, workspace-scoped route, and adapter/API/OpenAPI tests before touching Studio.

### 2026-07-19 — Prepare the Core Git inspection step

- Files changed: `docs/agent_memory.md`.
- Planned implementation: inject a `GitRepositoryAdapter` protocol into `CoreService`; default `create_app` to a GitPython implementation; make service lookup resolve the workspace first and pass only its root path into the adapter; keep FastAPI routers free of GitPython imports.
- Counting semantics: staged and unstaged counts are unique current paths within their respective index/worktree comparisons; untracked count is Git's untracked path list; changed-path count is their union. Diff metadata is sorted deterministically and may contain a staged plus unstaged entry for the same path.
- State handling: missing filesystem roots and non-directory paths are `repository-path-not-found` problems; existing non-repositories are `not-a-git-repository`; repositories without a resolvable commit are an `unsupported-repository-state` conflict; detached HEAD is supported with `branch: null`.
- Test boundary: adapter tests use disposable real Git repositories and assert clean, dirty, staged, untracked, rename, and detached behavior; API tests assert workspace scoping, exact media types/problem URNs, absence of patch-like fields, and OpenAPI surface.
- Follow-up: implement this boundary without invoking any Git write operation in production code.

### 2026-07-19 — Implement and verify Core read-only Git inspection

- Files changed: `services/core/pyproject.toml`, `services/core/src/mensura_core/{git_adapter,repository_models,exceptions,service,main}.py`, `services/core/src/mensura_core/api/{problems,routers/workspaces}.py`, `services/core/tests/{test_git_adapter,test_repository_api,test_openapi}.py`, and `docs/agent_memory.md`.
- Adapter design: `CoreService` depends on the one-method `GitRepositoryAdapter.inspect` protocol so one request uses one inspection boundary and minimizes cross-call drift. `GitPythonRepositoryAdapter` is the default implementation; GitPython types remain private to the adapter and can later be replaced without changing the router or HTTP contract. Concurrent external repository changes can still make a result best-effort rather than atomic.
- Implemented endpoint: `GET /api/v1/workspaces/{workspace_id}/repository` resolves the stored workspace root, returns branch/dirty/count/path metadata, supports detached HEAD with a null branch, and never requests or serializes diff patches.
- Problem contract: missing workspace uses `resource-not-found`; missing/non-directory roots use `repository-path-not-found` (404); existing non-repositories use `not-a-git-repository` (422); bare/unborn/uninspectable Git state uses `unsupported-repository-state` (409). All use `application/problem+json`.
- Production read-only boundary: implementation calls only repository opening, HEAD/branch lookup, index-to-HEAD/worktree comparisons, and untracked-file discovery. Git mutation commands appear only in disposable test-fixture setup, never in application code or against the user's repository.
- Coverage: disposable repositories verify clean state, staged plus unstaged changes on one path, untracked files, staged rename metadata, detached HEAD, missing/non-repo/unborn roots, workspace scoping, safe API shape, exact problem media/type, and OpenAPI schema/surface.
- Verification: Python 3.12 Ruff lint/format passed and all 22 Core tests passed with warnings treated as errors.
- Follow-up: add a separately failing TanStack Query repository request and compact active-workspace panel; do not couple it to task/run rendering.

### 2026-07-19 — Prepare the Studio repository summary step

- Files changed: `docs/agent_memory.md`.
- Planned client boundary: extend `CoreClient` with one typed `getWorkspaceRepository(workspaceId)` call and add a workspace-specific query key. Preserve exact RFC 9457 problems through the existing `CoreApiError` path.
- Planned UI boundary: render a compact panel only when an active workspace exists; show root/branch, clean or dirty status, category counts, and a bounded metadata list with change/staged badges. A repository failure remains local to this panel and must not hide or disable task/run/workspace controls.
- Empty/error behavior: no active workspace gets actionable guidance; a clean repository gets an explicit zero-change state; detached HEAD is shown as `Detached HEAD`; invalid root/non-repo problems are displayed with the existing structured Problem Details component.
- Test boundary: cover URL encoding/client typing, no-selection guidance, clean and dirty summaries, bounded changed-path rendering, detached branch, and non-fatal RFC 9457 display.
- Follow-up: implement the client/query/component slice and verify it independently before documentation and live runtime checks.

### 2026-07-19 — Implement and verify the Studio repository summary

- Files changed: `apps/studio/src/api/{coreClient,coreClient.test}.ts`, `apps/studio/src/app/{App,App.test}.tsx`, `apps/studio/src/app/queryClient.ts`, `apps/studio/src/features/repository/{RepositorySummaryPanel,RepositorySummaryPanel.test}.tsx`, `apps/studio/src/test/render.tsx`, `apps/studio/src/styles.css`, and `docs/agent_memory.md`.
- Implemented: typed repository client call with encoded workspace ID; dedicated TanStack Query key; active-workspace panel with refresh, branch/detached label, clean/dirty badge, staged/unstaged/untracked/unique-path counts, and a deterministic list capped at eight metadata entries.
- Isolation: the repository query is independent from workspace/task/run queries. No active workspace makes no request; inspection errors render through the existing Problem Details component inside the panel; the App acceptance test proves task/run actions remain available when repository inspection fails.
- Safe rendering: Studio renders path/change/staged metadata only. It has no patch viewer, content renderer, Git command controls, repository tree, or mutation hook.
- Coverage: client URL typing plus four panel behaviors cover no selection, dirty counts/bounded paths, clean detached HEAD, and RFC 9457 non-repository state. Studio now has 23 passing tests across 10 files, and strict TypeScript checking passes.
- Contract refinement: `branch` is always present and nullable so detached HEAD remains explicit; `oldPath` is optional/nullable across the shared contract and current Pydantic responses emit `null` when no previous path exists.
- Follow-up: update Core/Studio/root documentation, run all Python/TypeScript/Rust/build checks, then inspect this real Mensura repository through a live Core endpoint and release Studio WebView.

### 2026-07-19 — Prepare fifth-cycle documentation and acceptance verification

- Files changed: `docs/agent_memory.md`.
- Documentation plan: describe the new endpoint, GitPython adapter boundary, read-only guarantee, error URNs, panel behavior, and the fact that a workspace root must itself be a committed non-bare Git repository. Update the next priority without claiming execution or diff review.
- Automated verification plan: run root `pnpm check`, Core Ruff lint/format and all tests with warnings as errors, Rust format, and whitespace checks. Build the native Studio bundle only after those pass.
- Live verification plan: start fresh Core, create a workspace for the current Mensura repository, inspect its exact current branch/dirty metadata through HTTP, and launch the release Studio binary to confirm the WebView reaches the new repository endpoint. Do not alter the repository to manufacture dirty state; dirty behavior is already covered with disposable test repositories.
- Evidence boundary: live HTTP/native transport will confirm actual integration against the current local repository; component tests remain the evidence for exact badge/count/path/error rendering unless GUI automation is explicitly used.
- Follow-up: complete documentation and the verification matrix, then record only observed results.

### 2026-07-19 — Verify and complete the read-only repository vertical slice

- Files changed: `packages/shared-types/src/{repository,index}.ts`, `services/core/{pyproject.toml,README.md,src/**,tests/**}`, `apps/studio/{README.md,src/**}`, root `README.md`, and `docs/agent_memory.md`.
- Implemented outcome: a workspace can keep its existing local `rootPath`; Core can inspect that path through a replaceable read-only GitPython adapter; `GET /api/v1/workspaces/{workspace_id}/repository` returns safe branch/status/count/path metadata; Studio shows that summary for the active workspace without coupling failures to task/run controls.
- Root verification: `pnpm check` passed shared/Studio strict TypeScript, 10 shared tests, 23 Studio tests across 10 files, production shared/Studio builds, and native `cargo check`; `cargo fmt --check` and `git diff --check` passed.
- Core verification: Python 3.12 Ruff lint/format passed and all 23 API/OpenAPI/adapter tests passed with warnings treated as errors, including preservation of `branch: null` through the HTTP endpoint for detached HEAD. Disposable fixture repositories cover Git mutations needed to construct states; production code and the live Mensura repository were inspected read-only.
- Native build verification: `pnpm studio:build` rebuilt the optimized binary, macOS `.app`, and arm64 DMG successfully.
- Live real-repository verification: a fresh Core workspace pointed to `/Users/makedoni/Documents/mensura`; the endpoint returned `main`, dirty state, 0 staged, 19 unstaged, 7 untracked, and 26 unique changed paths with no patch/content fields. These counts matched the current worktree categories at inspection time.
- Live desktop verification: the release Tauri app connected to Core, listed the live workspace, and after selection rendered `main`, `Dirty`, the exact 0/19/7/26 counts, eight changed-path metadata rows, and an `18 more metadata entries` summary. Core recorded `200` requests for health, workspaces, and the new repository endpoint. Studio and Core then stopped cleanly.
- Safety boundary: no Git mutation was run against the Mensura repository. The API has no patch/body contract, Studio has no write control or content viewer, and invalid repository state remains a local RFC 9457 panel error.
- Next priority: implement the first narrowly configured Guard lint/test runner with structured blocking results and a compact Studio result view, preserving the same adapter and non-orchestration discipline.

### 2026-07-19 15:23 MSK — Start work cycle 4: first Studio task flow

- Files changed: `docs/agent_memory.md`.
- Audit: confirmed a clean worktree at `d0e802a`; re-read the cycle-3 Studio shell/client/query structure, workspace/task/run shared types, Core task/run routers and service methods, and current run documentation. No Mensura-specific external memory entry exists, so repository contracts remain authoritative.
- Planned vertical flow: persist one active workspace ID in localStorage; select or auto-select a created workspace; create a ready task with the existing `POST /api/v1/tasks`; start a queued run with the existing `POST /api/v1/tasks/{task_id}/runs`; seed/refetch the matching TanStack Query entries; show both resources immediately.
- State decision before implementation: active workspace ID is small client state owned by `App` through a focused persistence hook and passed by props. Server resources remain in TanStack Query. No global state library or optimistic server record is introduced.
- Mutation decision before implementation: add minimal `CreateTaskRequest` transport typing; use one reusable start-run component for newly created and looked-up tasks; preserve form values after any server failure; use client-side trimmed-title validation plus native form constraints and accessible error associations.
- Explicitly deferred: task/run lists, task status mutation, orchestration workers, run events/SSE, Core process supervision, durable Core storage, repository/editor/terminal/Kanban UI, Vault, Guard, Hub/plugins, routing, authentication, and endpoint settings.
- Follow-up: implement and verify active workspace persistence/selection first, without task or run controls, then record that boundary before continuing.

### 2026-07-19 — Implement active workspace selection and persistence

- Files changed: `apps/studio/src/app/{App,useActiveWorkspaceId}.tsx`, `apps/studio/src/app/useActiveWorkspaceId.test.tsx`, `apps/studio/src/features/workspaces/WorkspacesPanel.tsx`, its test, `apps/studio/src/styles.css`, `apps/studio/src/test/setup.ts`, and `docs/agent_memory.md`.
- Implemented: selectable workspace cards with `aria-pressed`; visible active badge; guidance when workspaces exist but none is selected; localStorage restoration under `mensura:active-workspace-id`; automatic selection after successful workspace creation; and removal of a restored selection when Core no longer returns that workspace.
- Resilience: localStorage read/write failures do not break the current Studio session. Query cache is updated with a created workspace before selection, preventing the reconciliation effect from clearing a valid new ID while the list refetches.
- Test issue resolved: Studio tests had relied on implicit Testing Library cleanup, which was not registered in the Vitest environment. Added explicit `afterEach(cleanup)` so component tests cannot interact with stale DOM from a previous test.
- Verification: Studio strict TypeScript checking passed; all 9 Studio tests across 6 files passed, including persistence, selection, auto-selection, and the previous shell/client behavior.
- Follow-up: add the typed task-create client method and active-workspace task form. Do not add run creation until task success/error behavior is independently verified and journaled.

### 2026-07-19 — Implement active-workspace task creation

- Files changed: `packages/shared-types/src/api.ts`, `packages/shared-types/package.json`, `apps/studio/src/api/{coreClient,coreClient.test}.ts`, `apps/studio/src/test/render.tsx`, `apps/studio/src/features/tasks/{TaskCreationPanel,TaskCreationPanel.test,TaskDetails,TaskInspector}.tsx`, `apps/studio/src/app/App.tsx`, `apps/studio/src/styles.css`, and `docs/agent_memory.md`.
- Implemented: minimal `CreateTaskRequest`; exact camelCase `POST /api/v1/tasks`; active workspace guidance and badge; labelled title/description/role form; whitespace-aware required title validation with `aria-invalid`/`aria-describedby`; pending/error/success states; immediate ready-task result; and TaskDetails reuse in both creation and lookup paths.
- State behavior: the response is written to `queryKeys.task(task.id)` and the matching query is invalidated/refetched; only the created task ID remains local UI state. Form values clear after success and remain intact after RFC 9457 or connection failure. Changing active workspace remounts the form and removes a result from the previous workspace.
- Resumability issue resolved: `@mensura/shared-types` previously exposed declaration types only from generated `dist`, so a new contract was invisible to Studio until a manual shared build. Type consumers now resolve `src/index.ts`, while runtime imports remain on built `dist`, allowing clean-checkout typechecking without stale generated declarations.
- Verification: shared and Studio strict TypeScript checks passed; all 13 Studio tests across 7 files passed, including task request serialization, client validation, success rendering, cache-backed refresh, RFC 9457 display, and value preservation after failure.
- Follow-up: add one reusable queued-run mutation/result component to TaskDetails so both newly created and looked-up tasks can start a run. Preserve the standalone run inspector and do not add events or orchestration behavior.

### 2026-07-19 — Implement reusable queued-run creation

- Files changed: `apps/studio/src/api/{coreClient,coreClient.test}.ts`, `apps/studio/src/test/render.tsx`, `apps/studio/src/features/runs/{RunDetails,RunInspector,StartRunAction,StartRunAction.test}.tsx`, `apps/studio/src/features/tasks/TaskDetails.tsx`, `apps/studio/src/styles.css`, and `docs/agent_memory.md`.
- Implemented: exact `POST /api/v1/tasks/{task_id}/runs`; reusable Start run action embedded in TaskDetails; pending and RFC 9457 failure states; immediate queued-run details; and shared RunDetails rendering for both the mutation result and run inspector.
- Reuse boundary: every successfully created or looked-up task exposes the same run action. No separate mutation implementations or duplicated task/run resource cards were introduced.
- Query behavior: run response is written to `queryKeys.run(run.id)`, then both its run query and the source task query are invalidated/refetched. This reflects Core's actual result—task remains `ready`, run remains `queued`—without optimistic status simulation.
- Verification: Studio strict TypeScript checking passed; all 16 Studio tests across 8 files passed, including run URL encoding, success refresh/rendering, and RFC 9457 failure behavior.
- Follow-up: add one full App-level test for workspace create/selection -> task create -> run create, update user documentation, then run root/Core/native/live verification before marking the cycle complete.

### 2026-07-19 — Prepare the fourth-cycle acceptance and verification pass

- Files changed: `apps/studio/src/app/App.test.tsx`, `apps/studio/src/features/tasks/TaskInspector.test.tsx`, `apps/studio/README.md`, root `README.md`, and `docs/agent_memory.md`.
- Acceptance coverage: added a full App-level user flow with an isolated test CoreClient: create workspace -> automatic persisted selection -> create task -> start run -> display queued run. Added explicit coverage that a task retrieved through Task Inspector exposes the same working run action.
- Documentation: Studio/root READMEs now describe active selection restoration, ready task creation, queued placeholder runs, Core restart behavior, and the still-deferred worker/list/event features.
- Verification before final matrix: Studio strict TypeScript check passed and 17 tests across 9 files passed before the additional looked-up-task acceptance case. No final success claim is made until the full root suite, Core regressions, Rust formatting/native build, and live HTTP sequence complete.
- Planned live evidence: run the exact Core workspace/task/run POST+GET sequence against Uvicorn and launch the newly built Tauri application against that Core. UI mutation behavior is covered by the App-level acceptance test; native runtime evidence must still confirm the built WebView reaches Core.

### 2026-07-19 — Verify and complete the first Studio task flow

- Files changed: `packages/shared-types/{package.json,src/api.ts}`, `apps/studio/src/{api,app,features,styles.css,test}/**`, `apps/studio/README.md`, root `README.md`, and `docs/agent_memory.md`.
- Implemented outcome: a user can create or select a workspace, restore that selection across Studio reloads, create a ready task for it, start a queued run from the created or looked-up task, and immediately inspect both resource responses in the existing shell.
- Root verification: `pnpm check` passed shared/Studio strict TypeScript, 10 shared tests, 18 Studio tests across 9 files, production shared/Studio builds, and native `cargo check`; `cargo fmt --check` and `git diff --check` passed.
- Core regression verification: Python 3.12 Ruff lint/format passed and all 12 API/OpenAPI tests passed with warnings treated as errors.
- Native build verification: `pnpm studio:build` rebuilt the optimized binary, macOS `.app`, and DMG with the new flow.
- Live Core verification: against a fresh Uvicorn process, `POST /workspaces`, `POST /tasks`, and `POST /tasks/{id}/runs` returned `201`; subsequent task/run GETs returned `200` with task `ready` and run `queued`. The freshly built Tauri WebView then connected to the same process and received `200` for health and workspace list. Studio and Core were stopped cleanly.
- Evidence boundary: App-level acceptance exercises the actual React forms, persistence hook, client interface, mutations, cache refreshes, and rendered results. The live pass separately proves the exact Core HTTP sequence and native WebView transport; it did not claim orchestration or a worker transition beyond `queued`.
- Mutation/refetch boundary: successful POST responses are committed to Query cache before non-blocking invalidation. A later GET failure is shown by that resource query and does not retroactively convert a successful create mutation into a failed submission or restore already accepted form values.
- Next priority: add a read-only Core Git adapter for the active workspace and a small Studio repository summary showing repository validity, branch, dirty state, and safe diff metadata. This is the next vertical slice toward repo -> task -> diff without adding editor or execution UI.

### 2026-07-19 14:55 MSK — Start work cycle 3: minimal Studio shell

- Files changed: `docs/agent_memory.md`.
- Audit: re-read the project journal, Studio architecture references, shared TypeScript contracts, Core HTTP models/README, root workspace scripts, and current git history. Node 22.23.1, pnpm 11.13.1, and Rust 1.97.1 are available; the repository is clean and ahead of `origin/main` by the two completed cycle commits.
- Planned: add one `apps/studio` package with a Vite/React frontend and Tauri 2 Rust shell; add a typed Core client, narrowly scoped native HTTP capability, TanStack Query provider, static shell layout, and health/workspace/task/run panels; then verify tests, production frontend build, native Rust/Tauri build, and a live Core integration path.
- Contract decisions before implementation: default Core URL is `http://127.0.0.1:8000` with a `VITE_MENSURA_CORE_URL` override; Studio will use Tauri's scoped native HTTP client inside the desktop runtime and standard `fetch` in browser/test contexts; RFC 9457 problems are preserved as a typed `CoreApiError`; resource and problem transport types belong in `@mensura/shared-types` rather than duplicated feature-local interfaces.
- Explicitly deferred: Monaco, terminals, repository tree, task creation, run creation/events, Kanban, Vault/Guard/Hub/plugin UI, settings screens, routing, authentication, and any global state store beyond TanStack Query's server cache.
- Follow-up: scaffold and wire the package without adding feature implementation yet, then record the runnable scaffold result before building the API/UI slice.

### 2026-07-19 — Establish the runnable Studio scaffold

- Files changed: `apps/studio/package.json`, `apps/studio/index.html`, `apps/studio/tsconfig.json`, `apps/studio/vite.config.ts`, `apps/studio/vitest.config.ts`, `apps/studio/src/**`, `apps/studio/src-tauri/**`, root `package.json`, `pnpm-lock.yaml`, and `docs/agent_memory.md`.
- Implemented: a workspace-owned React 19/Vite 8 entry point; a Tauri 2 Rust binary/library shell; production frontend distribution wiring; a single resizable desktop window; a content security policy; a narrowly scoped HTTP capability limited to local Core URLs; root `studio:dev` and `studio:build` commands; and locked npm/Cargo dependencies.
- Issue resolved: Vitest 3 and Vite 8 provided incompatible Vite plugin types under strict TypeScript. Both root and Studio test tooling now use Vitest 4, whose declared peer range includes Vite 8.
- Verification: Studio TypeScript checking passed, Vite production build completed, and `cargo check --manifest-path apps/studio/src-tauri/Cargo.toml` compiled the native shell and Tauri HTTP plugin successfully.
- Current limitation: the rendered React app is still a bootstrap placeholder. Core client behavior and the required health/workspace/task/run panels have not yet been implemented or claimed working.
- Follow-up: add shared API transport types and the modular Core client/query/UI slice, then record its test status before expanding documentation or attempting native end-to-end validation.

### 2026-07-19 — Implement the unverified Studio Core UI slice

- Files changed: `packages/shared-types/src/api.ts`, `packages/shared-types/src/domain.ts`, `packages/shared-types/src/index.ts`, and `apps/studio/src/{api,app,components,features,layout}/**` plus `apps/studio/src/main.tsx` and `styles.css`.
- Shared contracts: added Health, workspace collection/create, and RFC 9457 Problem Details transport types; aligned nullable Task role and Run timestamps with the actual Pydantic response schema.
- Client boundary: added a configurable typed Core client with URL normalization, encoded resource IDs, JSON request handling, native Tauri/browser transport selection, RFC 9457 preservation in `CoreApiError`, and explicit connection/malformed-error fallbacks. Components receive the client through a small React context so tests and future endpoint settings do not require module mutation.
- UI implemented in code: a static sidebar/top bar/main shell; health polling and manual refresh; workspace loading/empty/list/create states; task and run ID inspectors; resource detail rendering; and readable domain, validation, and connectivity errors. TanStack Query is the only server-state mechanism; form/lookup values remain local component state.
- Scope held: no router, global UI store, mock records, task/run creation controls, repository features, orchestration, or future IDE panels were added.
- Verification status: shared-types build, Studio strict TypeScript check, and Vite production build pass. Behavioral tests and live Core/Tauri connectivity remain pending, so this step is not yet marked as completed functionality.
- Follow-up: add focused client/component tests and Studio/Core run documentation, then execute the complete workspace, Python, live HTTP, and native Tauri verification matrix.

### 2026-07-19 — Add Studio behavior tests and run documentation

- Files changed: `apps/studio/src/**/*.test.tsx`, `apps/studio/src/api/coreClient.test.ts`, `apps/studio/src/test/render.tsx`, `apps/studio/README.md`, root `README.md`, root and Studio `package.json`, and `docs/agent_memory.md`.
- Tests added: seven Studio tests across five files cover typed health transport, RFC 9457 preservation, connection failure messages, healthy status rendering, workspace empty/create/refetch behavior, task validation details, and queued run rendering.
- Testability decision: feature components depend on a context-provided `CoreClient`, while production receives the native/browser implementation and tests receive a deterministic in-process implementation. This keeps UI tests free of mock records in production and avoids a global state library.
- Monorepo decision: root `pnpm check` now ends with the Studio `cargo check`, so the native Rust boundary is part of the normal repository health command rather than an undocumented side check.
- Documentation: added exact two-terminal Core/Studio run commands, current UI behavior, Core URL/security scope, build commands, prerequisites, in-memory limitations, and the explicit deferred surface.
- Verification: Studio strict TypeScript checking passed; all seven new Studio tests passed. Full root/Python checks, real Core requests through the built client, and native Tauri build/runtime validation remain pending.
- Follow-up: perform the final verification matrix and fix only issues that block the required shell/connectivity outcome before promoting this cycle into `Implemented Functionality`.

### 2026-07-19 15:18 MSK — Verify and complete the minimal Studio shell

- Files changed: `apps/studio/**`, `packages/shared-types/src/{api,domain,index}.ts`, `.gitignore`, root `README.md`, root `package.json`, `pnpm-lock.yaml`, and `docs/agent_memory.md`.
- Implemented: the runnable Tauri 2/React/Vite Studio package, scoped native Core transport, TanStack Query server cache, developer-tool layout, health/workspace/task/run panels, RFC 9457 UI, tests, app icons, local run/build documentation, and root scripts.
- Native build issue resolved: Tauri requires a default application icon even when the bundle icon list is omitted. Added one source SVG and generated only the desktop icon set; the previously generated Android/iOS assets were removed because mobile targets are outside Studio scope.
- Root verification: `pnpm check` passed strict TypeScript checks, 10 shared-types tests, 7 Studio tests, shared/Studio production builds, and native `cargo check`.
- Core regression verification: Python 3.12 Ruff lint and format checks passed; all 12 Core API/OpenAPI tests passed with warnings treated as errors.
- Native verification: `tauri build --no-bundle` produced the optimized desktop binary; `pnpm studio:build` produced `Mensura Studio.app` and `Mensura Studio_0.1.0_aarch64.dmg`. DMG creation required running outside the filesystem sandbox because it invokes macOS `hdiutil`.
- Live connectivity verification: launched the release Studio binary with Uvicorn Core on `127.0.0.1:8000`; Core recorded `200` requests for `GET /health` and `GET /api/v1/workspaces` from the running Tauri WebView. Both processes were then stopped cleanly.
- Working boundary: workspace creation and task/run inspectors are behavior-tested against the same injected client contract; Core still loses all resources on restart, and Studio does not start or supervise Core.
- Next Studio priority: add explicit workspace selection plus task creation and placeholder run launch using the already implemented Core v1 POST endpoints. This creates the first user-driven task flow without pulling in editor, terminal, Kanban, or orchestration scope.

### 2026-07-19 14:24 MSK — Initialize persistent project memory

- Files changed: `docs/agent_memory.md`
- Implemented: created the required resumable project journal with all mandated sections.
- Follow-up: complete the source audit and record the planned architecture and implementation order.

### 2026-07-19 14:32 MSK — Complete repository and specification audit

- Files changed: `docs/agent_memory.md`
- Implemented: recorded every source document, module boundaries, current gaps, local toolchain, phased architecture, and prioritized delivery plan.
- Follow-up: create and verify the root workspace plus the first shared contracts package.

### 2026-07-19 14:32 MSK — Establish runnable monorepo and shared contracts

- Files changed: `.editorconfig`, `.gitignore`, `README.md`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `tsconfig.base.json`, `packages/shared-types/**`, `docs/agent_memory.md`.
- Implemented: created the pnpm workspace; added strict TypeScript build/typecheck settings; defined Task, Run, Guard check, agent result, and plugin contracts; enforced review/check lifecycle transitions; added safe plugin manifest validation; documented the current setup and next target.
- Verification: `pnpm check` passed TypeScript checking, 10 Vitest tests in 2 files, and package compilation.
- Follow-up: define the minimal versioned Core transport contracts and implement a Python 3.12 FastAPI service without expanding into Vault, Guard execution, or Studio yet.

### 2026-07-19 — Start work cycle 2: minimal Core HTTP API

- Files changed: `docs/agent_memory.md`.
- Planned: revalidate the API and shared lifecycle contracts, define the v1 transport and RFC 9457 error shapes, then implement a Python 3.12 FastAPI service with replaceable in-memory repositories and success/error tests.
- Explicitly deferred: database integration, provider calls, agent orchestration, Guard execution, SSE unless the base HTTP contract is complete and stable.

### 2026-07-19 — Define the Core HTTP v1 contract

- Files changed: `docs/agent_memory.md`.
- Defined: unversioned `GET /health`; versioned workspace, task, and run endpoints under `/api/v1`; camelCase JSON fields; UUID identifiers; UTC timestamps; typed collection envelopes; `201 Created`, with `Location` when the created resource has a GET endpoint in this API slice.
- Error contract: RFC 9457 `application/problem+json` with `type`, `title`, `status`, occurrence-specific `detail`, and request-path `instance`; validation problems add an `errors` extension containing `detail` and JSON Pointer fields.
- Storage contract: service methods depend on repository protocols; the first implementation is process-local memory and must not claim restart durability.
- Run creation contract: creates a `queued` run only. It does not call a provider, mutate files, execute Guard, or simulate orchestration progress.
- Deferred: SSE run events, pagination cursors, authentication, database persistence, project resources, task mutation, and real execution.

### 2026-07-19 — Implement the unverified Core v1 service slice

- Files changed: `services/core/pyproject.toml`, `services/core/README.md`, `services/core/src/mensura_core/**`, `services/core/tests/**`, `packages/shared-types/src/domain.ts`, `README.md`, `docs/agent_memory.md`.
- Implemented in code: FastAPI bootstrap and OpenAPI, `/health`, v1 workspace/task/run routers, strict camelCase Pydantic contracts, repository protocol and lock-protected in-memory adapter, Core application service, RFC 9457 handlers, and success/error/OpenAPI tests.
- Shared contract alignment: added the Workspace type and made workspace ownership explicit on Task while retaining optional future `projectId`.
- Verification status: pending. No functionality from this step belongs in `Implemented Functionality` until Python 3.12 lint/tests and the existing pnpm checks pass.

### 2026-07-19 14:49 MSK — Verify and complete Core HTTP v1

- Files changed: `.gitignore`, `README.md`, `docs/agent_memory.md`, `packages/shared-types/src/domain.ts`, `services/core/**`.
- Implemented: seven requested HTTP endpoints; camelCase UUID/UTC resource contracts; typed success responses; RFC 9457 errors for domain, validation, framework, and unexpected failures; replaceable lock-protected in-memory storage; OpenAPI and service documentation.
- Tests: 12 Python API/OpenAPI tests cover health, workspace list/create, task create/get, run create/get, missing resources, missing parent workspace, conflicts, body/path validation, framework 404, sanitized unexpected failures, camelCase schema, exact problem media type, and the endpoint surface.
- Verification: Python 3.12.13; Ruff lint and format check passed; Pytest passed 12 tests with warnings treated as errors; `pnpm check` passed TypeScript checking, 10 existing tests, and build.
- Runtime smoke test: Uvicorn served `/health` as `200 application/json` and a missing task as `404 application/problem+json`; the server shut down cleanly.
- Follow-up: build the minimal Studio shell/client against the documented OpenAPI surface, or first add a generated/client contract workflow if Studio implementation requires it.

## Implemented Functionality

- Persistent repository-local project memory and execution journal.
- Installable pnpm monorepo with a single root health command: `pnpm check`.
- Strictly typed shared Task, Run, Guard check, agent result, and plugin manifest contracts.
- Task lifecycle rules that require review before approval and support revision/retry paths.
- Run lifecycle rules that require checking and an approval checkpoint before completion.
- Runtime plugin manifest validation for supported types and permissions, semantic versions, duplicate permissions, and unsafe entry paths.
- Automated coverage for the implemented lifecycle and plugin validation behavior (10 passing tests).
- Python 3.12 FastAPI Core service with enabled OpenAPI and eight implemented HTTP endpoints.
- Workspace creation/listing with exact-root conflict detection in a process-local repository.
- Task creation/retrieval tied to an existing workspace; created tasks begin in `ready` status.
- Placeholder run creation/retrieval; created runs remain `queued` and perform no orchestration or side effects.
- RFC 9457 `application/problem+json` responses for resource misses, conflicts, request validation, framework HTTP errors, and generic internal failures.
- CamelCase JSON contracts aligned with TypeScript Workspace/Task ownership and documented in OpenAPI.
- Twenty-three passing Core API/OpenAPI/Git-adapter tests plus successful real-Uvicorn repository inspection.
- Tauri 2 desktop Studio with React 19, Vite 8, a single resizable window, desktop app icons, CSP, and a local-Core-only native HTTP capability.
- TanStack Query-backed Core health polling, workspace list/create behavior, task lookup, and run lookup with explicit loading, empty, success, connection-error, and RFC 9457 error states.
- Shared Health, workspace transport, and Problem Details contracts aligned with Core's camelCase responses and nullable fields.
- Twenty-three passing Studio client/component/acceptance tests and successful native release binary, macOS `.app`, and DMG builds.
- Verified live desktop connectivity from the release Tauri WebView to Core health and workspace endpoints.
- Persisted active workspace selection with stale-ID reconciliation after Core restart.
- Accessible active-workspace task creation with client validation, RFC 9457 failures, value preservation on failure, and immediate ready-task details.
- Reusable queued-run creation from both created and looked-up tasks, with task/run query refresh and immediate queued-run details.
- Verified live Core workspace -> ready task -> queued run POST/GET sequence.
- Isolated shared repository summary/diff-metadata contracts with no patch or file-content fields.
- Replaceable read-only `GitRepositoryAdapter` with a GitPython implementation for branch, detached HEAD, clean/dirty, staged/unstaged/untracked counts, and safe changed-path metadata.
- Workspace-scoped repository inspection endpoint with dedicated RFC 9457 problems for missing paths, non-repositories, and unsupported Git states.
- Compact active-workspace Studio repository panel with independent TanStack Query failure handling and bounded changed-path rendering.

## Pending Tasks

### MVP

1. Add the first Guard runner for narrowly configured lint/test commands with structured, blocking results and a compact Studio result view.
2. Add deterministic Vault repository indexing and basic retrieval; defer embeddings until the ingestion contract is stable.
3. Implement one observable execution flow: queued run -> explicit stub/provider adapter -> produce safe diff metadata -> execute Guard -> review -> approve/reject.
4. Add Docker Compose only for dependencies required by the working flow, plus CI for format, typecheck, tests, and builds.
5. Replace temporary in-memory adapters with durable storage where acceptance criteria require restart-safe history.

### Post-MVP

1. Semantic embeddings, graph memory, and branch-aware shared Vault snapshots.
2. Multiple model providers, LangGraph checkpoints, retries, and parallel agent execution.
3. Team workspaces, authentication/authorization, shared audit UI, and remote runners.
4. Hub marketplace, signed plugins, community metadata, agent/template packs, and UI extensions.
5. Voice commands, scheduled automation, knowledge graph UI, and release agents.

## Technical Decisions

### Persistent execution journal

- Decision: maintain `docs/agent_memory.md` after every meaningful implementation step.
- Reason: future agents must be able to resume work without reconstructing project context.
- Alternatives considered: ephemeral chat-only notes; rejected because they are not repository-local or durable.
- Consequences: each work chunk includes a factual journal update and distinguishes plans from working functionality.

### Specification precedence

- Decision: use the master specification and PRD for product scope, architecture and roadmap for system/order, and module-specific documents for interface details.
- Reason: the documents are complementary but use both required and suggested language at different levels.
- Alternatives considered: treating every technology recommendation as mandatory; rejected because several choices are explicitly optional or unresolved.
- Consequences: conflicts are documented as open questions, and implementation choices remain replaceable until a working slice validates them.

### Incremental vertical delivery

- Decision: build contracts and one local sequential flow before multi-agent, distributed, marketplace, or advanced memory infrastructure.
- Reason: the main acceptance criterion is an inspectable end-to-end task, while scope inflation is the primary documented risk.
- Alternatives considered: scaffolding every target directory/service immediately; rejected because empty structure would not improve runnability.
- Consequences: target directories appear only when they contain executable code, tests, or necessary documentation.

### JavaScript workspace foundation

- Decision: use pnpm workspaces and strict TypeScript configuration for Studio/shared packages, beginning with `@mensura/shared-types`.
- Reason: pnpm and TypeScript are named by the docs, are available/compatible with the observed Node toolchain, and establish service boundaries without committing to UI implementation.
- Alternatives considered: starting with FastAPI; deferred because the observed Python 3.9 environment does not satisfy the documented Python 3.12+ baseline.
- Consequences: the first chunk can be installed, typechecked, and tested independently while Python setup is made explicit in a later Core chunk.

### Dependency-light runtime contracts

- Decision: implement small explicit runtime validators and lifecycle tables in `@mensura/shared-types` before adding a schema framework.
- Reason: the current contracts are small, and avoiding a runtime dependency keeps the first boundary auditable while still validating untrusted plugin manifests.
- Alternatives considered: Zod or JSON Schema generation; deferred until Core transport schemas establish whether cross-language schema generation is needed.
- Consequences: validators must remain exhaustively tested; adopt a schema tool later if manual TypeScript/Python contract parity becomes error-prone.

### Core HTTP v1 transport contract

- Decision: expose `/health` outside the API version and all domain endpoints under `/api/v1`; use camelCase JSON, UUID identifiers, UTC timestamps, collection envelopes, and explicit response models. Created Task and Run responses include `Location`; Workspace does not until an item GET route exists.
- Reason: health probes are operational rather than domain-versioned, while Studio-facing resources need a stable namespace and direct alignment with TypeScript conventions.
- Alternatives considered: snake_case wire fields and bare arrays; rejected because they create client translation work and leave no stable place for collection metadata.
- Consequences: Python uses snake_case internally through Pydantic aliases; OpenAPI documents camelCase; future pagination can extend collection envelopes without replacing response shapes.

### RFC 9457 problem details

- Decision: every HTTP error, including request validation and framework 404/405 responses, uses `application/problem+json`. Mensura-specific problem identities use stable `urn:mensura:problem:*` URIs until resolvable public problem documentation exists.
- Reason: one machine-readable contract avoids FastAPI's default error shape leaking into part of the API and follows the requested standard without claiming an unavailable public documentation host.
- Alternatives considered: FastAPI default `{detail: ...}` errors and fictional HTTPS problem URLs; rejected because the former is inconsistent and the latter would imply resolvable documentation that does not exist.
- Consequences: handlers must preserve agreement between HTTP status and the `status` member, avoid internal debugging details, and test the exact media type and validation extension.

### In-memory Core repositories

- Decision: place repository protocols between routers/service logic and a lock-protected in-memory implementation.
- Reason: the cycle requires runnable behavior but explicitly defers database integration.
- Alternatives considered: SQLite or PostgreSQL now; deferred until resource and migration contracts are validated by the minimal API.
- Consequences: all data disappears on restart and the README/OpenAPI must state that limitation; a durable adapter can replace storage without changing routes.

### Studio Core transport and state boundary

- Decision: use the Tauri 2 HTTP plugin for desktop requests with an allowlist restricted to local Core port 8000; use standard `fetch` outside Tauri; place endpoint methods behind an injected `CoreClient`; and use TanStack Query only for server state.
- Reason: native requests avoid WebView CORS differences while Tauri capabilities make network access reviewable. Client injection provides focused tests and a future endpoint-settings seam without introducing a global store.
- Alternatives considered: enabling wildcard CORS on Core, proxying every request through custom Rust commands, hard-coding fetch calls in panels, and adding a global UI state library. Rejected because each either widens access or duplicates state/transport logic without serving the minimal shell.
- Consequences: a non-default Core origin needs both a `VITE_MENSURA_CORE_URL` build setting and a reviewed capability change; browser-only Vite use may additionally require CORS; Studio currently connects to Core but does not manage its lifecycle.

### Studio active workspace and mutation results

- Decision: persist only the active workspace ID in localStorage; reconcile it against the server workspace query; keep task/run resources exclusively in TanStack Query; and retain only the IDs of the last created resources as local presentation state.
- Reason: workspace selection is durable client preference, while task/run records are server authority. Query seeding plus invalidation makes mutation results immediate without inventing optimistic status changes or adding a global client-state library.
- Alternatives considered: persisting full workspace/task/run objects, a Redux/Zustand store, optimistic task/run transitions, and separate run actions for created versus inspected tasks. Rejected because they create stale authorities, duplicate server state, or duplicate mutation behavior.
- Consequences: a Core restart invalidates the restored workspace ID and Studio clears it; switching workspace remounts the task form/result; created task and run remain visible through their query entries; run status truthfully stays `queued` until Core implements execution.

### Read-only Git inspection adapter

- Decision: use one `GitRepositoryAdapter.inspect` operation with GitPython as the MVP implementation, and expose one workspace-scoped summary endpoint.
- Reason: one operation minimizes inconsistent results and contract duplication across separate branch/status/diff calls, while the protocol keeps GitPython and local-process assumptions replaceable.
- Alternatives considered: shelling out directly from routers, multiple granular HTTP endpoints, raw patches, and early Dulwich integration; rejected because they couple transport to implementation, multiply race windows, expose unnecessary content, or add replacement work before the contract is proven.
- Consequences: workspace roots must currently be committed non-bare worktree roots; detached HEAD is supported as a null branch; responses may repeat one path for staged and unstaged metadata but count unique paths; concurrent external changes can make the read best-effort rather than atomic; invalid states are isolated RFC 9457 problems; no Git writes or patch content exist in the production surface.

## Open Questions

- Which pagination and authentication contracts should extend the implemented Core v1 resource/error schemas?
- Should local MVP persistence use SQLite before PostgreSQL, or should Dockerized PostgreSQL be required from the first Core service?
- Which model provider should power the first non-stub run, and how should BYOK credentials be stored on each platform?
- What exact sandbox guarantees are required for local command execution on macOS, Linux, and Windows?
- Which file types, ignore rules, chunking rules, and embedding provider define the first Vault index?
- How are plugin signatures rooted and verified, and which permissions are allowed for the first local plugin loader?
- Are the `[cite:…]` markers in the specifications backed by a source bibliography that should be added to the repository?
