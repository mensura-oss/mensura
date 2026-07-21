# Mensura Architecture Overview

## Purpose

Mensura is a local AI-assisted development platform that turns model-generated suggestions into a **controlled, auditable change pipeline** for codebases. It focuses on safety, reproducibility, and human approval instead of letting models write directly to repositories.

At a high level, Mensura manages this lifecycle:

`task → context pack → run → change proposal → verification → guarded apply → undo`

All artifacts are stored in a durable SQLite database, with explicit domain models, REST APIs, background jobs, and live UI updates via Server-Sent Events (SSE).

## Core Components

### Core Service

The Core service is a FastAPI-based backend responsible for domain logic, persistence, and safe interaction with Git workspaces.

Key technologies:
- SQLite with SQLAlchemy 2.x and Alembic migrations.
- WAL mode with `foreign_keys=ON` and `synchronous=NORMAL` pragmas for durability and concurrency.
- Structured Pydantic models for all public contracts.

Core domains (persisted in SQLite):
- Workspaces
- Tasks
- Runs and guard runs
- Vault inventory snapshots and items
- Context packs
- Change proposals
- Verification artifacts
- Application artifacts
- Undo artifacts
- Backup artifacts
- Jobs (durable background tasks)

### Studio

Studio is a Tauri-based desktop application (React + TypeScript) that provides the main user interface.

Responsibilities:
- Manage workspaces, tasks, runs, proposals, verifications, applications, undos, backups, and jobs.
- Subscribe to live SSE streams to reflect status changes without heavy polling.
- Use TanStack Query to keep views in sync with the Core REST API.

### Persistence Layer

Mensura uses a single SQLite database as the source of truth for all domain artifacts.

Characteristics:
- Database path: `~/.mensura/core.db` by default, configurable via `MENSURA_DATABASE_URL`.
- Alembic migrations (e.g., `001_initial_schema` through `005_add_job_retry_fields`).
- JSON columns for bounded structured payloads where appropriate.
- Repositories implemented against Protocol interfaces so tests can still inject in-memory implementations.

## Change Pipeline

### 1. Tasks and Context Packs

A **workspace** points to a Git repository. A **task** describes the desired change or review.

From a task and the current repository state, the Core builds an immutable **context pack**:
- Selected files and metadata.
- SHA-256 digests for integrity.
- Vault inventory references if needed.

This context pack is a snapshot of what the model is allowed to see, not the live filesystem.

### 2. Runs

A **run** executes a provider against an immutable input:
- Task description.
- Context pack.
- Provider configuration and prompt version.

Mensura currently supports:
- A deterministic, credential-free provider for fully local runs.
- An optional BYOK OpenAI provider using the Responses API with structured outputs, local keyring for API keys, and strict JSON Schema validation.

Guarantees:
- The provider receives only the persisted context, not a live repository path.
- Providers have no write access to the repository.
- Output is bounded, schema-validated JSON, or a structured failure.

### 3. Change Proposals

From a successful run, Mensura can derive a **ChangeProposal** artifact:
- Independent v1 schema.
- Lifecycle: `proposed → approved | rejected`.
- Maximum 16 file changes.
- Per-file fields such as path, change type, language, SHA-256 digests before/after, byte counts, truncation flags, and bounded proposed content.
- No raw patches, binary blobs, shell commands, or repository paths.

The proposal is reviewable and inspectable and does not mutate any repository state by itself.

### 4. Approval

Approval is modeled at the proposal level:
- Review state is `proposed`, `approved`, or `rejected`.
- Runs remain immutable execution records.

This separation keeps execution results, proposals, and approval decisions as distinct artifacts.

### 5. Verification in an Isolated Sandbox

For an approved proposal, Mensura can create a **verification** in a temporary sandbox:
- Uses `git worktree` to create a detached worktree of the repository’s HEAD under a fresh `mensura-verification-*` temp directory outside the repo.
- Materializes the proposal only inside that worktree, never in the main working tree.
- Runs Guard (e.g., ruff, pytest, or other checks) inside the sandbox.
- Cleans up the worktree in a `finally` block using `git worktree remove --force`, temp directory deletion, and `git worktree prune`.

The verification artifact records:
- Outcome (e.g., sandbox verified, guard failed, materialization failed).
- Verified commit.
- Per-file digests and safe diff metadata.
- Guard summaries with bounded excerpts.

Live repository state and digests are checked before and after to guarantee no writes and no leaked sandboxes.

### 6. Apply to Live Working Tree

An approved proposal with a passing verification can be **applied to the live working tree**:
- No staging, committing, pushing, or checking out branches.
- No provider involvement during apply.

Safety rules:
- Resolve each target path relative to the workspace, rejecting absolute paths, `..` segments, and symlinked components.
- Compare live file digests against the expected `beforeDigest` for all targets; if anything drifted, refuse the whole apply before writing.
- Apply the exact verified content only, never re-generating from the provider.

Atomic write strategy:
- Write each file to a temporary file in the same directory.
- Flush and fsync (where practical).
- Atomically replace the destination via `os.replace` or equivalent, so the change appears as a single operation.

After applying:
- Guard is run again on the live working tree.
- An **ApplicationArtifact** is persisted, recording per-file results, digests, Guard outcome, and undo metadata.

### 7. Undo

Mensura supports a **bounded, digest-guarded undo** for text-file applications:
- One explicit undo per application in this cycle.
- Uses recorded undo metadata: prior content, applied digests, and file-level intent.

Preconditions:
- All targeted live files must still match the recorded applied digest; any drift blocks the undo before any write.

Behavior:
- For created files: delete them if the current digest matches the applied digest.
- For modified files: restore the prior captured text via the same atomic temp-file strategy.
- No partial undo: prefer all-or-nothing semantics.

After undo:
- Guard is run again on the live working tree.
- An **UndoArtifact** is persisted with outcome, per-file results, and digests.

This completes a reversible pipeline:

`context pack → run → change proposal → approval → sandbox verification → guarded apply → guarded undo`

## Safety and Reliability

### Provider Isolation

Models never receive direct write access to the repository:
- They operate only on immutable context packs.
- All writes go through Core’s guarded apply/undo pipeline.

### Digest-Guarded Writes and Undo

Both apply and undo use digest checks to prevent overwriting unexpected live changes:
- A mismatch between expected and actual digests results in a refusal with a structured RFC 9457 problem response.

### Backups and Restore

Mensura provides explicit backup and restore for the Core database:

Backups:
- Implemented via the SQLite Online Backup API (`Connection.backup`) for safe snapshots of a live WAL-mode database.
- Each backup is stored under `~/.mensura/backups/` with SHA-256 digest, file size, and Alembic head captured.
- Exposed through:
  - `POST /api/v1/backups`
  - `GET /api/v1/backups`
  - `GET /api/v1/backups/{id}`

Restore:
- Validates the backup’s integrity.
- Performs a WAL checkpoint (TRUNCATE) and disposes the SQLAlchemy engine.
- Uses `shutil.copy2` and `os.replace` to restore the main DB file, then cleans up WAL/SHM.
- Requires a Core restart; this avoids complex in-process replacement.

### Durable Job Queue

Mensura includes a **SQLite-backed durable job queue** integrated into the Core database:

- Job types: `proposal_verification`, `application_apply`, `application_undo`, `backup_create`.
- Statuses: `queued`, `running`, `succeeded`, `failed`.
- Fields: job type, target entity type and ID, workspace ID, timestamps, attempt count, last error summary.
- A single in-process worker atomically claims queued jobs and runs the same service functions as the synchronous endpoints.

Restart behavior:
- On startup, jobs left in `running` are transitioned to `failed` with an "interrupted by restart; outcome unknown — inspect the artifact" summary.
- This avoids unsafe automatic re-execution and double side effects.

### SSE and Live Updates

SSE is used for live UI updates without turning events into the source of truth:

- Endpoint: `GET /api/v1/events/stream` (text/event-stream via sse-starlette).
- Event envelope: `eventId`, `eventType`, `occurredAt`, `workspaceId`, `entityType`, `entityId`, `status`, `summary` (≤ 200 chars).
- Event types (initial set):
  - `run.status.changed`
  - `verification.created`
  - `application.created`
  - `undo.created`
  - `backup.created`

Core maintains an in-memory sliding buffer (e.g., 100 events) to support basic Last-Event-Id replay. Studio uses these events only to trigger TanStack Query refetches; the REST API remains the authoritative state.

## Jobs and Retries

### Job-First Flows

Studio can launch long-running operations as durable jobs directly from domain panels:
- Proposal verification → `proposal_verification` job.
- Application apply → `application_apply` job.
- Application undo → `application_undo` job.
- Backup creation → `backup_create` job.

JobsPanel shows job status, type, target entity, timestamps, and error summaries.

### Retry Model

Retries are modeled as **linked child jobs**, never by mutating existing history:

- Fields:
  - `retryOfJobId` — direct parent job.
  - `rootJobId` — root of the retry chain.
  - `retryEligible` — whether another retry is allowed.
  - `retryCount` — number of retries used.
- Only FAILED jobs are retryable.
- One explicit retry per job in this cycle.
- No automatic retries.
- The child job reuses the same domain service functions, preserving all safety checks.

This design keeps the audit trail clear and aligns with best practices for idempotent, retry-safe job processing.

## Summary

Mensura combines:
- Local, SQLite-backed durable state.
- A reversible, digest-guarded pipeline for code changes.
- Sandbox verification via Git worktrees.
- Guarded apply/undo with atomic writes.
- Explicit backups and restores for Core state.
- A durable job queue and live SSE updates.

The result is a small, self-contained AI-assisted development platform that prioritizes safety, auditability, and human control over repository changes.
