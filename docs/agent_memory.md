# Agent Memory

## Project Summary

- Mensura is an AGPL-3.0 open-source, local-first and self-hostable agentic development platform for professional developers and teams.
- It combines a desktop workspace (Studio), orchestration (Core), project memory (Vault), quality and policy gates (Guard), extensions (Hub), and optional voice control (Voice).
- The product emphasizes reproducible agent runs, visible diffs and logs, human approval, mandatory checks, open MCP interoperability, and user-managed model providers.
- Current implementation status: the repository has a runnable pnpm workspace, a tested shared-contracts package, and a verified minimal Mensura Core FastAPI service. Studio, persistence, and agent execution remain unimplemented.

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

- Work cycle 2 implementation and verification are complete; the logical Git commit is pending.
- Core v1 is verified under Python 3.12 with versioned resource routes, predictable errors, replaceable in-memory storage, OpenAPI, and tests. Orchestration and database integration remain explicitly deferred.
- Git history: the initial license commit plus the committed foundation from work cycle 1; no product implementation history is deep enough for meaningful code hotspots yet.
- Documentation: ten project specifications, the root README, and this execution journal are tracked.
- Code at audit time: no applications, services, packages, tests, dependency manifests, CI, or local run scripts existed.
- Code now: pnpm workspace commands, strict shared TypeScript configuration, and `@mensura/shared-types` with domain contracts, guarded task/run transitions, plugin permissions, and runtime manifest validation.
- Toolchain observed locally: Node 22.23.1, pnpm 11.13.1, Rust 1.97.1, Docker 29.6.1, and Docker Compose 5.3.0.
- The default `python3` is 3.9.6, but Homebrew Python 3.12 is available at `/opt/homebrew/bin/python3.12`; FastAPI is not installed globally and Core will use a service-local virtual environment.
- Repository risk history is too small for meaningful hotspot or bug-magnet analysis; current risk is specification breadth and premature scaffolding.

## Completed Work Log

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
- Python 3.12 FastAPI Core service with enabled OpenAPI and seven implemented HTTP endpoints.
- Workspace creation/listing with exact-root conflict detection in a process-local repository.
- Task creation/retrieval tied to an existing workspace; created tasks begin in `ready` status.
- Placeholder run creation/retrieval; created runs remain `queued` and perform no orchestration or side effects.
- RFC 9457 `application/problem+json` responses for resource misses, conflicts, request validation, framework HTTP errors, and generic internal failures.
- CamelCase JSON contracts aligned with TypeScript Workspace/Task ownership and documented in OpenAPI.
- Twelve passing Core API/OpenAPI tests plus a successful real-Uvicorn smoke test.

## Pending Tasks

### MVP

1. Create a minimal Tauri/React Studio shell that connects to Core and shows service/workspace/task/run state.
2. Add local Git repository inspection and safe diff generation behind a Core adapter.
3. Add the first Guard runner for configured lint/test commands with structured, blocking results.
4. Add deterministic Vault repository indexing and basic retrieval; defer embeddings until the ingestion contract is stable.
5. Implement one observable task flow: create task -> run explicit stub/provider adapter -> produce diff -> execute Guard -> review -> approve/reject.
6. Add Docker Compose only for dependencies required by the working flow, plus CI for format, typecheck, tests, and builds.
7. Replace temporary in-memory adapters with durable storage where acceptance criteria require restart-safe history.

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

## Open Questions

- Which pagination and authentication contracts should extend the implemented Core v1 resource/error schemas?
- Should local MVP persistence use SQLite before PostgreSQL, or should Dockerized PostgreSQL be required from the first Core service?
- Which model provider should power the first non-stub run, and how should BYOK credentials be stored on each platform?
- What exact sandbox guarantees are required for local command execution on macOS, Linux, and Windows?
- Which file types, ignore rules, chunking rules, and embedding provider define the first Vault index?
- How are plugin signatures rooted and verified, and which permissions are allowed for the first local plugin loader?
- Are the `[cite:…]` markers in the specifications backed by a source bibliography that should be added to the repository?
