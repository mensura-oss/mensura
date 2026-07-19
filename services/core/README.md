# Mensura Core

Mensura Core is the HTTP boundary for tasks and future agent execution. The current service implements the first versioned resource contracts, process-local resource storage, read-only local Git inspection, deterministic Vault file inventory/retrieval, immutable context-pack assembly, and a manually triggered Ruff/pytest Guard runner. It does not call models, edit repositories, generate embeddings, return patch content, implement a full policy engine, or persist data across restarts.

## Requirements

- Python 3.12 or newer.
- Git available on `PATH` for GitPython-backed local inspection.

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
.venv/bin/python -m uvicorn mensura_core.main:app --reload
```

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
| `GET` | `/api/v1/workspaces/{workspace_id}/guard/runs/latest` | Returns the latest completed in-memory Guard result |
| `POST` | `/api/v1/workspaces/{workspace_id}/vault/inventory` | Builds/replaces a deterministic inventory and returns `201` |
| `GET` | `/api/v1/workspaces/{workspace_id}/vault/inventory` | Returns the latest in-memory inventory summary |
| `GET` | `/api/v1/workspaces/{workspace_id}/vault/files` | Returns sorted file metadata with optional filters |
| `GET` | `/api/v1/workspaces/{workspace_id}/vault/files/content?path=...` | Returns one bounded UTF-8 preview |
| `POST` | `/api/v1/workspaces/{workspace_id}/context-packs` | Creates or reopens a deterministic immutable pack and returns `201` |
| `GET` | `/api/v1/workspaces/{workspace_id}/context-packs` | Lists in-memory immutable pack summaries |
| `GET` | `/api/v1/workspaces/{workspace_id}/context-packs/{context_pack_id}` | Returns the exact immutable manifest |
| `GET` | `/api/v1/tasks/{task_id}` | Returns one task |
| `POST` | `/api/v1/tasks` | Creates a ready task in an existing workspace |
| `GET` | `/api/v1/runs/{run_id}` | Returns one run |
| `POST` | `/api/v1/tasks/{task_id}/runs` | Creates a queued placeholder run |

`POST /api/v1/tasks/{task_id}/runs` only records a queued run. No worker consumes it yet. SSE events are intentionally deferred until run execution has real events to expose.

## Read-only repository inspection

`Workspace.rootPath` is the repository candidate. For this MVP it must point directly to a committed, non-bare Git worktree root. The repository endpoint returns:

- branch name, or `null` for detached HEAD;
- clean/dirty state;
- unique staged, unstaged, untracked, and total changed-path counts;
- deterministic metadata entries containing only `path`, `changeType`, `staged`, and optional `oldPath`.

The response model has no patch, hunk, blob, line, file-content, command, remote, or credential field. Production code performs no `add`, `commit`, `checkout`, `reset`, `push`, `pull`, `stash`, branch, or other Git mutation.

## Vault v1 inventory and retrieval

Vault inventory is manual, synchronous, deterministic, and read-only. A successful build creates a new immutable snapshot ID/time and replaces the latest process-local snapshot for that workspace. Entries are sorted case-insensitively by relative POSIX path with an exact-path tie-breaker.

Traversal never follows symlinks. It prunes these directory names case-insensitively: `.git`, `node_modules`, `.pnpm-store`, `.venv`, `venv`, `.cache`, `dist`, `build`, `coverage`, `.next`, `target`, `out`, `output`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and `.turbo`. It also prunes the specific generated path suffix `src-tauri/gen` without excluding every directory named `gen`. Sensitive environment/credential/key names, common OS metadata, compiled/archive artifacts, files over 5 MiB, symlinks, non-regular nodes, and unreadable entries are excluded. Each pruned directory or excluded filesystem entry increments `excludedEntryCount` once; descendants of a pruned directory are not enumerated.

Remaining files are classified conservatively from known binary suffixes plus an 8 KiB sample: NUL bytes, invalid UTF-8, or a high control-character ratio produce `binary`; otherwise the item is `text`. A small fixed extension/name table provides language labels. Classification is not content parsing and is not guaranteed MIME detection.

`GET .../vault/files` accepts optional `query` (case-insensitive path/name substring), `extension` (case-insensitive exact extension, with or without its leading dot), and `limit` (1–500, default 200). `total` is the filtered total before the limit and `returned` is the response item count.

Preview accepts only a canonical relative path already present in the latest inventory. Core rejects absolute/backslash/parent/dot-normalized paths, revalidates every component against symlinks and root containment, and rechecks current file/size/binary state. Only strict UTF-8 text is returned, capped at 16 KiB with `previewBytes`, `totalBytes`, and `truncated`. No endpoint writes repository files. Fixed filtering does not interpret `.gitignore`, prove that content is secret-free, or provide embeddings, chunks, syntax trees, semantic scores, graph relations, watchers, or durable history.

## Immutable context packs

A context pack is a read-only manifest over an explicit set of paths from one concrete latest Vault inventory. POST accepts `{ "paths": [...] }`; paths must be unique canonical relative POSIX paths already included in that inventory. Core sorts them deterministically, rechecks root containment, symlinks, regular-file state, current size, and Vault exclusions, then hashes every complete allowed file with SHA-256.

Text entries capture at most 16 KiB of strict UTF-8 and report preview/total bytes plus truncation. Binary entries are allowed as metadata-only evidence with a full content digest and no preview text. One pack may select at most 50 files and capture at most 256 KiB of aggregate text preview; exceeding either limit rejects the complete request with `413`.

The manifest pins schema version, workspace and inventory ids, explicit limits, aggregate summary, ordered file metadata, per-file content digests, capture modes, and bounded preview text. Compact canonical UTF-8 JSON with sorted object keys is SHA-256 hashed; `sha256:<hex>` becomes both the pack id and digest. Creation time is intentionally absent. Repeating the same unchanged selection against the same inventory returns the exact stored manifest with `created: false`. There is no update or delete endpoint.

Context packs are not yet attached to tasks/runs and are not prompt or provider payloads. They remain process-local review artifacts until durable execution history is introduced.

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
- `urn:mensura:problem:vault-file-not-found` (`404`).

Context packs additionally use:

- `urn:mensura:problem:context-pack-invalid-selection` (`422`);
- `urn:mensura:problem:context-pack-too-large` (`413`);
- `urn:mensura:problem:context-pack-file-changed` (`409`);
- `urn:mensura:problem:context-pack-not-found` (`404`).

They also reuse Vault inventory/path/exclusion problems when those conditions are identical.

Problem URNs are stable machine identifiers. They can be replaced by resolvable HTTPS documentation only as a versioned compatibility decision.

## Storage boundary

Resource routers depend on `CoreService`; Guard routes depend on `GuardService`; Vault routes depend on `VaultService`; context-pack routes depend on `ContextPackService`. Services use replaceable storage/config/runner/Git/filesystem protocols. `InMemoryCoreRepository` stores workspaces/tasks/runs, `InMemoryGuardRunRepository` stores only the latest completed Guard result, `InMemoryVaultInventoryRepository` stores only the latest inventory/items, `InMemoryContextPackRepository` stores immutable manifests by workspace/digest, and the Git/filesystem adapters provide read-only live inspection. All in-memory resources disappear whenever Core stops. External filesystem changes can make any live read best-effort; preview and context capture therefore revalidate selected paths after inventory.
