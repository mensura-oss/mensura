# Agent Memory

## Project Summary

- Mensura is an AGPL-3.0 open-source, local-first and self-hostable agentic development platform for professional developers and teams.
- It combines a desktop workspace (Studio), orchestration (Core), project memory (Vault), quality and policy gates (Guard), extensions (Hub), and optional voice control (Voice).
- The product emphasizes reproducible agent runs, visible diffs and logs, human approval, mandatory checks, open MCP interoperability, and user-managed model providers.
- Current implementation status: the repository now has a runnable pnpm workspace and a tested shared-contracts package; Studio and backend services remain unimplemented.

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

- Git history: one initial commit containing only `LICENSE`; three local/remote branch references; no prior implementation history or code hotspots.
- Documentation: ten complete project specifications exist as untracked source files at the start of this cycle.
- Code at audit time: no applications, services, packages, tests, dependency manifests, CI, or local run scripts existed.
- Code now: pnpm workspace commands, strict shared TypeScript configuration, and `@mensura/shared-types` with domain contracts, guarded task/run transitions, plugin permissions, and runtime manifest validation.
- Toolchain observed locally: Node 22.23.1, pnpm 11.13.1, Rust 1.97.1, Docker 29.6.1, and Docker Compose 5.3.0.
- Python is currently 3.9.6 and does not meet the documented Python 3.12+ prerequisite; FastAPI and `uv` are not installed.
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

## Implemented Functionality

- Persistent repository-local project memory and execution journal.
- Installable pnpm monorepo with a single root health command: `pnpm check`.
- Strictly typed shared Task, Run, Guard check, agent result, and plugin manifest contracts.
- Task lifecycle rules that require review before approval and support revision/retry paths.
- Run lifecycle rules that require checking and an approval checkpoint before completion.
- Runtime plugin manifest validation for supported types and permissions, semantic versions, duplicate permissions, and unsafe entry paths.
- Automated coverage for the implemented lifecycle and plugin validation behavior (10 passing tests).

## Pending Tasks

### MVP

1. Define the minimum versioned Core HTTP/error/event contracts from the shared domain model.
2. Create a runnable FastAPI Core service with health, workspace, task, and in-memory/local-persistence run endpoints; document Python 3.12 setup.
3. Create a minimal Tauri/React Studio shell that connects to Core and shows service/run state.
4. Add local Git repository inspection and safe diff generation behind a Core adapter.
5. Add the first Guard runner for configured lint/test commands with structured, blocking results.
6. Add deterministic Vault repository indexing and basic retrieval; defer embeddings until the ingestion contract is stable.
7. Implement one observable task flow: create task -> run explicit stub/provider adapter -> produce diff -> execute Guard -> review -> approve/reject.
8. Add Docker Compose only for dependencies required by the working flow, plus CI for format, typecheck, tests, and builds.
9. Replace temporary local/in-memory adapters with durable storage where acceptance criteria require restart-safe history.

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

## Open Questions

- What are the versioned request/response schemas, error envelope, pagination rules, and authentication model for the API outline?
- Should local MVP persistence use SQLite before PostgreSQL, or should Dockerized PostgreSQL be required from the first Core service?
- Which model provider should power the first non-stub run, and how should BYOK credentials be stored on each platform?
- What exact sandbox guarantees are required for local command execution on macOS, Linux, and Windows?
- Which file types, ignore rules, chunking rules, and embedding provider define the first Vault index?
- How are plugin signatures rooted and verified, and which permissions are allowed for the first local plugin loader?
- Are the `[cite:…]` markers in the specifications backed by a source bibliography that should be added to the repository?
