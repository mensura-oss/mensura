# Mensura — Complete Project Master Specification

## Project identity

**Mensura** is an open-source agentic development platform for real developers and teams. It combines AI-assisted coding, multi-agent orchestration, project memory, quality gates, self-hosted deployment, and an extensible plugin ecosystem into a single local-first platform[cite:31][cite:72][cite:85].

The project is designed as an alternative to vibe-only coding tools by emphasizing engineering control, reproducibility, reviewability, and self-hosting. The architectural foundation relies on open standards such as Model Context Protocol (MCP), which is defined as an open protocol for connecting LLM applications with external tools and data sources[cite:31][cite:74].

## Product line

The Mensura brand is organized as a platform with several core modules:

| Module | Purpose |
|---|---|
| Mensura Studio | Desktop client and main developer workspace |
| Mensura Core | Agent orchestration backend and execution engine |
| Mensura Vault | Long-term memory, semantic search, and project knowledge graph |
| Mensura Guard | Quality gates, security policies, review workflow, and auditability |
| Mensura Hub | Plugin ecosystem, MCP connectors, templates, and community extensions |
| Mensura Voice | Optional voice interface for commands, dictation, and hands-free workflows |

## Vision

Mensura enables developers to work with AI agents as controlled collaborators rather than opaque copilots. The platform is optimized for software teams that want speed from AI without losing visibility into changes, test discipline, architectural context, or deployment safety[cite:79][cite:85].

## Product goals

- Create a local-first, self-hostable AI development environment.
- Support both natural-language workflows and traditional coding workflows.
- Provide reproducible agent runs with logged context, outputs, and diffs.
- Make quality checks mandatory before task completion.
- Support open integrations through MCP and plugin APIs.
- Avoid dependency on a proprietary cloud or mandatory billing account.
- Build as a fully open-source project suitable for community contribution.

## Non-goals

- Building a closed SaaS-first experience.
- Replacing Git, CI, or standard code review tools entirely.
- Optimizing only for non-developers.
- Hiding agent behavior behind black-box automation.

## Core use cases

### Solo developer

A solo developer opens Mensura Studio, connects a repository, asks an architect agent to analyze the codebase, assigns implementation subtasks to coding agents, reviews the diffs, runs tests, and merges approved changes locally.

### Team workflow

A team shares a self-hosted Mensura Core instance. Tasks are assigned on a Kanban board, Vault stores project memory, Guard enforces lint/test/security policies, and reviewers inspect agent-generated pull requests.

### Legacy code understanding

Mensura indexes an existing codebase, builds semantic memory, maps dependencies, summarizes architectural modules, and enables targeted questions about design decisions and code history.

### Research and implementation

A developer asks a research agent to inspect framework documentation, generate an implementation plan, create a task breakdown, then hand off validated subtasks to coding and testing agents.

## Target users

- Professional developers.
- Open-source maintainers.
- Small engineering teams.
- Technical founders.
- Security-conscious users who need local or self-hosted operation.
- Educators and learners who want transparent AI-assisted software workflows.

## Differentiation

Mensura differs from vibe-coding-first platforms by combining agent orchestration with engineering rigor. The differentiators include self-hosting, reproducible runs, policy-based permissions, mandatory quality gates, and a modular open plugin system[cite:31][cite:79][cite:85].

## Functional architecture

### 1. Mensura Studio

Mensura Studio is the primary desktop interface.

Key capabilities:
- Multi-pane terminal workspace, target 1–16 panes.
- Integrated code editor using Monaco.
- Repository tree and file search.
- Kanban board for tasks.
- Agent chat with thread history.
- Diff viewer with structured explanations.
- Local command runner.
- Workspace presets per project type.
- Session restore.
- Theme system.

### 2. Mensura Core

Mensura Core is the orchestration backend.

Key capabilities:
- Agent planner and dispatcher.
- Execution queue.
- Tool routing.
- Model routing.
- Run logging.
- Context assembly.
- Prompt/version tracking.
- Retry and failure handling.
- Human approval checkpoints.
- Local and remote execution adapters.

### 3. Mensura Vault

Mensura Vault is the memory and retrieval layer.

Key capabilities:
- Repository indexing.
- Documentation ingestion.
- Semantic code search.
- Decision memory.
- Task memory.
- Embedding storage.
- Graph relationships between files, tasks, docs, and decisions.
- Time-based memory recall.
- Branch-aware memory snapshots.

### 4. Mensura Guard

Mensura Guard is the governance and quality system.

Key capabilities:
- Lint and format checks.
- Test execution gates.
- Secret scanning.
- Dependency vulnerability checks.
- Change-risk scoring.
- Protected path rules.
- Approval policies.
- Audit logs.
- Diff explanation requirements.
- Merge/pre-completion blocking.

### 5. Mensura Hub

Mensura Hub is the extension ecosystem.

Key capabilities:
- MCP connector registry.
- Plugin installation.
- Agent templates.
- Prompt packs.
- Stack templates.
- Workflow recipes.
- Community ratings and metadata.
- Signed plugin manifests.

### 6. Mensura Voice

Mensura Voice is optional.

Key capabilities:
- Dictation to chat or task fields.
- Voice commands for workflow control.
- Push-to-talk for coding commands.
- Local transcription mode.
- Multilingual support.

## User workflows

### Repository onboarding

1. User creates or opens a workspace.
2. User connects a local Git repository.
3. Vault indexes repository files and docs.
4. Core generates an architecture summary.
5. Guard detects available linters, tests, and policy suggestions.
6. Studio proposes an initial project profile.

### Agent-driven task execution

1. User creates a task card in Kanban.
2. User assigns an agent role or accepts an automatic recommendation.
3. Core assembles context from Vault.
4. Agent creates a plan.
5. Guard checks whether approval is needed.
6. Agent writes code in a branch or workspace sandbox.
7. Guard runs formatting, linting, tests, and security checks.
8. Studio presents diff, explanation, logs, and status.
9. User approves or requests revision.

### Research-to-build workflow

1. Research agent gathers relevant docs.
2. Planner agent converts findings into implementation steps.
3. Coder agent modifies files.
4. Test agent writes or updates tests.
5. Reviewer agent critiques the diff.
6. Guard enforces thresholds before task completion.

## Agent system design

### Agent roles

- Architect agent.
- Research agent.
- Coder agent.
- Refactor agent.
- Test agent.
- Reviewer agent.
- Security agent.
- Docs agent.
- DevOps agent.
- Release agent.

### Orchestration model

The primary orchestration approach should be graph-based to support stateful, multi-step workflows and human checkpoints. LangGraph is a strong candidate because it is widely positioned for production-grade, stateful agent systems and complex workflows[cite:72][cite:79][cite:85].

### Agent execution modes

- Single-agent mode.
- Sequential pipeline mode.
- Parallel swarm mode.
- Human-in-the-loop mode.
- Scheduled automation mode.

## Recommended technology stack

### Client

| Layer | Technology | Reason |
|---|---|---|
| Desktop shell | Tauri 2 + Rust | Suitable for developer desktop tools and resource-efficient compared with heavier desktop approaches[cite:73][cite:80] |
| Frontend | React + TypeScript | Mature ecosystem and component flexibility |
| UI framework | Tailwind CSS + shadcn/ui | Fast iteration and maintainable design system |
| Editor | Monaco Editor | Mature code editing capabilities |
| Terminal | xterm.js | Browser-based terminal UI |
| State | Zustand or Redux Toolkit | Predictable local state management |
| Data fetching | TanStack Query | Query caching and sync |
| Local persistence | SQLite or IndexedDB | Fast workspace/session caching |

### Backend

| Layer | Technology | Reason |
|---|---|---|
| API | FastAPI | Strong Python ecosystem for AI tooling |
| Orchestration | LangGraph | Strong fit for stateful multi-step agent execution[cite:72][cite:79][cite:85] |
| Optional role framework | CrewAI | Useful for role-based agent teams[cite:72][cite:76] |
| Async jobs | Celery or Arq | Background job processing |
| Message broker | Redis or NATS | Lightweight coordination and queues |
| Primary DB | PostgreSQL | Reliable structured data store |
| Vector store | pgvector or Qdrant | Semantic retrieval and memory |
| Graph store | Neo4j optional | Relationship-centric memory queries |
| Search indexing | Tantivy or Meilisearch optional | Fast local/project search |

### Standards and integrations

| Concern | Technology | Reason |
|---|---|---|
| Tool interoperability | MCP | Open protocol for connecting LLM apps to tools/data[cite:31][cite:74] |
| Auth for self-host | Keycloak or Authentik optional | Self-hosted identity |
| SCM integration | Git, GitHub, GitLab | Repository workflows |
| Container execution | Docker | Isolated task execution |
| Infra scaling | Kubernetes later | Team deployment option |
| Observability | OpenTelemetry, Prometheus, Grafana | Tracing and metrics |
| Error tracking | Sentry self-host or GlitchTip | Failure visibility |

### Quality and security

| Concern | Tools |
|---|---|
| JS lint/format | ESLint, Prettier |
| Python lint/format | Ruff, ruff-format |
| Tests | Vitest, Jest, Pytest |
| E2E | Playwright |
| Secrets | gitleaks |
| Containers | Trivy |
| Static analysis | Semgrep, SonarQube optional |
| Web quality | Lighthouse CI |

### Voice module

| Concern | Technology |
|---|---|
| Local STT | whisper.cpp |
| Cloud STT optional | Deepgram or OpenAI |
| Voice activity | WebRTC VAD or equivalent |

## Deployment models

### Local desktop only

- Studio runs locally.
- Core runs embedded or as a local sidecar.
- Vault uses SQLite + local vector DB.
- Ideal for solo developers.

### Self-host team mode

- Studio desktop clients connect to a self-hosted Core.
- PostgreSQL, Redis, and vector storage run via Docker Compose.
- Shared Vault memory and Guard policies are available to the team.

### Hybrid mode

- Local Studio.
- Self-hosted Core.
- User-managed LLM providers through BYOK.
- Optional remote runners for heavy jobs.

## Repository architecture

Recommended monorepo layout:

```text
mensura/
  apps/
    studio/
    web/
    docs/
  services/
    core/
    vault/
    guard/
    hub/
    voice/
  packages/
    ui/
    sdk/
    mcp/
    shared-types/
    prompts/
  infra/
    docker/
    k8s/
    terraform/
  examples/
  scripts/
  docs/
```

## Data model overview

Core entities:
- User
- Workspace
- Project
- Repository
- Branch
- Task
- Run
- Agent
- PromptVersion
- Diff
- CheckResult
- Policy
- MemoryItem
- Embedding
- Plugin
- Connector
- AuditEvent

## API surface

### Internal service boundaries

- Core API: tasks, runs, agents, approvals.
- Vault API: indexing, search, memory recall, graph queries.
- Guard API: checks, policies, approvals, risk scoring.
- Hub API: plugin manifests, installation, updates, registry metadata.
- Voice API: transcription and command parsing.

### External developer interfaces

- REST/JSON for administration and automation.
- WebSocket for real-time run status.
- MCP server compatibility for tools/resources/prompts[cite:31].
- Plugin SDK for community modules.

## Feature backlog

### MVP

- Desktop workspace.
- Git repo connection.
- Code editor + terminal.
- Agent chat.
- Single orchestration flow.
- Semantic repo indexing.
- Diff review.
- Lint + test gates.
- BYOK model provider support.
- Docker Compose self-host.

### V1

- Multi-agent Kanban dispatch.
- Graph memory.
- Review agent.
- Security agent.
- Plugin hub.
- Team workspaces.
- Audit logs.
- Protected file policies.

### V2

- Remote runners.
- Scheduled automations.
- Full plugin marketplace.
- Knowledge graph visualizer.
- Enterprise policy packs.
- Multi-repo memory.
- Release automation.

## Product principles

- Open source first.
- Self-host first.
- Human review before critical changes.
- Logs over magic.
- Reproducibility over opaque convenience.
- Modular over monolithic.
- Interoperability over lock-in.

## Licensing recommendation

A strong default license for this project is AGPL-3.0 if the goal is to keep hosted derivatives open as well. Apache 2.0 is a more permissive alternative when ecosystem adoption is the primary goal[cite:58][cite:62][cite:65].

## Governance recommendation

- Public roadmap.
- RFC process for major architectural changes.
- Contributor guide.
- Code of conduct.
- Plugin review policy.
- Security disclosure policy.
- Design system contribution rules.

## Risks

- Scope inflation due to combining IDE, agents, RAG, and governance.
- Complexity in maintaining secure agent execution.
- UX risk if orchestration is powerful but hard to understand.
- Plugin trust and supply-chain security.
- Cost management for users who connect paid model providers.

## Success metrics

- Time from install to first successful run.
- Task completion rate after one agent iteration.
- Percentage of runs passing Guard checks.
- Number of active plugins/connectors.
- Mean time to understand a legacy codebase using Vault.
- Contributor growth and community retention.

## One-sentence positioning

Mensura is an open-source, self-hosted agentic development platform that combines AI speed with engineering control.
