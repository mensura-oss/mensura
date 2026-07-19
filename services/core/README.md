# Mensura Core

Mensura Core is the HTTP boundary for tasks and future agent execution. The current service implements only the first versioned resource contracts and process-local storage. It does not call models, edit repositories, execute Guard checks, or persist data across restarts.

## Requirements

- Python 3.12 or newer.

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
| `GET` | `/api/v1/tasks/{task_id}` | Returns one task |
| `POST` | `/api/v1/tasks` | Creates a ready task in an existing workspace |
| `GET` | `/api/v1/runs/{run_id}` | Returns one run |
| `POST` | `/api/v1/tasks/{task_id}/runs` | Creates a queued placeholder run |

`POST /api/v1/tasks/{task_id}/runs` only records a queued run. No worker consumes it yet. SSE events are intentionally deferred until run execution has real events to expose.

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

Problem URNs are stable machine identifiers. They can be replaced by resolvable HTTPS documentation only as a versioned compatibility decision.

## Storage boundary

Routers depend on `CoreService`; the service depends on the `CoreRepository` protocol. `InMemoryCoreRepository` is the current adapter. It is lock-protected for local concurrent requests, but its contents disappear whenever the process stops.
