# Agent Memory

## Project Summary

- Mensura is an AGPL-3.0 open-source, local-first and self-hostable agentic development platform for professional developers and teams.
- It combines a desktop workspace (Studio), orchestration (Core), project memory (Vault), quality and policy gates (Guard), extensions (Hub), and optional voice control (Voice).
- The product emphasizes reproducible agent runs, visible diffs and logs, human approval, mandatory checks, open MCP interoperability, and user-managed model providers.
- Current implementation status: the repository has a runnable pnpm workspace, tested shared contracts, a verified minimal Mensura Core FastAPI service, and a verified Tauri/React Studio flow for workspace selection -> ready task -> queued run, read-only repository inspection, deterministic Vault file inventory/preview, immutable context-pack creation/review, and manually triggered lint/test Guard results. Durable server persistence and agent execution remain unimplemented.

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

- Work cycle 8 is complete in the working tree from clean baseline commit `9c258d3`: Core creates deterministic immutable context packs only from an existing Vault inventory, and Studio explicitly selects and reviews their exact bounded evidence without provider execution.
- Work cycle 7 is complete in the working tree from clean baseline commit `a893268`: Core has deterministic process-local Vault inventory and bounded safe text retrieval, and Studio has a compact active-workspace inventory/preview inspector.
- Work cycle 6 is complete in the working tree from baseline commit `6552d2d`: Core has a manually triggered, bounded Ruff/pytest Guard runner and Studio has a compact active-workspace result panel.
- Core v1 now includes tested replaceable read-only Git inspection, Guard execution, Vault inventory, and immutable context-pack adapters in addition to versioned resource routes, predictable RFC 9457 errors, replaceable in-memory storage, and OpenAPI.
- Git history contained eight commits at this cycle's baseline; it remains too short for meaningful code-hotspot inference.
- Documentation: ten project specifications, the root README, and this execution journal are tracked.
- Code at audit time: no applications, services, packages, tests, dependency manifests, CI, or local run scripts existed.
- Code now: pnpm workspace commands, strict shared TypeScript configuration, and `@mensura/shared-types` with domain contracts, guarded task/run transitions, plugin permissions, and runtime manifest validation.
- Toolchain observed locally: Node 22.23.1, pnpm 11.13.1, Rust 1.97.1, Docker 29.6.1, and Docker Compose 5.3.0.
- The default `python3` is 3.9.6, but Homebrew Python 3.12 is available at `/opt/homebrew/bin/python3.12`; FastAPI is not installed globally and Core will use a service-local virtual environment.
- Repository risk history is too small for meaningful hotspot or bug-magnet analysis; current risk is specification breadth and premature scaffolding.

## Completed Work Log

### 2026-07-19 — Start work cycle 8: immutable context packs

- Files changed: `docs/agent_memory.md`.
- Baseline: confirmed clean worktree at `9c258d3`; re-read the cycle request, current journal, Vault models/service/store, Core dependency/router wiring, Studio Vault/client/App patterns, and the eight-commit history. History has no bug-fix magnets or firefighting commits; current hotspots are the expected journal, README, shared export, and Studio integration seams.
- Contract boundary: add isolated context-pack v1 contracts for create request/response, immutable manifest, deterministic file entries, summary, and collection. A pack belongs to one workspace and one concrete Vault inventory snapshot; it is not a provider payload, prompt, semantic retrieval result, task mutation, or run transition.
- Immutability boundary: accept an explicit non-empty file-path set, canonicalize and sort it, reject duplicates and paths absent from the latest inventory, capture current safe metadata plus bounded UTF-8 preview evidence, and store the complete manifest by content-derived identity. No update/delete endpoint will exist.
- Binary policy: permit binary inventory items as metadata-only entries with a content SHA-256 computed from a bounded-inventory file (maximum 5 MiB), zero preview bytes, no text field, and explicit `binary` kind. Text entries capture at most 16 KiB of UTF-8 preview plus total bytes and truncation state.
- Deterministic identity: compute per-file SHA-256 from current full file bytes; hash canonical JSON containing a schema version, workspace id, inventory id, deterministic ordered entries, limits, and aggregate summary. Exclude creation time and pack id from the digest input; repeated creation from unchanged selected inputs yields the same `sha256:<hex>` id/digest and idempotently reuses the stored manifest.
- Explicit limits: at most 50 selected files, at most 16 KiB preview per text file, and at most 256 KiB aggregate captured preview text. Vault's existing 5 MiB included-file ceiling remains the maximum hash input per file. Reject an oversized selection/aggregate rather than silently omit selected evidence.
- API boundary: synchronous `POST /api/v1/workspaces/{workspace_id}/context-packs`, `GET .../context-packs`, and `GET .../context-packs/{context_pack_id}`. List returns immutable manifest summaries only; get returns the exact manifest. Stable RFC 9457 problems cover absent inventory, invalid/excluded selections, oversized requests, changed/unavailable files, and missing packs.
- Studio boundary: add one active-workspace review panel that reuses the Vault file collection query, shows explicit checkbox selection and an upper-bound preview estimate before creation, submits via a TanStack mutation, lists process-local packs, and opens one immutable manifest without displaying full captured contents. Errors stay local to this panel.
- Explicitly deferred: provider/model execution, prompts, embeddings, semantic retrieval, editable packs, repository writes, background refresh/watchers, durable storage, task/run attachment, provider payload formats, and full content rendering.
- Follow-up: define and verify shared TypeScript contracts before implementing Core storage and hashing.

### 2026-07-19 — Define and verify the context-pack v1 shared contract

- Files changed: `packages/shared-types/src/{context-pack,context-pack.test,index}.ts` and `docs/agent_memory.md`.
- Defined: pinned schema version `1`; explicit `text_preview | metadata_only` capture modes; SHA-256 digest strings; manifest limits; deterministic file entries with content digest and nullable bounded preview; aggregate file/byte/truncation summary; create request/response; and summary collection contracts.
- Isolation: context-pack types live separately from Vault snapshots and task/run entities. They reference a workspace and inventory by id but do not mutate either contract or imply provider/prompt attachment.
- Binary policy is visible on the wire: binary entries remain reviewable metadata with a content digest, null text/encoding, zero preview bytes, and `metadata_only` capture mode.
- Verification: strict TypeScript typecheck/build and all 16 shared tests across five files pass.
- Follow-up: implement Core canonicalization, current-file validation, bounded capture, content-derived storage, APIs, problems, and deterministic regression coverage.

### 2026-07-19 — Prepare the Core context-pack step

- Files changed: `docs/agent_memory.md`.
- Planned modules: isolated Pydantic context-pack models, a lock-protected immutable repository protocol/adapter, application service, router, dependency wiring, RFC 9457 exceptions/handlers, and API/OpenAPI tests. Existing Vault builder/store remains the authority for which paths are selectable.
- Capture algorithm: load the latest inventory record; normalize, de-duplicate, and sort requested POSIX paths; require every path in that exact snapshot; re-resolve each target under the workspace with the same no-symlink/containment checks; stream-hash at most Vault's allowed 5 MiB; decode at most 16 KiB of text using the existing safe preview behavior; and retain binary files as metadata-only.
- Canonicalization: Pydantic models serialize camelCase JSON; a separate digest payload omits only `id`/`digest`, uses sorted object keys and compact UTF-8 JSON separators, and retains the ordered file array. The resulting `sha256:<hex>` is both resource id and digest.
- Store semantics: `save_if_absent` never replaces a manifest and returns whether this process created it. Listing is sorted by id and returns summaries; storage remains process-local and is explicitly documented as non-durable.
- API/problems: POST returns the typed `{ contextPack, created }` envelope and a deterministic `Location`; repeated creation returns the same manifest with `created: false`. Add problem identities for invalid selection, excluded/changed files, oversized request, and missing pack; reuse missing workspace and inventory-not-built problems where exact semantics already match.
- Follow-up: implement and verify Core before changing Studio.

### 2026-07-19 — Implement and verify immutable Core context packs

- Files changed: `services/core/src/mensura_core/{context_pack_models,context_pack_repositories,context_pack_service,exceptions,main}.py`, `services/core/src/mensura_core/api/{dependencies,problems,router,routers/context_packs}.py`, `services/core/tests/{test_context_pack_api,test_openapi}.py`, and `docs/agent_memory.md`.
- Architecture: `ContextPackService` depends on the existing Core workspace repository, the same injected latest-inventory repository used by `VaultService`, and a separate immutable repository protocol. The default adapter stores manifests process-locally under `(workspaceId, digest)` and only supports save-if-absent, list, and get.
- Creation behavior: requires a built inventory and 1–50 unique normalized POSIX paths; sorts paths case-insensitively with an exact tie-break; rejects missing/excluded/traversing paths; rechecks root containment, every symlink component, regular-file state, current size, and Vault's 5 MiB ceiling before capture.
- Exact evidence: streams every allowed file through SHA-256 without retaining full content; text entries capture at most 16 KiB of strict UTF-8 without splitting a trailing code point; binary entries retain only metadata and digest. Any size/classification/unavailability drift produces a `409` and asks the client to refresh inventory.
- Limits: aggregate text preview bytes may not exceed 256 KiB. The service rejects the whole request with `413` if either the 50-file or aggregate-preview limit is exceeded; it never silently drops selected evidence.
- Identity: canonical compact UTF-8 JSON uses sorted object keys and contains schema/workspace/inventory ids, explicit limits, aggregate summary, and deterministically ordered complete entries. SHA-256 of this payload becomes both `id` and `digest`; creation time is absent, so identical unchanged selection against one inventory produces byte-identical manifests and idempotent storage.
- API: added POST/list/get workspace-scoped routes. POST returns `{ contextPack, created }`, always sets a deterministic `Location`, and reports `created: false` with the exact stored manifest on duplicate content. No update/delete route exists.
- Problems: added stable context-pack invalid-selection (422), too-large (413), changed-file (409), and not-found (404) RFC 9457 types; reused existing missing workspace/inventory, Vault path-invalid, and Vault excluded-file types where semantics are identical.
- Verification: Ruff lint/format pass and all 47 Core tests pass with warnings treated as errors. Coverage includes deterministic reversed-order creation, same input/same id, per-file hashes, binary metadata-only behavior, UTF-8 truncation, both limit classes, path/exclusion/duplicate/drift failures, missing inventory/workspace/pack, list/get, camelCase schemas, and exact endpoint surface.
- Follow-up: add the typed Studio client/query/mutation and a compact explicit selection/immutable-review panel without task/run attachment.

### 2026-07-19 — Prepare the Studio context-pack step

- Files changed: `docs/agent_memory.md`.
- Client/query plan: add create/list/get methods and workspace-scoped collection/manifest keys. The create mutation seeds the exact manifest, invalidates the summary list, and selects the returned deterministic id; no optimistic manifest is fabricated.
- UI plan: a separate full-width active-workspace panel consumes the existing bounded Vault file query, renders checkboxes with text/binary and size cues, shows selected count plus a conservative per-file preview upper-bound, and disables creation for empty or over-limit selection.
- Review plan: show process-local packs in a compact list; opening one fetches the immutable manifest and renders id/digest, inventory id, aggregate counts/bytes, ordered file rows, capture mode, content digest, and preview/truncation byte indicators. Do not render preview bodies in the main UI.
- State boundary: selected paths and opened pack id are small component-local state; all API resources remain in TanStack Query. A Vault refresh can make a selection stale, and Core remains authoritative with a structured action-local problem.
- Test plan: cover typed URLs/body, no-selection/no-inventory states, explicit selection and estimate, pending creation, successful immutable review, reopening a listed pack, binary cues, and RFC 9457 mutation errors.
- Follow-up: implement Studio and verify it independently before documentation and native acceptance.

### 2026-07-19 — Implement and verify the Studio context-pack builder/reviewer

- Files changed: `apps/studio/src/api/{coreClient,coreClient.test}.ts`, `apps/studio/src/app/App.tsx`, `apps/studio/src/app/queryClient.ts`, `apps/studio/src/features/context-packs/{ContextPackPanel,ContextPackPanel.test}.tsx`, `apps/studio/src/test/render.tsx`, `apps/studio/src/styles.css`, and `docs/agent_memory.md`.
- Typed transport: added create/list/get client methods with encoded workspace/digest path values and typed shared request/response contracts. Added separate workspace-scoped collection, candidate-file, and manifest query keys so the builder's 500-file inventory view cannot collide with Vault's 200-file inspector cache entry.
- Builder: requires active workspace plus ready inventory; displays up to 500 deterministic inventoried files as labeled checkboxes; shows exact selected paths, text-preview vs binary-metadata policy, selected count, and a conservative preview-byte upper bound before submission. Empty selection and >50-file/>256-KiB estimates disable creation with local guidance.
- Mutation/review: submits the explicit path array, keeps selection on failure, shows a bounded pending state, seeds the exact returned manifest cache, refreshes the pack list, and distinguishes new creation from idempotent reopening. No optimistic digest or manifest is fabricated.
- Immutable library: lists process-local summaries and opens any digest in read-only mode. Review shows schema/locked state, full pack digest, inventory snapshot id, aggregate file/byte/truncation counts, ordered paths, capture modes, full per-file content digests, and captured/total byte indicators; preview bodies are intentionally not rendered.
- Failure isolation/accessibility: labels are native checkbox labels; selection/pending/success states are announced; RFC 9457 errors remain adjacent to creation or manifest retrieval; missing inventory is neutral guidance; the panel does not disable Vault, Guard, task, or run flows.
- Verification: Studio strict typecheck, all 42 tests across 13 files, and Vite production build pass. Tests cover client paths/body encoding, no-workspace/no-inventory guidance, exact text/binary selection, preview estimate, pending create, immediate locked review, listed-pack retrieval, hidden preview body, and preserved selection on structured server refusal.
- Live issue resolved: the initial collection invalidation used TanStack Query's prefix matching and unnecessarily refetched the candidate file list plus the seeded open manifest. Setting `exact: true` now refreshes only the pack-summary collection while preserving immediate immutable review and avoiding redundant filesystem reads.
- State issue resolved: the candidate-file query key now includes the concrete inventory id. A Vault refresh therefore creates a new candidate cache entry immediately instead of briefly offering paths from the previous snapshot; Core's current-inventory validation remains authoritative.
- Explicitly deferred: task/run attachment, provider execution, prompt rendering, editable packs, full captured text display, durable history, pagination/search, and background inventory synchronization.
- Follow-up: update user-facing docs, run the full monorepo/Core suite, then verify live Uvicorn and release Tauri behavior on the Mensura repository.

### 2026-07-19 — Prepare cycle 8 acceptance and documentation

- Files changed: `docs/agent_memory.md`.
- Documentation plan: update root/Core/Studio READMEs with the three endpoints, deterministic identity/capture limits, metadata-only binary behavior, process-local storage, and the builder/review workflow without overstating task/run or provider integration.
- Regression plan: run `pnpm check`, Core Ruff lint/format and pytest with warnings as errors, Cargo format, `git diff --check`, production scans for forbidden provider/repository-write behavior, and a release desktop bundle if local packaging remains available.
- Live plan: start Core against a clean process, create a Mensura workspace/inventory, use Studio to select real inventoried files, create/reopen a pack, confirm list/get and exact digest behavior in Core logs/UI, and stop all processes cleanly.
- Follow-up: only mark the cycle complete after documented counts and live evidence match the shipped contracts.

### 2026-07-19 — Tighten a generated-artifact rule found during native acceptance

- Files changed before implementation: `docs/agent_memory.md`.
- Observation: the release Tauri build creates ignored schema output under `apps/*/src-tauri/gen`; the current fixed Vault traversal offered those files as selectable context because general `.gitignore` interpretation is intentionally deferred.
- Decision: add one explicit case-insensitive `src-tauri/gen` directory-path exclusion, count each pruned directory once, and apply the same rule to direct context-pack selection validation. Do not add a broad `gen` directory exclusion that could hide legitimate source.
- Verification plan: add the synthetic Tauri path to the existing Vault fixture, keep included-file expectations unchanged, increment excluded count once, rerun Core/full checks, and confirm a rebuilt real Mensura inventory no longer returns any `/src-tauri/gen/` path.
- Files changed after implementation: `services/core/src/mensura_core/vault_inventory.py`, `services/core/tests/test_vault_api.py`, `services/core/README.md`, and `docs/agent_memory.md`.
- Implemented: traversal and direct relative-path checks now prune only directory paths ending in the case-insensitive pair `src-tauri/gen`; a generic directory named `gen` remains eligible. The directory counts once and its generated schemas are never enumerated or selectable by a context pack.
- Verification: Ruff lint/format and all 47 Core tests pass with warnings as errors. A direct rebuild over the real repository reports 149 included/23 excluded entries and zero paths containing `/src-tauri/gen/`.

### 2026-07-19 — Complete work cycle 8 acceptance

- Files changed: 28 files across shared contracts, Core models/service/repository/router/problems/tests, Studio client/query/panel/styles/tests, Vault's Tauri-generated path rule, root/Core/Studio READMEs, and this journal.
- Full verification: `pnpm check` passes strict shared/Studio typechecks, 16 shared tests, 42 Studio tests, both production builds, and native Cargo check. Core Ruff lint/format and all 47 tests pass with warnings treated as errors. Cargo format, `git diff --check`, and the production scan for context-pack subprocess/provider/repository-write calls pass.
- Release artifacts: a full `pnpm studio:build` succeeded and produced the optimized binary, `Mensura Studio.app`, and `Mensura Studio_0.1.0_aarch64.dmg`. After the query-key refinements, a second packaging request could not start because the approval service returned HTTP 503; the safer `tauri build --no-bundle` then rebuilt the final optimized release binary successfully after both cache fixes. The packaged app used for live acceptance contains the complete feature; only the redundant-refetch and snapshot-key refinements landed afterward.
- Live native acceptance: started a fresh Uvicorn Core and the release Tauri app; created and selected the Mensura workspace; built inventory; selected `apps/studio/README.md` as text and `apps/studio/src-tauri/icons/128x128.png` as binary; created a two-file pack; reviewed locked schema/inventory/aggregate/path/capture/digest metadata; reopened the exact same pack; and quit Studio/Core cleanly.
- Live identity/evidence: pack id `sha256:89199f552b174d3e72ffd63e5fd9728882d1d00fd5d394be0dc7d2d5495c0e97`; UI showed 8.9 KiB file bytes, 5.3 KiB preview bytes, zero truncations, 5.3 KiB text capture, zero-byte binary preview, and full distinct per-file digests. Core logs confirmed POST create, GET list, encoded-digest GET, and repeated idempotent POST all succeeded.
- Acceptance follow-up: the live build exposed ignored Tauri generated schemas in inventory; the specific `src-tauri/gen` exclusion and regression coverage now remove them. Final direct real-repository inventory is 149 included/23 excluded with zero generated-schema paths.
- Definition of done: a user can explicitly select inventoried files, create a stable immutable pack, review exact bounded evidence in Studio, list/get/reopen it, and receive predictable RFC 9457 failures. No provider/model execution, prompt rendering, task/run attachment, embeddings, repository writes, watchers, or durable storage were introduced.
- Next priority: make queued run creation accept and immutably record a reviewed `contextPackId`, validate that task/workspace/pack ownership agrees, and show the exact binding in Studio. Provider execution should follow only after that reproducibility link exists.

### 2026-07-19 16:34 MSK — Start work cycle 7: deterministic Vault inventory

- Files changed: `docs/agent_memory.md`.
- Audit: confirmed a clean worktree at `a893268`; re-read the Vault requirements in the master spec, PRD, architecture, roadmap, API outline, setup guide, current journal, and the existing shared/Core/Studio adapter patterns. The seven-commit history has no bug magnets or firefighting commits; current hotspots are the expected journal, README, shared export, Studio client/App/styles, and test helper seams.
- Contract boundary: add isolated Vault v1 models for a ready inventory snapshot, aggregate extension/language counts, deterministic file metadata, filtered file collections, and bounded UTF-8 preview metadata. Do not reuse Git status models or imply semantic relevance, chunks, embeddings, or persisted memory.
- Inventory boundary: build manually from the stored workspace root; sort all paths deterministically; never follow symlinks; prune fixed generated/dependency/VCS directories; exclude sensitive names, large/generated artifacts, and non-regular entries; classify remaining files conservatively as UTF-8 text or binary; retain only the latest snapshot in a replaceable in-memory store.
- Retrieval boundary: list snapshot metadata with optional case-insensitive path/name query and exact normalized extension filtering; preview only a path already present in the latest snapshot; resolve it inside the workspace again; refuse excluded, missing, changed-to-symlink, and binary targets; return at most 16 KiB of decoded UTF-8 with byte counts and an explicit truncation flag.
- API boundary: use synchronous `POST /api/v1/workspaces/{workspace_id}/vault/inventory` for build/refresh, `GET .../vault/inventory` for the latest summary, `GET .../vault/files` for deterministic metadata, and `GET .../vault/files/content?path=...` for preview. Missing workspace stays the existing resource problem; Vault adds stable RFC 9457 identities for invalid roots, absent inventory, invalid/traversing paths, excluded paths, missing files, and binary preview refusal.
- Studio boundary: one independent active-workspace TanStack Query panel with manual build/refresh, compact counts and language summary, bounded file list, explicit selection, metadata, and bounded preview. Inventory/preview problems remain local and do not disable repository, Guard, task, or run panels.
- Explicitly deferred: embeddings, semantic search, Tree-sitter, chunking, graph memory, watchers, repository writes, Git-ignore interpretation, content search, full file browser/editor, background indexing, durable snapshots, and task/run context assembly.
- Follow-up: define and verify the shared Vault wire contracts before adding filesystem traversal.

### 2026-07-19 — Define and verify the Vault v1 shared contract

- Files changed: `packages/shared-types/src/{vault,vault.test,index}.ts` and `docs/agent_memory.md`.
- Defined: literal `ready` inventory state; conservative `text | binary` file kinds; snapshot identity/workspace/time; included/excluded/text/binary/byte aggregates; deterministic extension/language count arrays; file path/name/extension/language/kind/size metadata; filtered collection totals; and UTF-8 preview text/byte/truncation fields.
- Isolation: Vault transport types live in `vault.ts` and do not extend Git diff metadata, Guard results, or task/run entities. The contract contains no embedding, score, chunk, syntax tree, graph, file mutation, or semantic-search field.
- Verification: strict TypeScript checking and all 14 shared tests across four files pass; exact inventory-state and file-kind vocabularies are regression tested.
- Follow-up: implement Core traversal, classification, latest-snapshot storage, retrieval, problems, and API/OpenAPI tests against this contract.

### 2026-07-19 — Prepare the Core Vault inventory step

- Files changed: `docs/agent_memory.md`.
- Planned modules: isolate Pydantic Vault API models, fixed inventory rules/classifier, filesystem inventory adapter, lock-protected latest-snapshot repository, Vault application service, routers, and problem handlers. `VaultService` depends on the existing workspace repository plus replaceable inventory/store protocols; resource and Guard services remain unchanged.
- Traversal rules: use sorted `os.scandir` recursion without following symlinks; exclude fixed case-insensitive directory names (`.git`, dependencies, virtual environments, caches, and common build outputs); exclude sensitive names/key material, generated/archive/binary artifact suffixes, files over 5 MiB, symlinks, sockets/devices, and unreadable entries. A pruned directory counts as one excluded entry.
- Classification rules: keep included binary files as metadata but refuse preview. Known binary extensions, NUL bytes, invalid UTF-8, or a high control-character ratio classify conservatively as binary; otherwise classification is text. Language is a small extension/name lookup only, never parser inference.
- Retrieval rules: inventory list filtering is a case-insensitive path substring plus normalized exact extension with a 1–500 result limit. Preview requires a safe normalized relative POSIX path present in the latest snapshot, revalidates containment/non-symlink/regular-file state, reads at most 16 KiB plus one byte, and refuses content that is or has become binary.
- Test boundary: synthetic real directories cover deterministic sorting/counts, all required exclusions, language/extension counts, text/binary classification, preview truncation, traversal/absolute/excluded/binary/missing/refreshed-file errors, workspace/root/no-inventory problems, filters, safe media types, and exact OpenAPI surface.
- Follow-up: implement and independently verify Core before adding any Studio code.

### 2026-07-19 — Implement and verify Core Vault inventory and retrieval

- Files changed: `services/core/src/mensura_core/{vault_models,vault_inventory,vault_repositories,vault_service,exceptions,main}.py`, `services/core/src/mensura_core/api/{dependencies,problems,router,routers/vault}.py`, `services/core/tests/{test_vault_api,test_openapi}.py`, and `docs/agent_memory.md`.
- Adapter design: `VaultService` depends on the existing workspace repository, a `VaultInventoryBuilder` protocol, and a `VaultInventoryRepository` protocol. The default local builder owns read-only filesystem traversal/classification; the default lock-protected store keeps one immutable snapshot and item tuple per workspace. Routes depend only on `VaultService`.
- Implemented rules: traversal uses deterministic case-folded path ordering and does not follow symlinks. It prunes VCS, Node/pnpm, Python virtual environment/cache, general cache, Next, build/dist/coverage/target/out/output directories; excludes sensitive environment/credential/key paths, OS metadata, compiled/archive artifacts, files over 5 MiB, symlinks, non-regular nodes, and unreadable entries; and counts every pruned or excluded entry once.
- Classification: known media/document suffixes and NUL/invalid-UTF-8/control-heavy samples classify as binary; other readable samples classify as text. Binary items remain inventory metadata but cannot be previewed. A fixed small extension/name table labels common languages without parsing content.
- API/storage: added build/refresh `POST .../vault/inventory` (`201`), latest summary `GET .../vault/inventory`, filtered metadata `GET .../vault/files`, and bounded preview `GET .../vault/files/content?path=...`. Each build receives a new UUID/time and atomically replaces the process-local latest record after successful traversal.
- Retrieval safety: request paths must be canonical relative POSIX paths; absolute, backslash, dot-normalized, and parent traversal forms are rejected. Preview verifies every path component is not a symlink, resolves inside the current root, rechecks file/size/binary state, reads only 16 KiB plus one sentinel byte, safely handles an incomplete terminal UTF-8 code point, and reports exact preview/total byte counts and truncation.
- RFC 9457 problems: `vault-root-invalid` (409), `vault-inventory-not-built` (404), `vault-path-invalid` (422), `vault-file-excluded` (403), `vault-binary-preview-refused` (415), and `vault-file-not-found` (404), while missing workspace remains `resource-not-found`.
- Verification: Core Ruff lint/format passes and all 43 Python tests pass with warnings treated as errors. New tests cover deterministic real-directory inventory, every fixed directory rule, summaries, path/extension/limit filtering, refresh replacement, bounded text, binary and changed-to-binary refusal, sensitive/symlink refusal, traversal/absolute rejection, missing workspace/root/inventory/file, exact media types, and OpenAPI models/routes.
- Follow-up: add the typed Studio client/query/mutation panel and independently verify selection, summary, list, preview, and local problem states.

### 2026-07-19 — Prepare the Studio Vault inspector step

- Files changed: `docs/agent_memory.md`.
- Planned client/query boundary: add typed build/get/list/preview Core methods; workspace-scoped inventory and file-list query keys; a path-scoped preview key; and a manual build mutation that seeds the snapshot then invalidates metadata. No inventory data enters localStorage or a global client-state store.
- Planned UI: no-selection guidance; neutral not-built state with `Build inventory`; visible building/refreshing state; ready summary counts and a short language breakdown; a scroll-bounded deterministic file button list; selected-file metadata; and separately loading/refused/bounded preview. Binary selection is inspectable metadata and should show a concise preview-unavailable state without issuing a request.
- Failure isolation: inventory/list/build problems render inside Vault; preview problems render only in the inspector. The panel must not hide or disable repository, Guard, workspace, task, or run features.
- Test boundary: typed URL/query encoding; no selection/no inventory; pending build then ready refresh; compact counts/languages/files; selection and bounded preview; binary no-request behavior; RFC 9457 build/list/preview errors; and App-level independence.
- Follow-up: implement this one panel without routing, editor behavior, content search, virtualized tree, automatic indexing, or semantic controls.

### 2026-07-19 — Implement and verify the Studio Vault panel

- Files changed: `apps/studio/src/api/{coreClient,coreClient.test}.ts`, `apps/studio/src/app/{App,App.test}.tsx`, `apps/studio/src/app/queryClient.ts`, `apps/studio/src/features/vault/{VaultPanel,VaultPanel.test}.tsx`, `apps/studio/src/test/render.tsx`, `apps/studio/src/styles.css`, and `docs/agent_memory.md`.
- Client/state: added typed build/get/list/preview methods with encoded workspace IDs, filters, and file paths; workspace inventory/list and path preview query keys; manual build mutation; immediate snapshot cache seeding; file-list invalidation; and removal of stale preview queries. Only selected path is component state.
- UI: active-workspace-only Build/Refresh action, visible traversal pending state, neutral no-inventory guidance, five compact aggregate cells, a bounded language badge summary, scroll-bounded file buttons, file metadata inspector, separately loading text preview, byte/truncation evidence, and independent Problem Details rendering.
- Binary behavior: binary files remain selectable and show path/kind/language/size metadata, but Studio makes no content request and states that text preview is unavailable. This avoids a predictable 415 round trip without hiding the item.
- Isolation/scope: switching workspace remounts and clears the selection; refresh clears selection and preview cache; Vault failure does not affect any other panel. No search form, repository tree, editor, route, content search, local persistence, watcher, auto-build, semantic score, or global client-state library was added.
- Verification: strict Studio TypeScript checking and all 36 tests across 12 files pass. New coverage verifies all four client URLs, neutral states, pending build then ready cache/list flow, counts/languages, text selection/preview, binary no-request behavior, local RFC 9457 preview refusal, and existing App task-flow independence.
- Issue resolved: initial tests attempted file selection after summary readiness but before the independent metadata query completed, and one assertion ignored the intentional duplicate path in list plus inspector. Tests now await the accessible file button and assert both semantic locations rather than coupling queries.
- Follow-up: document exact user-visible behavior and filtering limits, then execute full workspace/Core/native build plus live Core/release-Studio inventory and preview verification.

### 2026-07-19 — Prepare seventh-cycle documentation and acceptance verification

- Files changed: `docs/agent_memory.md`.
- Documentation plan: update root/Core/Studio READMEs with all four endpoints, process-local refresh semantics, fixed exclusion/classification rules, 5 MiB inventory limit, 16 KiB UTF-8 preview cap, list filtering/limit, sensitive/binary refusals, Studio workflow, and explicit non-semantic/read-only scope.
- Automated verification plan: run root `pnpm check`, Core Ruff/format and all tests with warnings as errors, Rust format, and `git diff --check`; inspect OpenAPI endpoint/model surface and scan production Vault code for filesystem write calls or traversal weaknesses.
- Live HTTP plan: start fresh Uvicorn, create a Mensura-root workspace, confirm 404 before build, POST inventory, verify sorted metadata/filtering, preview this README, binary-refusal behavior against an available binary asset, and matching latest snapshot.
- Native plan: build the final release Studio app/DMG, launch it against that same Core process, select the workspace, observe no-inventory/build pending/ready summary, select a text file, confirm bounded preview metadata, then stop both processes cleanly.
- Evidence boundary: live file/count values describe the current working tree at build time and may change with generated/ignored local files that do not match fixed exclusions. Success proves deterministic local metadata and bounded retrieval, not semantic relevance, persisted indexing, complete secret detection, or OS sandboxing.
- Follow-up: implement documentation, run the matrix, and record only observed results before committing.

### 2026-07-19 16:55 MSK — Verify and complete the minimal Vault vertical slice

- Files changed: shared Vault contracts/tests/exports; Core Vault models, rules/builder, store, service, routes, problems, wiring, OpenAPI/API tests, and README; Studio typed client/query/App integration, Vault panel/tests/styles, test client, and README; root README and `docs/agent_memory.md`.
- Endpoints: added `POST` and `GET /api/v1/workspaces/{workspace_id}/vault/inventory`, `GET .../vault/files`, and `GET .../vault/files/content?path=...`. Core now exposes 14 HTTP operations across 12 paths including health and all previous resources.
- Automated verification: root `pnpm check` passed strict shared/Studio typechecks, 14 shared tests, 36 Studio tests, production shared/frontend builds, and native `cargo check`; Core Ruff lint/format and all 43 Python tests passed with warnings as errors; Rust formatting, `git diff --check`, and a production Vault scan for filesystem writes/subprocesses passed.
- Native build: final Studio code produced the optimized release binary, `Mensura Studio.app`, and the arm64 DMG through `pnpm studio:build`.
- Live API result: fresh Core returned `404 application/problem+json` before build, then inventoried the current Mensura working tree as 144 included files, 21 excluded entries, 127 text files, 17 binary files, and 1,144,523 included bytes. Paths were deterministic; `.py` filtering returned 36 matches; README preview returned exact byte/truncation metadata; PNG preview returned `415 application/problem+json` with `vault-binary-preview-refused`.
- Verification issue resolved: the first real inventory exposed repository-local `.pnpm-store` cache contents, `.DS_Store`, and pnpm database files as metadata. Added fixed `.pnpm-store`/`.cache` pruning plus OS-metadata exclusions and regression coverage; the rebuilt snapshot dropped from 158 to 144 files, removed those artifacts, and retained source/configuration paths.
- Native Studio result: the release WebView restored/reconciled active workspace state, loaded the 144/21/127/17 summary, showed six language badges and 144 deterministic file buttons, selected `apps/studio/README.md`, displayed its Markdown metadata and 4.3 KiB bounded preview, selected a PNG and showed binary metadata without a preview request, then manually refreshed inventory and cleared stale selection. Core logged the WebView inventory/list/preview requests, refresh `POST 201`, and refreshed list `200`; Studio and Core stopped cleanly.
- Working boundary: Vault reads only; one latest snapshot lives in process memory; listing returns at most 200 items in Studio (API maximum 500); preview is strict UTF-8 capped at 16 KiB; binary/sensitive/generated/large/unsafe paths are refused. Fixed rules are deterministic but do not interpret `.gitignore`, guarantee secret detection, or make a filesystem snapshot atomic against concurrent external changes.
- Intentionally deferred: embeddings, semantic/content search, Tree-sitter, chunks, graph memory, watchers, repository writes, durable snapshots, full tree/editor UI, automatic indexing, branch-aware history, and task/run context assembly.
- Next priority: add a task/run-linked, immutable context-pack slice in which the user selects inventoried files, Core captures their bounded metadata/previews under a stable manifest, and Studio reviews the exact context before any provider execution. This connects Vault to orchestration without inventing a fake agent engine.

### 2026-07-19 16:06 MSK — Start work cycle 6: minimal Guard runner

- Files changed: `docs/agent_memory.md`.
- Audit: confirmed a clean worktree at `6552d2d`; re-read the Guard specification/API outline, existing aspirational check types, Core service/dependency/router/problem/storage patterns, Studio active-workspace client/query/mutation panels, and current cycle-5 verification notes. No Mensura-specific external memory entry exists, so repository contracts remain authoritative.
- Configuration boundary: use one repository-local `.mensura/guard.json` with literal version 1, required `lint` and `test` entries, argv-array commands, per-check `blocking` flags, and one shared `timeoutSeconds` constrained to 1–300 seconds. Configuration is explicit and manually invoked; there is no command discovery, shell parsing, plugin policy, or auto-run behavior.
- Execution safety before implementation: run argv with `shell=False` and workspace `rootPath` as cwd; reject missing/non-directory roots, oversized/malformed/out-of-root configuration, empty/oversized command tokens, and concurrent runs for the same workspace; bound each command by timeout and capture at most 8 KiB per stdout/stderr stream while draining excess output to avoid pipe deadlock.
- Result boundary: add isolated v1 Guard request/response contracts for lint/test, passed/failed/error check states, per-check command/exit/duration/compact output, aggregate counts, and an explicit overall blocking boolean. Non-zero exit codes are structured check failures; process-start failures are RFC 9457 execution errors; timeouts are structured error checks so a completed request remains observable.
- Storage/API boundary: keep only the latest completed Guard run per workspace in a replaceable lock-protected in-memory store; expose `POST /api/v1/workspaces/{workspace_id}/guard/runs` and `GET /api/v1/workspaces/{workspace_id}/guard/runs/latest`. The POST is synchronous in this cycle and must execute in FastAPI's worker thread rather than blocking the event loop.
- Studio boundary: one independent TanStack Query/mutation panel for the active workspace with manual `Run checks`, pending state, overall pass/fail/blocking badge, per-check compact summaries, optional collapsed output, and local RFC 9457 errors. No auto-run, background polling, policy editing, log console, or global state is added.
- Explicitly deferred: full policy engine, format/security/dependency/secret checks, Vault, auth, plugins, CI, background workers/queues, run-task orchestration, durable Guard history, cancellation, streaming output, and broad language/toolchain discovery.
- Follow-up: define and verify the shared Guard wire contracts before implementing command execution.

### 2026-07-19 — Define the Guard v1 shared contract

- Files changed: `packages/shared-types/src/{guard,guard.test,index}.ts` and `docs/agent_memory.md`.
- Defined: exact `lint | test` check kinds; `passed | failed | error` check states; `passed | failed` run states; optional check selection request; per-check blocking/command/exit/duration/stdout/stderr/truncation fields; aggregate total/pass/fail/error/blocking-failure counts; top-level blocking state; UUID/timestamp run response.
- Compatibility choice: these transport types are isolated in `guard.ts` rather than expanding the earlier aspirational domain `CheckResult`, whose broader format/unit/integration/security vocabulary belongs to later policy work.
- Semantics: any failed or error check makes overall status `failed`; only a failed/error check configured as blocking makes `blocking` and `summary.isBlocking` true. This preserves visibility of non-blocking failures without pretending the check passed.
- Verification: shared strict TypeScript checking and 12 tests pass, including exact MVP Guard vocabulary.
- Follow-up: implement the repository-local config loader, bounded subprocess adapter, latest-run store, Guard service, RFC 9457 handlers, and both workspace-scoped endpoints before changing Studio.

### 2026-07-19 — Prepare the Core Guard execution step

- Files changed: `docs/agent_memory.md`.
- Planned modules: isolate Pydantic Guard API/config models, JSON config loading, subprocess execution, in-memory latest-run storage, and Guard application service. Routers depend only on `GuardService`; Git/task/run services do not execute commands.
- Process contract: execute sequentially in requested/config order, use no shell, retain argv in the result, measure monotonic duration, drain stdout/stderr concurrently into bounded buffers, terminate the process group on timeout where supported, and never interpret command output as instructions.
- Error contract: missing config `guard-configuration-not-found` (404); invalid/unsafe config `invalid-guard-configuration` (422); missing/non-directory workspace root `unsupported-workspace-state` (409); process spawn failure `guard-execution-failed` (500); same-workspace overlap `guard-run-in-progress` (409); no latest result uses normal resource-not-found (404).
- Test contract: deterministic fake runner tests cover aggregate semantics and storage; real bounded runner tests cover cwd, stdout/stderr, exit code, truncation, and timeout; API tests cover pass, lint fail, test fail, missing config/workspace, invalid config, execution error, latest lookup, camelCase/OpenAPI, and compact output.
- Follow-up: implement and independently verify Core with no Studio dependency.

### 2026-07-19 — Implement and verify the bounded Core Guard runner

- Files changed: `services/core/src/mensura_core/{guard_models,guard_config,guard_runner,guard_repositories,guard_service,exceptions,main}.py`, `services/core/src/mensura_core/api/{dependencies,problems,router,routers/guard}.py`, `services/core/tests/{test_guard_runner,test_guard_api,test_openapi}.py`, and `docs/agent_memory.md`.
- Implemented architecture: `GuardService` depends on separate configuration-loader, command-runner, latest-run repository, and existing workspace repository protocols. `create_app` wires JSON/Git-independent defaults while keeping every Guard adapter injectable for future storage/runner replacements.
- Controlled configuration: `.mensura/guard.json` is strict camelCase v1 JSON capped at 64 KiB and cannot resolve outside the workspace. Both checks are required. Lint may invoke only Ruff and test only pytest, either directly or via a narrowly recognized Python executable plus `-m`; raw shells, inline eval, arbitrary executables, missing/blank/newline tokens, unknown fields, and out-of-range timeouts are rejected.
- Bounded execution: commands run sequentially with `shell=False`, cwd fixed to workspace root, a small environment allowlist, Python startup injection removed, pytest plugin autoload disabled, per-check timeout, POSIX process-group termination, concurrent stdout/stderr draining, and 8 KiB capture per stream. Exit code, duration, command, compact outputs, and truncation are observable.
- Normalization: Ruff JSON failures become diagnostic counts when parseable; pytest/non-JSON failures retain exit-code summaries; timeout becomes a structured `error` result with null exit code; failed/error checks set overall `failed`, while only configured blocking failures set the blocking decision.
- API/storage: added synchronous `POST /api/v1/workspaces/{workspace_id}/guard/runs` (runs in FastAPI's worker thread) and `GET .../latest`; only the latest completed response is stored per workspace in process memory. A lock prevents overlapping runs for one workspace without serializing different workspaces.
- Problems: stable RFC 9457 URNs cover missing config, invalid config, unsupported root, process-start failure, and run-in-progress; missing workspace/latest result uses the existing resource-not-found contract. Expected non-zero check exits remain `201` structured results, not HTTP errors.
- Verification: Ruff lint/format passed and all 34 Core tests passed with warnings treated as errors. Tests execute real disposable Ruff/pytest workspaces for pass, blocking lint failure, non-blocking test failure, latest retrieval, missing config/workspace/root, invalid tool, sanitized spawn failure, plus runner cwd/streams/truncation/timeout/start-failure behavior and OpenAPI shape.
- Issue resolved: the first warnings-as-errors run exposed unclosed parent pipe handles after reader threads completed. Explicit handle closure removed ResourceWarnings without weakening bounded draining.
- Follow-up: add the typed Studio client/query/mutation panel and verify UI behavior independently before creating the repository's real Guard config.

### 2026-07-19 — Prepare the Studio Guard result step

- Files changed: `docs/agent_memory.md`.
- Planned client/query boundary: add typed `createGuardRun(workspaceId, request)` and `getLatestGuardRun(workspaceId)` methods plus one workspace-scoped latest query key. The manual mutation seeds the latest response and refetches it non-blockingly, matching existing mutation semantics.
- Planned UI: render no-selection guidance, latest-loading/no-result state, `Run checks` pending control, overall Passed/Failed plus Blocking/Non-blocking badges, aggregate counts, and one compact card each for lint/test. Output stays collapsed in native `<details>` and is omitted entirely when empty.
- Failure isolation: POST/config/execution problems appear next to the action; GET no-latest is an expected empty state rather than a red error, while other RFC 9457 results remain structured. Guard failure does not disable repository/task/run panels.
- Test boundary: cover encoded URLs/request body, no selection, no latest result, pending mutation, passing result, blocking failure, compact/collapsed output, RFC 9457 mutation failure, and App-level independence.
- Follow-up: implement Studio without configuration editing, auto-run, polling, cancellation, or raw log console.

### 2026-07-19 — Implement and verify the Studio Guard panel

- Files changed: `apps/studio/src/api/{coreClient,coreClient.test}.ts`, `apps/studio/src/app/{App,App.test}.tsx`, `apps/studio/src/app/queryClient.ts`, `apps/studio/src/features/guard/{GuardPanel,GuardPanel.test}.tsx`, `apps/studio/src/test/render.tsx`, `apps/studio/src/styles.css`, related Core latest-run problem files/tests, and `docs/agent_memory.md`.
- Implemented client/state: typed create/latest Guard methods with encoded workspace IDs and `{}` request body; one latest-run query key; manual TanStack mutation; immediate latest-cache seeding followed by non-blocking invalidation; no client state store or optimistic check result.
- Implemented UI: active-workspace-only `Run checks`; loading and in-request status; explicit no-history guidance; overall Passed/Failed and Blocking/Non-blocking badges; passed/failed/error/duration counts; compact lint/test cards with summary, exit, duration, configured blocking flag, argv, truncation indicator, and collapsed stdout/stderr only when present.
- Error behavior: introduced `urn:mensura:problem:guard-run-not-found` so an empty latest history is a neutral Studio state without confusing it with a missing workspace. POST configuration/execution problems remain structured action errors. Guard UI/query failure is independent from repository/task/run state.
- Scope held: no config editor, check selection UI, auto-run, interval polling, cancellation, streamed output, policy rules, history list, or full log console.
- Verification: Studio strict TypeScript checking and all 29 tests across 11 files pass. Coverage includes client POST/GET serialization, no selection, no history, pending manual run, passing aggregate/result cards, blocking failure/truncation/collapsed output, RFC 9457 mutation failure, and existing App flow independence.
- Test issue resolved: initial assertions queried duplicate visual labels (`Passed`/`Failed`) shared by the heading and count definitions. Tests now select the semantic `strong`/`dt` elements rather than weakening UI labels.
- Follow-up: add the repository's real explicit Ruff/pytest config, document trust/runtime limits, run the full matrix, then manually trigger Guard against Mensura through live Core and release Studio.

### 2026-07-19 — Prepare repository configuration and acceptance verification

- Files changed: `docs/agent_memory.md`.
- Planned Mensura config: `.mensura/guard.json` v1 with 120-second per-check timeout; blocking Ruff JSON lint over `services/core/src` and `services/core/tests`; blocking pytest over `services/core/tests` with concise output and warnings treated as errors. This intentionally validates the currently implemented Core Guard boundary rather than claiming whole-monorepo language coverage.
- Documentation plan: publish exact config schema/example, Ruff/pytest-only restriction, trusted-config/manual-trigger boundary, synchronous request behavior, output/time limits, latest-only in-memory storage, problem URNs, and Studio interaction. Remove Guard from the deferred list but keep the policy engine and orchestration integration deferred.
- Automated verification plan: run root `pnpm check`, Core Ruff/format and all tests with warnings as errors, Rust format, config JSON validation, and whitespace checks; then build final native app/DMG.
- Live verification plan: start fresh Core, create a workspace for the current Mensura root, confirm neutral latest state, POST a real Guard run, verify both checks pass and GET latest matches, launch the release Studio app, select the workspace, manually click `Run checks`, and observe compact non-blocking passing results plus Core endpoint logs.
- Safety/evidence boundary: the user-authored cycle explicitly authorizes manual configured Guard execution. Only the checked-in Ruff/pytest argv will run, with no shell or discovery. Live success proves current Mensura Core lint/tests, not a general policy engine or full monorepo gate.
- Follow-up: implement configuration/docs and record only observed verification results.

### 2026-07-19 16:29 MSK — Verify and complete the minimal Guard vertical slice

- Files changed: `.mensura/guard.json`, `packages/shared-types/src/{guard,guard.test,index}.ts`, Guard modules/routes/problems/tests under `services/core`, Guard client/query/panel/tests under `apps/studio`, root/Core/Studio READMEs, and `docs/agent_memory.md`.
- Config model: one trusted repository-local `.mensura/guard.json` v1 with required lint and test argv arrays, per-check blocking flags, and a shared 1–300 second timeout. The checked-in Mensura config runs only Core Ruff JSON lint and Core pytest, both blocking, with no shell or command discovery.
- Core result: `POST /api/v1/workspaces/{workspace_id}/guard/runs` executes selected configured checks synchronously and `GET .../latest` returns the latest completed in-memory result. Responses contain stable passed/failed/error states, blocking decisions, exit codes, durations, compact summaries, argv, and at most 8 KiB each of stdout/stderr; non-zero exits are structured `201` results rather than transport failures.
- Studio result: the active-workspace panel manually starts checks, shows an observable pending state, then renders overall pass/fail and blocking state plus compact per-check details. No-history is neutral, RFC 9457 problems remain local to the panel, and captured output is collapsed rather than dumped into the main shell.
- Runner hardening: subprocesses use argv without a shell, fixed workspace cwd, reduced environment, per-check timeout, and process groups where supported. Concurrent readers prevent pipe deadlock; a final regression test proves a completed parent cannot leave the request hanging merely because a descendant inherited its output pipes.
- Automated verification: root `pnpm check` passed strict shared/Studio typechecks, 12 shared tests, 29 Studio tests, production frontend builds, and native `cargo check`; Core Ruff lint/format and all 36 Python tests passed with warnings as errors; Rust formatting, Guard JSON parsing, and `git diff --check` passed.
- Native/live verification: final Studio code produced the release binary, macOS app bundle, and arm64 DMG. Against fresh Uvicorn state, latest-before-run returned the dedicated 404 problem, direct POST returned a two-check passing result and matching latest resource, and the release Studio WebView displayed the prior result, the disabled `Running checks…` state, then a fresh Passed/Non-blocking result. Core logged the WebView POST as `201` and latest refresh as `200`; both processes stopped cleanly.
- Safety boundary: this is controlled execution of trusted project configuration, not OS sandboxing. Ruff and pytest can execute repository Python code and can read/write with Core's operating-system permissions; there is no network isolation, policy pack, auto-run, background worker, cancellation, durable history, or task/run orchestration integration.
- Next priority: add deterministic Vault repository file inventory and basic retrieval behind a replaceable adapter, without embeddings, so the next orchestration slice has explicit inspectable context rather than fabricated agent behavior.

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
- Automated coverage for shared lifecycle, plugin validation, Guard, Vault, and context-pack wire-contract behavior (16 passing tests).
- Python 3.12 FastAPI Core service with enabled OpenAPI and seventeen implemented HTTP operations across fourteen paths.
- Workspace creation/listing with exact-root conflict detection in a process-local repository.
- Task creation/retrieval tied to an existing workspace; created tasks begin in `ready` status.
- Placeholder run creation/retrieval; created runs remain `queued` and perform no orchestration or side effects.
- RFC 9457 `application/problem+json` responses for resource misses, conflicts, request validation, framework HTTP errors, and generic internal failures.
- CamelCase JSON contracts aligned with TypeScript Workspace/Task ownership and documented in OpenAPI.
- Forty-seven passing Core service/runner/API/OpenAPI/Git/Vault/context-pack tests plus successful real-Uvicorn repository inspection, Guard execution, inventory, filtering, preview retrieval, and immutable pack creation/get/list.
- Tauri 2 desktop Studio with React 19, Vite 8, a single resizable window, desktop app icons, CSP, and a local-Core-only native HTTP capability.
- TanStack Query-backed Core health polling, workspace list/create behavior, task lookup, and run lookup with explicit loading, empty, success, connection-error, and RFC 9457 error states.
- Shared Health, workspace transport, and Problem Details contracts aligned with Core's camelCase responses and nullable fields.
- Forty-two passing Studio client/component/acceptance tests and successful native release binary, macOS `.app`, and DMG builds.
- Verified live desktop connectivity from the release Tauri WebView to Core health and workspace endpoints.
- Persisted active workspace selection with stale-ID reconciliation after Core restart.
- Accessible active-workspace task creation with client validation, RFC 9457 failures, value preservation on failure, and immediate ready-task details.
- Reusable queued-run creation from both created and looked-up tasks, with task/run query refresh and immediate queued-run details.
- Verified live Core workspace -> ready task -> queued run POST/GET sequence.
- Isolated shared repository summary/diff-metadata contracts with no patch or file-content fields.
- Replaceable read-only `GitRepositoryAdapter` with a GitPython implementation for branch, detached HEAD, clean/dirty, staged/unstaged/untracked counts, and safe changed-path metadata.
- Workspace-scoped repository inspection endpoint with dedicated RFC 9457 problems for missing paths, non-repositories, and unsupported Git states.
- Compact active-workspace Studio repository panel with independent TanStack Query failure handling and bounded changed-path rendering.
- Isolated shared Guard v1 contracts for lint/test selection, normalized check states, compact output, aggregate counts, and explicit blocking decisions.
- Replaceable Core Guard config/runner/latest-store boundaries with strict repository-local configuration, Ruff/pytest allowlisting, no-shell execution, timeout/process-group handling, bounded concurrent output capture, and same-workspace overlap prevention.
- Workspace-scoped Guard create/latest endpoints with dedicated RFC 9457 problems for missing or invalid configuration, unsupported roots, execution startup failure, overlapping runs, and absent history.
- Compact active-workspace Studio Guard panel with manual execution, visible pending state, overall and per-check status, collapsed bounded output, neutral no-history state, and independent RFC 9457 failure handling.
- Verified live release-Studio -> Core -> configured Ruff/pytest -> normalized Guard result -> refreshed Studio result flow on the Mensura repository.
- Isolated shared Vault v1 contracts for ready snapshots, deterministic metadata, summary counts, file collections, and bounded UTF-8 preview evidence.
- Replaceable Core Vault filesystem-builder/latest-store boundaries with fixed exclusions, no-symlink deterministic traversal, conservative text/binary classification, small language mapping, path/extension filters, and no write/subprocess operations.
- Workspace-scoped Vault build/latest/list/preview endpoints with stable RFC 9457 problems for invalid roots, absent inventory, invalid or excluded paths, binary preview refusal, and missing files.
- Compact active-workspace Studio Vault panel with manual build/refresh, aggregate/language summary, bounded deterministic file list, metadata inspector, bounded text preview, binary no-request state, and isolated errors.
- Verified live release-Studio -> Core -> Mensura inventory -> file metadata -> safe preview -> refresh flow, including discovery and removal of local package-cache/OS artifacts from fixed rules.
- Isolated shared context-pack v1 contracts for pinned schema/limits, deterministic entries, SHA-256 identities, immutable manifests, summaries, and create/list/get transport shapes.
- Replaceable Core context-pack service/repository boundaries that bind to one Vault inventory, revalidate selected paths, stream-hash full allowed files, capture bounded UTF-8 previews, keep binary evidence metadata-only, and store by content-derived identity without update/delete operations.
- Workspace-scoped context-pack create/list/get endpoints with stable RFC 9457 problems for invalid/excluded/changed files, oversized packs, absent inventory, and missing manifests.
- Compact active-workspace Studio builder with explicit pre-creation selection, bounded-size estimates, native checkbox labels, idempotent creation, process-local pack library, and locked manifest review without preview-body dumping.
- Verified live release-Studio -> Core -> real Mensura inventory -> selected text/binary evidence -> deterministic pack -> read-only get/list/reopen flow; native UI displayed stable pack/per-file digests and repeating creation reopened the same id.

## Pending Tasks

### MVP

1. Bind a reviewed immutable context pack to queued run creation, validate workspace ownership, persist the immutable run-context reference, and show it in Studio before any provider call.
2. Implement one observable execution flow: queued run with reviewed context -> explicit provider/runner adapter -> safe diff metadata -> Guard -> review -> approve/reject.
3. Add Docker Compose only for dependencies required by the working flow, plus CI for format, typecheck, tests, and builds.
4. Replace temporary in-memory adapters with durable storage where acceptance criteria require restart-safe history.

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

### Trusted, bounded Guard execution

- Decision: load one strict `.mensura/guard.json` v1 from the workspace, accept argv arrays only, allow Ruff for lint and pytest for tests, and execute them behind injectable loader/runner/store protocols with synchronous workspace-scoped endpoints.
- Reason: the first useful Guard slice needs real project checks and structured blocking results, while explicit tools and no-shell argv keep the execution surface understandable and replaceable without pretending to provide a complete policy or sandbox system.
- Alternatives considered: shell command strings, toolchain auto-discovery, arbitrary executables, a background queue, separate Guard service, raw unbounded logs, and immediate policy packs. Rejected or deferred because they widen trust, add hidden behavior or infrastructure, and are unnecessary for a manually triggered two-check MVP.
- Consequences: configuration is trusted executable project input; Ruff/pytest may execute repository code with the Core process's filesystem/network permissions. Each check is time-bounded, output capture is bounded, overlapping runs for one workspace are rejected, only the latest completed run survives in memory, and transport/storage/runner adapters can later be replaced without changing the v1 response shape.

### Deterministic, read-only Vault inventory

- Decision: use a replaceable local filesystem builder with fixed checked-in rules, conservative sample-based text/binary classification, an in-memory latest-snapshot store, deterministic metadata listing, and 16 KiB strict UTF-8 previews tied to inventoried paths.
- Reason: future execution needs explicit inspectable context now, while parsers, embeddings, watchers, and databases would obscure whether basic inclusion, containment, and retrieval contracts are correct. Fixed rules make the same tree explainable without shelling out or interpreting project commands.
- Alternatives considered: Git tracked-file enumeration, `.gitignore` libraries, content/MIME discovery dependencies, hashing every file, SQLite, background watchers, Tree-sitter chunks, embeddings, and returning full text. Deferred because they add policy, cost, durability, concurrency, or semantic assumptions beyond a minimal inventory; Git-only enumeration would also hide safe untracked context.
- Consequences: one pruned directory counts once; the inventory is not an atomic filesystem snapshot; known safe untracked files can appear; fixed exclusions require maintenance as real repositories expose new local artifacts; language labels are shallow; only one latest record survives per workspace; preview revalidates path containment/symlinks/current binary state and never writes files.

### Immutable, content-derived context packs

- Decision: create context packs only from explicit paths in one latest Vault inventory; capture bounded UTF-8 preview evidence or metadata-only binary evidence; hash every complete allowed file; and derive the immutable resource id from canonical schema/workspace/inventory/limits/summary/entry JSON.
- Reason: a future provider run must have human-reviewable, reproducible input before orchestration exists. Including inventory identity, content digests, exact ordered paths, capture modes, and hard bounds makes evidence changes visible without inventing prompt or model payload formats.
- Alternatives considered: mutable selections, random UUID ids, creation timestamps inside the digest, full file bodies, binary rejection, semantic retrieval, task/run mutation in this cycle, and provider-specific envelopes. Rejected or deferred because they weaken reproducibility, exceed safe review bounds, or couple this evidence layer to execution that does not yet exist.
- Consequences: unchanged selection against one inventory idempotently returns one `sha256:<hex>` resource; rebuilding inventory deliberately changes identity even if paths are unchanged; text capture is capped at 16 KiB/file and 256 KiB/pack; binary content is represented only by metadata/digest; packs disappear on Core restart; no update/delete endpoint or repository write exists; task/run binding is the next explicit compatibility step.

## Open Questions

- Which pagination and authentication contracts should extend the implemented Core v1 resource/error schemas?
- Should local MVP persistence use SQLite before PostgreSQL, or should Dockerized PostgreSQL be required from the first Core service?
- Which model provider should power the first non-stub run, and how should BYOK credentials be stored on each platform?
- What exact sandbox guarantees are required for local command execution on macOS, Linux, and Windows?
- Which project-specific ignore mechanism should extend the fixed Vault rules before team-scale indexing, and when should hashing/durable branch-aware snapshots become necessary?
- Should queued run creation require a context pack immediately, or first allow an explicit nullable immutable reference while older clients migrate?
- How are plugin signatures rooted and verified, and which permissions are allowed for the first local plugin loader?
- Are the `[cite:…]` markers in the specifications backed by a source bibliography that should be added to the repository?
