# Mensura Core

Mensura Core is the HTTP boundary for tasks and future agent execution. The current service implements the first versioned resource contracts, process-local resource storage, read-only local Git inspection, and a manually triggered Ruff/pytest Guard runner. It does not call models, edit repositories, return patch content, implement a full policy engine, or persist data across restarts.

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

Problem URNs are stable machine identifiers. They can be replaced by resolvable HTTPS documentation only as a versioned compatibility decision.

## Storage boundary

Resource routers depend on `CoreService`; Guard routes depend on `GuardService`. Services use replaceable storage/config/runner/Git protocols. `InMemoryCoreRepository` stores workspaces/tasks/runs, `InMemoryGuardRunRepository` stores only the latest completed Guard result per workspace, and `GitPythonRepositoryAdapter` provides read-only live inspection. All in-memory resources disappear whenever Core stops. If another process changes Git state during one request, the repository summary is best-effort rather than atomic.
