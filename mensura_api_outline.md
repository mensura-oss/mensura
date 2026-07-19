# Mensura — API Outline

## Core API

### Workspaces
- `POST /workspaces`
- `GET /workspaces/:id`
- `PATCH /workspaces/:id`
- `DELETE /workspaces/:id`

### Projects
- `POST /projects`
- `GET /projects/:id`
- `POST /projects/:id/connect-repo`
- `POST /projects/:id/index`

### Tasks
- `POST /tasks`
- `GET /tasks/:id`
- `PATCH /tasks/:id`
- `POST /tasks/:id/run`
- `POST /tasks/:id/approve`
- `POST /tasks/:id/reject`

### Runs
- `GET /runs/:id`
- `GET /runs/:id/logs`
- `GET /runs/:id/diff`
- `GET /runs/:id/checks`
- `POST /runs/:id/retry`
- `POST /runs/:id/cancel`

## Vault API

- `POST /vault/index`
- `POST /vault/search`
- `GET /vault/memory/:id`
- `POST /vault/graph/query`
- `POST /vault/summarize`

## Guard API

- `POST /guard/checks/run`
- `GET /guard/checks/:runId`
- `POST /guard/policies/validate`
- `GET /guard/audit/:projectId`

## Hub API

- `GET /hub/plugins`
- `POST /hub/plugins/install`
- `POST /hub/plugins/uninstall`
- `GET /hub/connectors`
- `GET /hub/templates`

## Realtime

- `WS /ws/runs/:id`
- `WS /ws/tasks/:id`
- `WS /ws/project/:id/events`
