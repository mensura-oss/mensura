# Mensura Core

Mensura Core is the HTTP boundary for tasks and controlled agent execution. The current service implements versioned resource contracts, durable SQLite-backed persistence, read-only local Git inspection, deterministic Vault inventory/retrieval plus a durable Vault index with local semantic search (a real local Ollama embedding model when available, honest offline lexical-vector fallback otherwise) and heuristic architecture summaries, immutable context-pack assembly, a manual Ruff/pytest Guard runner, the credential-free deterministic provider, one optional OpenAI BYOK adapter with bounded structured results, separately persisted write-isolated change-proposal review, isolated sandbox verification of approved proposals in temporary Git worktrees, an explicit digest-checked apply-to-live step, bounded digest-guarded undo execution serialized with apply through a unified per-workspace write reservation, safe local backup and restore, a durable SQLite-backed background job queue with an in-process worker, live Server-Sent Event (SSE) status updates, and a once-per-process startup maintenance pass that sweeps orphaned verification sandboxes and prunes backups and terminal jobs under a conservative retention policy. It never commits, stages, pushes, or checks out.

## Requirements

- Python 3.12 or newer.
- Git available on `PATH` for GitPython-backed local inspection.
- An operating-system credential backend supported by Python `keyring` to configure optional OpenAI BYOK. Deterministic execution does not require it.

## Local setup

From `services/core`:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Run the quality checks:

```sh
.venv/bin/python -m ruff check src tests
.venv/bin/python -m pytest
```

Start the API:

```sh
.venv/bin/python -m uvicorn mensura_core.main:create_sql_app --factory --reload
```

`create_sql_app` is the durable entry point: it applies Alembic migrations, uses the SQLite-backed repositories (`~/.mensura/core.db`, overridable via `MENSURA_DATABASE_URL`), and starts the in-process background job worker. The bare `mensura_core.main:app` target is an ephemeral in-memory variant for quick checks only and does not persist across restarts. The `mensura-core` console script runs the same durable app without `--reload`.

OpenAPI JSON is available at `http://127.0.0.1:8000/openapi.json` and Swagger UI at `http://127.0.0.1:8000/docs`.

## HTTP v1 contract

JSON property names use camelCase. Resource identifiers are UUIDs and timestamps are UTC ISO 8601 values.

| Method | Path | Result |
|---|---|---|
| `GET` | `/health` | Service identity and liveness |
| `GET` | `/api/v1/workspaces` | `{ "items": [...], "total": number }` |
| `POST` | `/api/v1/workspaces` | Creates a workspace and returns `201` |
| `GET` | `/api/v1/workspaces/{workspace_id}/repository` | Read-only branch/status/path metadata for the workspace root |
| `POST` | `/api/v1/workspaces/{workspace_id}/guard/runs` | Runs configured lint/test checks synchronously and returns `201` |
| `GET` | `/api/v1/workspaces/{workspace_id}/guard/runs/latest` | Returns the latest completed Guard result |
| `POST` | `/api/v1/workspaces/{workspace_id}/vault/inventory` | Builds/replaces a deterministic inventory and returns `201` |
| `GET` | `/api/v1/workspaces/{workspace_id}/vault/inventory` | Returns the latest inventory summary |
| `GET` | `/api/v1/workspaces/{workspace_id}/vault/files` | Returns sorted file metadata with optional filters |
| `GET` | `/api/v1/workspaces/{workspace_id}/vault/files/content?path=...` | Returns one bounded UTF-8 preview |
| `POST` | `/api/v1/vault/index` | Indexes a workspace into memory items + chunks and returns `201` |
| `GET` | `/api/v1/vault/indexes/{workspace_id}` | Returns the latest Vault index status and summary |
| `POST` | `/api/v1/vault/search` | Returns relevance-ranked chunk hits for a query |
| `GET` | `/api/v1/vault/memory/{memory_id}` | Returns one memory item and its chunks |
| `POST` | `/api/v1/vault/summarize` | Returns a heuristic architecture summary from indexed material |
| `POST` | `/api/v1/workspaces/{workspace_id}/context-packs` | Creates or reopens a deterministic immutable pack and returns `201` |
| `GET` | `/api/v1/workspaces/{workspace_id}/context-packs` | Lists immutable pack summaries |
| `GET` | `/api/v1/workspaces/{workspace_id}/context-packs/{context_pack_id}` | Returns the exact immutable manifest |
| `GET` | `/api/v1/workspaces/{workspace_id}/tasks` | Lists the workspace's tasks (oldest first), each with its latest run's compact status |
| `GET` | `/api/v1/tasks/{task_id}` | Returns one task |
| `POST` | `/api/v1/tasks` | Creates a ready task in an existing workspace |
| `GET` | `/api/v1/runs/{run_id}` | Returns one run |
| `POST` | `/api/v1/runs/{run_id}/execute` | Manually executes one queued run and returns its terminal record |
| `POST` | `/api/v1/tasks/{task_id}/runs` | Creates a queued run bound to an immutable context pack |
| `GET` | `/api/v1/providers` | Lists deterministic/OpenAI availability with redacted local configuration state |
| `PUT` | `/api/v1/providers/openai/config` | Saves a write-only API key plus non-secret model setting locally |
| `POST` | `/api/v1/runs/{run_id}/change-proposals` | Creates/reopens one bounded proposal from a successful run |
| `GET` | `/api/v1/change-proposals/{proposal_id}` | Returns one proposal artifact |
| `GET` | `/api/v1/workspaces/{workspace_id}/change-proposals` | Lists proposal artifacts for a workspace |
| `POST` | `/api/v1/change-proposals/{proposal_id}/approve` | Records approval without applying changes |
| `POST` | `/api/v1/change-proposals/{proposal_id}/reject` | Records rejection without applying changes |
| `POST` | `/api/v1/change-proposals/{proposal_id}/verify` | Verifies an approved proposal in a temporary isolated Git worktree and returns `201` |
| `GET` | `/api/v1/change-proposals/{proposal_id}/verifications` | Lists verification artifacts for a proposal |
| `GET` | `/api/v1/verifications/{verification_id}` | Returns one verification artifact |
| `POST` | `/api/v1/change-proposals/{proposal_id}/apply` | Applies an approved, verified proposal to the live working tree (`{ verificationId }`) and returns `201` |
| `GET` | `/api/v1/applications/{application_id}` | Returns one application artifact |
| `GET` | `/api/v1/workspaces/{workspace_id}/applications` | Lists application artifacts for a workspace |

`GET /api/v1/workspaces/{workspace_id}/tasks` returns `{ "items": [...], "total": number }` — the workspace's tasks oldest-first, each a `TaskSummary` (the full `Task` plus a compact `latestRun`). `latestRun` is the task's most recent run reduced to `{ id, status, createdAt, updatedAt }` (`status` ∈ `queued | running | succeeded | failed`), or `null` when the task has never run. It reuses the existing `Task`/`Run` models and adds no run detail beyond that compact status; unknown workspaces return the standard `404` Problem Details. This read-only listing backs the Studio Workspace task board.

`POST /api/v1/tasks/{task_id}/runs` requires this strict body:

```json
{
  "contextPackId": "sha256:<64 lowercase hexadecimal characters>"
}
```

Core resolves the task first, requires the exact immutable pack to exist, and rejects a pack owned by another workspace. The stored/read run includes `contextPackId` plus a compact `contextPack` reference with workspace/inventory/schema identities and aggregate file/byte evidence. Creation records a queued run only; execution remains a separate explicit action.

This endpoint is also the launch path behind the Studio Workspace task board's **Start run** action. Two properties it deliberately keeps make that a thin client concern: creation is **not gated on task status** (Core accepts a run for a task in any status as long as the pack resolves — the board's `draft`/`ready` eligibility is a client-side affordance, not a server rule), and it **does not mutate `task.status`** (only a new queued `Run` is persisted; the task keeps its status and simply gains a latest run, which is what the board's `latestRun` badge reflects). A stale/mismatched pack still returns the usual `context-pack-not-found` (404) / `context-pack-workspace-mismatch` (409) Problem Details, which the board renders inline.

## Manual run execution

`POST /api/v1/runs/{run_id}/execute` requires an explicit provider selection:

```json
{
  "providerId": "mensura.builtin"
}
```

The other supported value is `openai`, which must be configured first. The request cannot supply replacement context, a prompt, credential, model, or repository path. Core reloads the stored run and task, retrieves the exact bound immutable manifest, and rechecks direct pack identity, task/workspace ownership, inventory/schema identity, and stored aggregate evidence before invoking the selected adapter.

The implemented state machine is exactly `queued -> running -> succeeded | failed`. An atomic expected-status repository update claims a queued run before provider work, so overlapping requests cannot both execute it. `startedAt` is persisted on the running transition; `finishedAt`, bounded duration, and either a validated result or safe failure are persisted on the terminal transition. Any later execute request is a `409` conflict. There is no cancellation or retry transition in this slice.

`ProviderRegistry` resolves selection before Core claims the queued run. `ProviderAdapter` then isolates immutable adapter identity and a typed execution request/result. The default `DeterministicReviewProvider` is credential-free and receives only the stored Task plus the complete bounded `ContextPackManifest`; it receives no `Workspace`, `rootPath`, Git/filesystem/subprocess capability, credential, or write method. It deterministically returns schema-v2 task intent, context aggregates/languages, bounded warnings/review steps, and an explicit empty-change proposal draft rather than fabricating code.

The optional `OpenAIReviewProvider` calls the Responses API with `store: false`, no tools, input truncation disabled, a 1,200-token output cap, and strict JSON Schema. The code-controlled `review.v2` mapping serializes only the persisted Task and exact immutable manifest, including already bounded captured previews. It adds a compact proposal draft with summary, rationale, and at most 16 create/modify/delete text suggestions; an empty list is valid. Core parses and locally validates the model payload, then attaches context counts/digests derived from the manifest rather than trusting model claims. It does not read the repository during execution or expose prompts, raw upstream responses, or credentials in the run result. `review.v1` remains defined with its original no-file-modification meaning.

Provider identity is visible as `providerId`, `providerKind`, `adapterId`, `adapterVersion`, nullable `model`, and `promptVersion`. Provider and validation failures persist a failed run with a closed safe code/summary before returning RFC 9457 Problem Details; exception, upstream body, credential, and schema internals are not exposed. Unsupported or unconfigured selection occurs before claim and leaves the run queued. A selected OpenAI failure never silently changes to deterministic. The `POST …/execute` action itself is synchronous through FastAPI's worker-thread handling and has no run-level streaming or retry. Durable background jobs, live SSE status updates, and explicit single-retry of failed jobs exist as separate features (documented below); additional provider vendors/prompts and multi-agent orchestration remain deferred.

## Write-isolated change proposals

`POST /api/v1/runs/{run_id}/change-proposals` accepts no body. The run must already be `succeeded` with a schema-v2 result. Core uses the proposal draft stored in that terminal result and rechecks the exact task/workspace/context-pack lineage before creating an independent `ChangeProposal` schema-v1 artifact. It does not call a provider again and `ChangeProposalService` has no workspace root, Git, filesystem, subprocess, tool, or write dependency.

One idempotent proposal is stored per source run. The response is `{ "proposal": {...}, "created": boolean }` and includes `Location`; a repeated request returns the exact artifact with `created: false`. Proposal identity is a UUID. The artifact records source run/task/workspace, exact context-pack digest, provider/prompt lineage, created/reviewed timestamps, summary/rationale, and deterministically path-sorted file changes.

File change types are closed to `create`, `modify`, and `delete`. Paths must be normalized relative POSIX paths. Modify/delete paths must exist in the immutable manifest; create paths must not. Text bodies are refused for captured binary files and deletes. Core derives `beforeDigest` from the immutable entry and `afterDigest` from the complete proposed UTF-8 text—never from live repository state or a provider-supplied digest.

At most 16 changes are accepted. Aggregate source text is capped at 128 KiB; larger drafts are rejected with `413`. Stored content is UTF-8-safe truncated to 8 KiB/file and 32 KiB/proposal, with `proposedTextBytes`, `originalTextBytes`, and `truncated` fields. The after digest still represents the complete pre-truncation suggestion. There is no raw patch/hunk field and no binary body.

Review state belongs only to the proposal. The complete lifecycle is `proposed -> approved | rejected`; expected-state repository replacement makes the first decision terminal, and a repeated/conflicting decision returns `409`. Approve/reject does not update the run, execute Guard, apply content, invoke Git, or write repository files. Approval only makes the separate isolated verification action eligible.

## Isolated proposal verification

`POST /api/v1/change-proposals/{proposal_id}/verify` accepts no body and is allowed only for `approved` proposals whose stored file text is complete (untruncated). The workspace root must be a committed, non-bare Git repository. Core creates a detached temporary worktree of the current `HEAD` commit under a fresh `mensura-verification-*` system temp directory outside the repository, materializes the proposal's create/modify/delete changes only inside that worktree, runs the workspace's configured Guard lint/test checks against the worktree contents, and then removes the worktree (`git worktree remove --force`, temp-dir deletion, `worktree prune`). Sandboxes are never persisted; only the resulting artifact is.

Verification never writes the live branch, working tree, index, or repository files, and it performs no commit, push, or stage anywhere—including inside the sandbox. Materialization refuses symlinked path components, requires create targets to be absent, and requires modify/delete targets to match the captured `beforeDigest`; any refusal becomes an unapplied file result rather than a write. If any file cannot be applied, Guard is skipped and the outcome is `materialization_failed`.

Each verification is a separate immutable `ProposalVerification` schema-v1 artifact with `passed | failed` status, a closed `sandbox_verified | guard_failed | materialization_failed` outcome, proposal/run/task/workspace/context lineage, sandbox metadata (`git_worktree` kind, verified commit, cleanup flag—no temporary paths), per-file results (`path`, change type, before/after/sandbox digests, `appliedInSandbox`, closed reason), safe diff aggregates, and a compact Guard result whose per-check output is bounded to a 2,000-character excerpt. Repeated verification creates additional artifacts; one verification runs per workspace at a time. A passing verification is the precondition for the separate explicit apply-to-live action.

## Explicit apply to live working tree

`POST /api/v1/change-proposals/{proposal_id}/apply` accepts `{ "verificationId": "..." }` and is the only flow that writes the user's live working tree. It is eligible only when the proposal is `approved`, its stored text is complete, it has at least one file change, the referenced verification belongs to the proposal and is `passed`, no application already exists for the proposal (single-apply), the workspace is a usable non-bare Git repository, and the committed Guard configuration loads. All of these are checked before any write; a failure returns an RFC 9457 problem and nothing is written.

Application is digest-checked and all-or-nothing. Phase one resolves every safe live path (refusing absolute paths, `..` components, and symlinked parents) and compares each live file's current digest against the proposal's captured `beforeDigest` (create targets must be absent); any drift or unsafe path refuses the whole application before writing. Phase two stages every create/modify body to a same-directory temporary file with `flush`+`fsync`, then commits atomic `os.replace`/`os.unlink`. Applied content is the proposal's exact verified text—never re-generated and never a provider call. No `git add`, commit, push, checkout, or reset is ever run; the changes simply appear as ordinary working-tree edits. After a successful write Guard re-runs against the live tree.

Each application is a separate immutable `ApplicationArtifact` schema-v1 record referencing proposal, verification, run, task, workspace, and context lineage, with a closed status of `applied_guard_passed`, `applied_guard_failed`, `applied_guard_unavailable` (written, but Guard could not execute—recorded, never hidden), or `application_failed` (a rare partial write recorded per file). It carries `live_working_tree` target metadata (live HEAD, verification commit, HEAD-moved flag), a compact bounded Guard result, per-file applied results (expected/live-before/after/applied digests plus a closed `applied | write_failed | not_attempted` reason), a summary, and undo metadata (per-file prior existence/digest/bounded prior text with a truncation flag and applied digest). Undo metadata is consumed by the separate digest-guarded undo flow (documented below). An artifact exists only when the live tree was written.

## Workspace write coordination

Apply and undo are the only operations that write a workspace's live working tree. A single process-wide reservation (`WorkspaceWriteReservation`, exposed on `app.state.workspace_write_reservation`) guarantees that at most one live-tree writer per workspace runs at a time — whether it originates from a synchronous HTTP request or the background job worker (which invokes the same service methods, so it cannot bypass the reservation). The claim is keyed by `workspaceId`, made atomically within the process, released in a `finally` block, and never queued: a second writer for a reserved workspace is refused immediately with `urn:mensura:problem:workspace-write-in-progress` (`409`) and nothing is written. Under a background job this refusal maps to an honest `failed` job carrying a bounded `lastError`, with no partial artifact created. Diagnostics on each holder record the holder kind (`application_apply` / `application_undo`), the target entity, and `acquiredAt`.

Verification, backup, and standalone Guard deliberately do **not** take this reservation. Verification materializes its sandbox from the committed `HEAD` and writes only inside a temporary worktree, so concurrent live-tree writes (which never commit, move `HEAD`, or touch `.git`) cannot affect it; it keeps its own per-workspace verification serialization. Backup snapshots the SQLite database, not the workspace tree. Standalone Guard reads the live tree and keeps its own guard-run reservation. The internal Guard sub-run inside apply/undo already executes under the held write reservation, so post-write Guard sees a stable tree.

## Local BYOK configuration

`PUT /api/v1/providers/openai/config` accepts `{ "apiKey": "...", "model": "..." }`. The key is write-only: Core stores it through Python `keyring` under service `dev.mensura.studio`, account `openai-api-key`, and no GET or response schema contains it. The model is the only provider value written to `providers.json` in the platform user-config directory (`~/Library/Application Support/Mensura` on macOS), with `MENSURA_CONFIG_DIR` available for an explicit local override. This settings file is mode `0600` where supported and contains no secret.

Saving configuration validates local shape but does not spend a model request. Rejected credentials are reported on the first selected execution. OpenAI use requires outbound access to `https://api.openai.com`; deterministic execution remains fully functional without network, config, or credentials.

## Read-only repository inspection

`Workspace.rootPath` is the repository candidate. For this MVP it must point directly to a committed, non-bare Git worktree root. The repository endpoint returns:

- branch name, or `null` for detached HEAD;
- clean/dirty state;
- unique staged, unstaged, untracked, and total changed-path counts;
- deterministic metadata entries containing only `path`, `changeType`, `staged`, and optional `oldPath`.

The response model has no patch, hunk, blob, line, file-content, command, remote, or credential field. Production code performs no `add`, `commit`, `checkout`, `reset`, `push`, `pull`, `stash`, branch, or other Git mutation.

## Vault v1 inventory and retrieval

Vault inventory is manual, synchronous, deterministic, and read-only. A successful build creates a new immutable snapshot ID/time and replaces the latest stored snapshot for that workspace. Entries are sorted case-insensitively by relative POSIX path with an exact-path tie-breaker.

Traversal never follows symlinks. It prunes these directory names case-insensitively: `.git`, `node_modules`, `.pnpm-store`, `.venv`, `venv`, `.cache`, `dist`, `build`, `coverage`, `.next`, `target`, `out`, `output`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and `.turbo`. It also prunes the specific generated path suffix `src-tauri/gen` without excluding every directory named `gen`. Sensitive environment/credential/key names, common OS metadata, compiled/archive artifacts, files over 5 MiB, symlinks, non-regular nodes, and unreadable entries are excluded. Each pruned directory or excluded filesystem entry increments `excludedEntryCount` once; descendants of a pruned directory are not enumerated.

Remaining files are classified conservatively from known binary suffixes plus an 8 KiB sample: NUL bytes, invalid UTF-8, or a high control-character ratio produce `binary`; otherwise the item is `text`. A small fixed extension/name table provides language labels. Classification is not content parsing and is not guaranteed MIME detection.

`GET .../vault/files` accepts optional `query` (case-insensitive path/name substring), `extension` (case-insensitive exact extension, with or without its leading dot), and `limit` (1–500, default 200). `total` is the filtered total before the limit and `returned` is the response item count.

Preview accepts only a canonical relative path already present in the latest inventory. Core rejects absolute/backslash/parent/dot-normalized paths, revalidates every component against symlinks and root containment, and rechecks current file/size/binary state. Only strict UTF-8 text is returned, capped at 16 KiB with `previewBytes`, `totalBytes`, and `truncated`. No endpoint writes repository files. Fixed filtering does not interpret `.gitignore` or prove that content is secret-free. Embeddings, chunks, and semantic scores are provided by the separate Vault index below; syntax trees, graph relations, watchers, and per-file durable history are not.

These two read-only endpoints also back the Studio **Workspace** panel's repository tree and read-only Monaco editor: the tree is folded client-side from `GET .../vault/files` and the editor shows the same bounded `GET .../vault/files/content` preview. That surface added **no new Core endpoints** — it deliberately reuses the inventory's existing safety posture (ignore rules, symlink/root containment, size and binary caps) rather than introducing arbitrary filesystem traversal.

## Vault index, semantic retrieval, and architecture summary

The Vault index is an additive layer over the read-only inventory that makes a workspace's code and docs searchable and summarizable. It is manual and synchronous: `POST /api/v1/vault/index` walks the workspace, chunks and embeds supported files, and replaces the latest index for that workspace (one index per workspace; re-indexing cascade-deletes the prior memory items and chunks). Indexing writes only Core's SQLite database — never the repository.

**Ingestion and exclusions.** The walk reuses the inventory's safety posture and exclusion rules (never follows symlinks or leaves the workspace root; prunes `.git`, `node_modules`, `.venv`, `dist`, `build`, and the rest of the inventory list; excludes secrets/keys, compiled/archive artifacts, and files over the inventory's 5 MiB cap). Among the remaining files it indexes three source types: **code** (Python, TypeScript/JavaScript, Rust, Go, C/C++, Java, Kotlin, Swift, Shell, SQL, CSS/SCSS, HTML, XML, Dockerfile, Makefile), **doc** (`.md`/`.markdown`/`.mdx`/`.rst`/`.txt`/`.adoc`), and **config** (`.json`/`.yaml`/`.yml`/`.toml`/`.ini`/`.cfg`/`.conf`/`.properties`). A file that is unreadable, binary (NUL byte / invalid UTF-8), larger than the explicit 1 MB indexing cap, of an unsupported type, or empty is skipped with a recorded reason (`read_error`, `binary`, `too_large`, `unsupported_type`, `empty`); the index summary carries counts by reason plus a bounded sample.

**Chunking.** Docs are split on markdown headings and blank-line paragraph boundaries; code and config are split into bounded fixed line windows (≤80 lines and ≤~1500 chars). Every chunk retains its 1-based inclusive `startLine`/`endLine`, `charCount`, and a SHA-256 `digest`, and traces back to its memory item (`path`, `sourceType`, `language`, content `digest`, `sizeBytes`).

**Embedding backends (local-first, honest).** Chunks and queries are embedded through a pluggable `Embedder` protocol (`vault_embedding.py`) with two interchangeable **local** backends. There is no cloud embedding service.

- **`OllamaEmbedder` (real semantic).** Calls a **local Ollama daemon** (`http://localhost:11434/api/embed`, over the already-present `httpx`) to embed text with a real neural model (default `nomic-embed-text`, 768-dim). Vectors are L2-normalized. Setup: install Ollama (`brew install ollama` / [ollama.com](https://ollama.com)), start it (`ollama serve`), and pull the model (`ollama pull nomic-embed-text`).
- **`HashingEmbedder` (offline lexical fallback).** A deterministic, dependency-free term-frequency hashing vectorizer: unigrams + bigrams hashed with `blake2b` into a fixed 16,384-bucket vector, L2-normalized. Fully offline and reproducible across restarts, but lexical — it cannot bridge a vocabulary gap (a query and a relevant chunk that share meaning but no literal tokens). The bucket space is sized generously so the sparse inverted index below is *selective* (few hash collisions); it costs no extra storage because a chunk's stored vector holds one entry per distinct token bucket regardless of the space size.

Both return the same L2-normalized sparse-dict shape (a dense embedding is a fully-populated dict keyed by index), so the schema, the persisted `vault_chunks.embedding` JSON column, and cosine ranking are **unchanged** by the switch to real embeddings (no migration).

**Backend selection.** The production app (`create_sql_app`) picks a backend from environment configuration once at startup and records it on each index it builds:

| Variable | Default | Meaning |
|---|---|---|
| `MENSURA_VAULT_EMBEDDER` | `auto` | `auto` = use Ollama when reachable, else lexical; `ollama` = require Ollama (still falls back to lexical with a logged warning if it is down); `hashing` = force the offline lexical embedder (no probe/network) |
| `MENSURA_OLLAMA_URL` | `http://localhost:11434` | Ollama daemon base URL |
| `MENSURA_OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |

The ephemeral in-memory `:app` target and the test suite always use the offline lexical embedder (they never touch a daemon). Selection is honest: when Ollama is unavailable the factory logs the reason and the mode degrades to lexical — the product never pretends semantic embeddings are active.

**Retrieval strategy.** `POST /api/v1/vault/search` embeds the query with the same backend and ranks chunks by **embedding cosine similarity (primary)**, keeping a small exact-substring boost as a **secondary** re-rank only, optionally filtered by `sourceType` (`limit` 1–50, default 10). The response `strategy` reports the mode honestly: `semantic-cosine:ollama/<model>` for real embeddings, `lexical-vector-cosine` for the lexical fallback. The index summary carries an `embedding` object (`backend`, `model`, `dim`, `semantic`) so callers know which backend produced the vectors. `GET /api/v1/vault/memory/{memory_id}` returns one memory item and its chunk texts.

**Sub-linear search acceleration (sparse inverted index).** Search no longer depends solely on an O(N) linear cosine scan of every chunk. For **lexical (sparse) indexes** — the default local-first mode when Ollama is absent — indexing also persists a **sparse inverted index** (`vault_chunk_postings`: one row per chunk × non-zero embedding bucket, indexed on `(workspace_id, bucket)`), built in the same transaction as the chunks (atomic — no partially-ready acceleration structure) and fully replaced per workspace on every re-index. At query time the service reads only the posting lists for the query's own buckets to gather a small **candidate set** (the chunks that share ≥1 bucket), then reranks *exactly that set* with the unchanged cosine + substring-boost scorer. This is **exact**, not approximate: for the sparse lexical space a shared bucket implies cosine > 0 and a substring match implies shared buckets, so the candidate set is a superset of every chunk the linear scan would score above zero — results (hits, scores, order, `total`) are identical to the full scan, just computed over far fewer chunks (a real repo sees ~25–50× faster search on 2k–40k-chunk indexes, scaling with the candidate count rather than the index size). The acceleration is invisible to callers — same request/response, same `strategy`. Search falls back to the exact linear scan, explicitly and bounded, whenever the accelerated path does not apply: a **dense/semantic** or **legacy** index (no postings persisted — see the remaining-limit note below), an all-stopword query (no buckets to probe), a query so broad it exceeds the candidate cap (2,000 distinct matches), or a corrupt/unreadable acceleration index (the error is caught, logged, and the linear scan answers correctly).

**Fallback, mismatch, and re-indexing.** If the embedding backend fails **while indexing**, indexing fails clearly with `503 urn:mensura:problem:vault-embedding-backend-unavailable` rather than persisting a half-embedded (mixed-space) index. At **search** time, if the index was built by a *different* backend than the one now configured — e.g. a semantic index queried after the Ollama daemon went down, or an old lexical index queried with Ollama now on — the service never scores across incompatible vector spaces: it degrades to a lexical re-rank over the stored chunk text and reports `strategy: lexical-fallback:reindex-required`. Old lexical indexes remain fully searchable; to *gain* semantic ranking a workspace must be re-indexed with the backend running (the required backend is visible in the index summary's `embedding` metadata).

**Limitations/tradeoffs.** A 768-dim dense vector is a larger JSON blob than a sparse lexical one (more index disk); real embedding adds one local HTTP round-trip per chunk batch at index time (bounded, batched, local); indexing is still manual + full-replace; cross-file embedding batching is per file today. **Search acceleration currently covers only the sparse (lexical) space** — **dense/semantic (Ollama) indexes still use the exact linear scan** because a coordinate inverted index over dense neural vectors is neither selective nor exact; sub-linear *dense* retrieval (a local IVF/clustering or HNSW candidate index over the 768-dim vectors) is the next scale slice. The lexical inverted index stays sub-linear only while queries are selective: an all-stopword or extremely common-token query matches most chunks and correctly falls back to the linear scan.

**Architecture summary.** `POST /api/v1/vault/summarize` derives a concise, deterministic, non-AI summary from the indexed material: file/code/doc/config counts and total bytes, top languages, top-level directory "modules" (file count, bytes, dominant language), technologies detected from marker files (`package.json`→Node.js, `pyproject.toml`/`requirements.txt`→Python, `Cargo.toml`→Rust, `go.mod`→Go, `Dockerfile`→Docker, `tsconfig.json`→TypeScript, `alembic.ini`→Alembic, …), and heuristic entry points (`main.py`, `index.ts`, `main.rs`, …). It is a first orientation, not a guaranteed-complete or AI-generated design document.

These endpoints now have a user-facing **Studio "Vault memory" panel** (index trigger, indexed/not-indexed status and summary counts, ranked search with a `sourceType` filter, and an on-demand architecture summary), which states the lexical-vector and manual-full-replace limits in the UI. Clicking a search hit opens a read-only **file view** in Studio that reuses `GET /api/v1/vault/memory/{memory_id}` (no new endpoint) to reconstruct a line-numbered rendering of the file from its indexed chunks and scroll to / highlight the hit's line range; a stale hit whose memory item was dropped by a re-index surfaces the existing `urn:mensura:problem:vault-memory-not-found` 404 as a bounded message.

Deferred: full graph memory and linked task memory, branch-aware or cross-workspace shared memory, incremental/watched re-indexing, cross-file embedding batching, a sub-linear **dense/semantic** candidate index (IVF/clustering or HNSW over the 768-dim Ollama vectors — the lexical/sparse space is now accelerated by the persisted inverted index above, but dense search is still a linear scan), automatic re-index when the embedding backend changes, and in-editor navigation to a file/line from a search hit (Studio currently opens the indexed chunk with its line range). Real local neural embeddings now ship (Ollama), replacing the lexical-only baseline; a fully in-process embedding model (no daemon) remains deferred to avoid heavy native dependencies.

## Immutable context packs

A context pack is a read-only manifest over an explicit set of paths from one concrete latest Vault inventory. POST accepts `{ "paths": [...] }`; paths must be unique canonical relative POSIX paths already included in that inventory. Core sorts them deterministically, rechecks root containment, symlinks, regular-file state, current size, and Vault exclusions, then hashes every complete allowed file with SHA-256.

Text entries capture at most 16 KiB of strict UTF-8 and report preview/total bytes plus truncation. Binary entries are allowed as metadata-only evidence with a full content digest and no preview text. One pack may select at most 50 files and capture at most 256 KiB of aggregate text preview; exceeding either limit rejects the complete request with `413`.

The manifest pins schema version, workspace and inventory ids, explicit limits, aggregate summary, ordered file metadata, per-file content digests, capture modes, and bounded preview text. Compact canonical UTF-8 JSON with sorted object keys is SHA-256 hashed; `sha256:<hex>` becomes both the pack id and digest. Creation time is intentionally absent. Repeating the same unchanged selection against the same inventory returns the exact stored manifest with `created: false`. There is no update or delete endpoint.

Context packs can be selected as the required immutable evidence binding for a queued run. Runs reference the pack by digest and expose only a compact summary; they do not copy mutable path selections or turn the manifest into a prompt/provider payload. Packs and runs are persisted durably in SQLite.

## Guard v1 configuration and execution

Guard reads exactly `.mensura/guard.json` from the workspace root. The checked-in Mensura configuration is the reference shape:

```json
{
  "version": 1,
  "timeoutSeconds": 120,
  "checks": {
    "lint": {
      "command": ["services/core/.venv/bin/python", "-m", "ruff", "check", "services/core/src"],
      "blocking": true
    },
    "test": {
      "command": ["services/core/.venv/bin/python", "-m", "pytest", "services/core/tests", "-q"],
      "blocking": true
    }
  }
}
```

Both checks are required. `timeoutSeconds` applies independently to each and must be between 1 and 300. Guard v1 deliberately accepts only Ruff for `lint` and pytest for `test`, either directly or as `python -m ruff|pytest`. Commands are argv arrays; Core never invokes a shell or discovers commands from project files.

Execution is manual and synchronous. Core fixes cwd to the workspace, uses a reduced environment, disables pytest plugin autoload, prevents concurrent Guard runs for the same workspace, terminates timed-out process groups where supported, and captures at most 8 KiB from each stdout/stderr stream while continuing to drain excess output. Non-zero exits are normal structured failed checks; timeouts are structured error checks; only configured blocking failures set the overall blocking decision.

The config must be treated as executable project configuration and reviewed before use. Ruff and pytest can read/write project files or execute test/import code; cwd/tool restrictions are not an OS sandbox and do not guarantee filesystem or network isolation.

## Errors

All HTTP errors use RFC 9457 Problem Details and the `application/problem+json` media type:

```json
{
  "type": "urn:mensura:problem:resource-not-found",
  "title": "Resource not found",
  "status": 404,
  "detail": "Task '...' was not found.",
  "instance": "/api/v1/tasks/..."
}
```

Validation responses use `urn:mensura:problem:validation-error` and add an `errors` array. Each item has a human-readable `detail` and a `pointer` identifying the invalid request member.

Repository inspection additionally uses these stable problem types:

- `urn:mensura:problem:repository-path-not-found` (`404`) for a missing or non-directory root;
- `urn:mensura:problem:not-a-git-repository` (`422`) for an existing non-Git root;
- `urn:mensura:problem:unsupported-repository-state` (`409`) for bare, unborn, or otherwise uninspectable Git state.

Guard additionally uses:

- `urn:mensura:problem:guard-configuration-not-found` (`404`);
- `urn:mensura:problem:guard-run-not-found` (`404`) when no completed run exists;
- `urn:mensura:problem:invalid-guard-configuration` (`422`);
- `urn:mensura:problem:unsupported-workspace-state` (`409`);
- `urn:mensura:problem:guard-run-in-progress` (`409`);
- `urn:mensura:problem:guard-execution-failed` (`500`) when a configured process cannot start.

Vault additionally uses:

- `urn:mensura:problem:vault-root-invalid` (`409`);
- `urn:mensura:problem:vault-inventory-not-built` (`404`);
- `urn:mensura:problem:vault-path-invalid` (`422`);
- `urn:mensura:problem:vault-file-excluded` (`403`);
- `urn:mensura:problem:vault-binary-preview-refused` (`415`);
- `urn:mensura:problem:vault-file-not-found` (`404`);
- `urn:mensura:problem:vault-index-not-built` (`404`);
- `urn:mensura:problem:vault-memory-not-found` (`404`);
- `urn:mensura:problem:vault-embedding-backend-unavailable` (`503`) when the configured embedding backend cannot produce vectors during indexing.

Context packs additionally use:

- `urn:mensura:problem:context-pack-invalid-selection` (`422`);
- `urn:mensura:problem:context-pack-too-large` (`413`);
- `urn:mensura:problem:context-pack-file-changed` (`409`);
- `urn:mensura:problem:context-pack-not-found` (`404`).
- `urn:mensura:problem:context-pack-workspace-mismatch` (`409`) when a task and selected pack have different owners.

They also reuse Vault inventory/path/exclusion problems when those conditions are identical.

Run execution additionally uses:

- `urn:mensura:problem:run-invalid-state` (`409`) when a run is not queued;
- `urn:mensura:problem:run-context-pack-missing` (`409`) when the persisted bound pack is no longer retrievable;
- `urn:mensura:problem:run-context-inconsistent` (`409`) when task, workspace, manifest, or stored binding evidence disagrees;
- `urn:mensura:problem:provider-execution-failed` (`502`) when an adapter raises during execution;
- `urn:mensura:problem:unsupported-provider` (`422`);
- `urn:mensura:problem:provider-configuration-missing` (`409`);
- `urn:mensura:problem:provider-configuration-unavailable` (`503`);
- `urn:mensura:problem:provider-credentials-invalid` (`422`);
- `urn:mensura:problem:provider-upstream-failed` (`502`);
- `urn:mensura:problem:structured-result-invalid` (`502`) when adapter output fails the bounded schema.

Change proposals additionally use:

- `urn:mensura:problem:change-proposal-not-found` (`404`);
- `urn:mensura:problem:change-proposal-run-not-eligible` (`409`) for a non-successful run;
- `urn:mensura:problem:change-proposal-output-invalid` (`422`) for unsafe paths, inconsistent lineage, binary text, duplicates, or invalid change semantics;
- `urn:mensura:problem:change-proposal-content-too-large` (`413`) when source text exceeds 128 KiB;
- `urn:mensura:problem:change-proposal-invalid-state` (`409`) after any prior review decision.

Proposal verification additionally uses:

- `urn:mensura:problem:verification-not-found` (`404`);
- `urn:mensura:problem:verification-proposal-not-approved` (`409`) for `proposed` or `rejected` proposals;
- `urn:mensura:problem:verification-content-incomplete` (`422`) when stored proposal text is truncated;
- `urn:mensura:problem:verification-in-progress` (`409`) for a concurrent verification in the same workspace;
- `urn:mensura:problem:verification-sandbox-failed` (`500`) when the temporary worktree cannot be created;

Apply-to-live additionally uses:

- `urn:mensura:problem:application-not-found` (`404`);
- `urn:mensura:problem:application-proposal-not-approved` (`409`);
- `urn:mensura:problem:application-content-incomplete` (`422`) when stored proposal text is truncated;
- `urn:mensura:problem:application-empty-proposal` (`422`) when the proposal has no file changes;
- `urn:mensura:problem:application-verification-not-found` (`404`), `-verification-mismatch` (`409`), and `-verification-not-passed` (`409`);
- `urn:mensura:problem:application-already-exists` (`409`) for a single-apply re-attempt;
- `urn:mensura:problem:workspace-write-in-progress` (`409`) when another live-tree writer (apply or undo) already holds the workspace's write reservation;
- `urn:mensura:problem:application-live-drift` (`409`) when a live file no longer matches the verified basis;
- `urn:mensura:problem:application-unsafe-path` (`422`) when a proposed path escapes the workspace root;
- `urn:mensura:problem:application-write-failed` (`500`) when staging fails before any live file changed;
- the existing repository problems (`repository-path-not-found`, `not-a-git-repository`, `unsupported-repository-state`) and Guard configuration/execution problems for the sandbox's Guard run.

Problem URNs are stable machine identifiers. They can be replaced by resolvable HTTPS documentation only as a versioned compatibility decision.

## Durable background jobs

Long-running operations can run as durable, persisted jobs instead of inline within the request:

| Method | Path | Result |
|---|---|---|
| `POST` | `/api/v1/jobs` | Enqueue a job (`201` + queued `Job` + `Location`) |
| `GET` | `/api/v1/jobs?workspaceId=&status=&jobType=` | List jobs, newest first |
| `GET` | `/api/v1/jobs/{job_id}` | Get one job |

The enqueue body is a discriminated union on `jobType`: `{ "jobType": "proposal_verification", "proposalId": "…" }`, `{ "jobType": "application_apply", "proposalId": "…", "verificationId": "…" }`, `{ "jobType": "application_undo", "applicationId": "…" }`, or `{ "jobType": "backup_create", "label": "…"? }`. Enqueue performs a light existence check on the target (a missing proposal/application returns the usual `404`), resolves the owning `workspaceId`, and persists a `Job` schema-v1 record with `jobType`, `targetEntityType`/`targetEntityId`, optional `workspaceId`, `status` (`queued | running | succeeded | failed`), `attemptCount`, a bounded reference `payload` (identifiers and a label only), `resultEntityType`/`resultEntityId`, a bounded `lastError`, and `createdAt`/`startedAt`/`finishedAt`.

**Existing synchronous endpoints are unchanged.** The job API is purely additive; `…/verify`, `…/apply`, `…/undo`, and `POST /backups` keep their exact `201`+artifact semantics. Enqueue is opt-in durable async.

A single in-process `JobWorker`, started from the FastAPI lifespan in production (`create_sql_app`), drains the queue. Claiming is an atomic compare-and-set (`UPDATE … SET status='running' WHERE id=? AND status='queued'`), so only one worker ever claims a job. The worker invokes the **same** service method the synchronous endpoint calls, so every digest/Guard/path/single-use safety check is preserved—no new provider or Git capability is introduced. Jobs are orchestration only: a job `succeeded` means the operation ran to completion and produced its artifact, while the artifact's own status still records the domain outcome (a `guard_failed` verification or `applied_guard_failed` application still yields a `succeeded` job). Only pre-write refusals that raise a domain error (drift, unsafe path, not-approved, already-applied, ineligible undo) mark the job `failed` with a bounded summary.

**Restart recovery.** Queued jobs persist in SQLite and are picked up by the worker after a restart. At startup, before the worker runs, any job left `running` by an interrupted process is atomically transitioned to `failed` with an honest "interrupted by a Core restart; the operation's outcome is unknown—inspect the target artifact and re-enqueue if needed" summary. This is the safe choice over auto-requeue: it never produces duplicate backups or verification artifacts and never silently re-applies. Automatic retries are deferred (`attemptCount` is recorded for forward-compatibility); restore stays explicit/synchronous and is never queued.

## Server-Sent Events (SSE)

Core exposes a bounded one-way event stream for live status updates:

| Method | Path | Result |
|---|---|---|
| `GET` | `/api/v1/events/stream?workspaceId=` | `text/event-stream` with live events |

### Event envelope

Each event carries a compact `MensuraEvent` payload with `eventId`, `eventType`, `occurredAt`, optional `workspaceId`, `entityType`, `entityId`, `status`, and a `summary` (≤200 chars). No file contents, artifact bodies, diffs, or patches are streamed.

### Supported event types

- `run.status.changed` — emitted when a run transitions to `succeeded` or `failed`
- `verification.created` — emitted when a sandbox verification completes
- `application.created` — emitted when an application to the live tree completes
- `undo.created` — emitted when an undo operation completes or is refused
- `backup.created` — emitted when a database backup completes
- `job.status.changed` — emitted when a background job is enqueued, claimed, or reaches a terminal state

### Reconnection and replay

The stream emits an initial `connected` event with the buffer size. Clients can send a `Last-Event-Id` header to replay missed events from the in-memory buffer (last 100 events). SSE is a notification mechanism only — REST API remains the authoritative source of truth.

### Filtering

Pass `?workspaceId=` to receive only events scoped to that workspace. Without the filter, all events are streamed.

## Startup maintenance: sandbox cleanup and retention

The durable app (`create_sql_app`) runs a once-per-process maintenance pass inside its startup lifespan, **before the job worker starts and before it accepts traffic**. Every step is best-effort: a failure is logged as a warning and never aborts startup. The ephemeral in-memory `:app` target does not run maintenance.

### Verification sandbox sweep

Proposal verification runs inside a temporary Git worktree named `mensura-verification-*` (created under the system temp directory, or `MENSURA_SANDBOX_DIR` when set) that holds exactly one `worktree` child. A crash or hard termination mid-verification can leave the temp directory and its stale `.git/worktrees` metadata behind. Because Core is single-process, no verification can be in flight during the startup sweep, so any directory that still matches the Mensura naming scheme is necessarily orphaned by a previous process.

The sweep is deliberately conservative:

- **When it runs:** once, in the startup lifespan, before the worker and before traffic.
- **What it deletes:** only directories whose name starts with `mensura-verification-` **and** whose layout matches what the factory creates (empty, or containing exactly one `worktree` child); then, for each configured workspace, it runs Git's own `git worktree prune` to drop stale worktree metadata (directories are removed first so the prune sees the missing working tree).
- **What it never deletes:** anything not matching that prefix and structure, symlinks, or a prefixed directory with unexpected contents (those are logged and skipped). It never touches the live repository, and it never edits `.git` internals by hand.
- It logs a summary: sandboxes inspected, removed, skipped, and workspaces whose worktree metadata was pruned.

### Retention (backups and terminal jobs)

Retention is **best-effort local hygiene** to bound the two operational byproducts that otherwise grow without limit over long-term single-user use — database **backups** and **terminal jobs** (succeeded/failed). It is not a replacement for an external backup strategy.

A single policy governs both: an item is **kept** if it is within the newest `keep_at_least`, **or** within the newest `count`, **or** newer than `days`; it is **pruned** only when it fails all three (beyond the count *and* older than the age). A dimension set to `0` is inactive, and **both `0` disables pruning** for that item type.

| Item | Count var (default) | Days var (default) | Never-pruned floor |
|---|---|---|---|
| Backups | `MENSURA_BACKUP_RETENTION_COUNT` (10) | `MENSURA_BACKUP_RETENTION_DAYS` (30) | the newest backup is always kept (`keep_at_least=1`) |
| Terminal jobs | `MENSURA_JOB_RETENTION_COUNT` (200) | `MENSURA_JOB_RETENTION_DAYS` (30) | queued/running jobs are never candidates |

- **What is pruned:** completed/failed backups beyond the policy (both the metadata row and the on-disk file — the file is unlinked *before* the row, and a file-unlink failure skips the row deletion so a surviving row always still refers to its file); and terminal jobs beyond the policy. A terminal job still referenced by another job as its retry parent or root is kept, so pruning never orphans a retry lineage.
- **What is never pruned:** core domain artifacts (tasks, runs, proposals, verifications, applications, undos) and queued/running jobs. Retention only touches backups and terminal jobs.
- **Safety:** the user's only backup is never deleted; a value below `1` for the backup count is treated as `1`; a single failed deletion is logged and skipped, never raised.
- **When it runs:** backup retention runs after every successful backup creation (bounding the backup directory as it grows) and again at startup; terminal-job retention runs at startup. There is no scheduler or cron.

## Storage boundary

Resource routers depend on `CoreService`; provider routes use `ProviderRegistry`; Guard, Vault, context-pack, change-proposal, verification, application, undo, backup, and event routes retain dedicated services. Services use replaceable storage/config/credential/runner/Git/filesystem/provider/sandbox protocols. Workspaces/tasks/runs, Guard results, Vault inventories, Vault indexes (memory items, embedded chunks, and — for lexical indexes — a sparse inverted-index postings table for sub-linear search), context packs, change proposals, verification artifacts, application artifacts, undo artifacts, backups, and background jobs are persisted in SQLite via SQLAlchemy 2.0 + Alembic migrations. Only the non-secret OpenAI model setting and keyring credential follow separate storage paths. Git/filesystem adapters provide read-only live inspection; provider adapters consume only persisted task/context objects; proposal materialization consumes only the persisted successful run plus its exact stored manifest. Isolated verification writes exclusively inside its temporary worktree before removing it. Explicit apply-to-live and undo write the live working tree, and both do so with digest checks and atomic replaces after every precondition passes—still without any Git command—while holding the shared per-workspace write reservation so two live-tree writers can never interleave on the same workspace. External filesystem changes can make inventory/context capture best-effort, but executing a run or creating/reviewing/verifying its proposal does not write the repository.

The durable SQLite path sets `PRAGMA busy_timeout = 5000` alongside `journal_mode = WAL` and `foreign_keys = ON` on every connection, so a brief writer overlap between the single in-process worker and a synchronous request waits up to five seconds rather than failing immediately with `SQLITE_BUSY`. The value is driver-independent and defined in `persistence/database.py`.
