# Mensura — System Architecture

## High-level architecture

Mensura is a modular system composed of a desktop client, orchestration backend, memory subsystem, governance subsystem, and extension registry. The integration boundary is designed around open standards, especially MCP, which standardizes how AI applications interact with tools, prompts, and resources[cite:31][cite:74].

## Core components

### Studio
- Tauri desktop shell.
- React frontend.
- Monaco editor.
- xterm.js terminals.
- WebSocket client for live run updates.

### Core
- FastAPI service.
- LangGraph orchestration engine[cite:72][cite:79][cite:85].
- Run scheduler.
- Context assembler.
- Provider router.
- Approval manager.

### Vault
- Ingestion pipeline.
- Parser layer.
- Embedding generator.
- Semantic retrieval.
- Optional graph database.

### Guard
- Check runners.
- Policy interpreter.
- Risk scorer.
- Audit logger.

### Hub
- Plugin registry.
- Signature verifier.
- Manifest index.
- Template catalog.

## Suggested service topology

```text
Studio (desktop)
  -> Core API
     -> Run Queue
     -> Agent Executor
     -> Vault API
     -> Guard API
     -> Provider Router
     -> Git Adapter
     -> Docker Runner
```

## Data flow

### Task execution flow

1. Studio sends a task request to Core.
2. Core retrieves project context from Vault.
3. Core builds a run graph.
4. Agent executor calls model providers and tools.
5. File changes are staged in a workspace or branch.
6. Guard runs checks.
7. Results return to Studio with diff, logs, and status.

### Memory ingestion flow

1. Repo/file watcher detects changes.
2. Ingestion parses files and docs.
3. Chunking and embeddings are generated.
4. Indexed items are stored in PostgreSQL and vector storage.
5. Optional graph relationships are updated.

## Security boundaries

- Agents should execute in constrained sandboxes when possible.
- Sensitive file paths should be protected by policy.
- Provider credentials should never be exposed to plugins directly.
- Audit trails should persist every approval, tool use, and high-risk change.

## Recommended stack

| Domain | Choice |
|---|---|
| Desktop | Tauri 2, Rust, React[cite:73][cite:80] |
| API | FastAPI |
| Agent orchestration | LangGraph[cite:72][cite:79][cite:85] |
| Interop | MCP[cite:31] |
| DB | PostgreSQL |
| Queue/cache | Redis |
| Vector search | pgvector or Qdrant |
| Optional graph | Neo4j |
| Observability | OpenTelemetry, Prometheus, Grafana |
| Containers | Docker |

## Scaling path

### Phase 1
Single-user desktop with local services.

### Phase 2
Self-hosted team instance with shared database and vector memory.

### Phase 3
Remote runners, workload isolation, and policy packs for large teams.
