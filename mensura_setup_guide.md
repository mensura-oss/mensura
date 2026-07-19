# Mensura — Initial Setup Guide

## Local development prerequisites

- Rust toolchain.
- Node.js LTS.
- pnpm.
- Python 3.12+.
- Docker and Docker Compose.
- Git.

## First local setup

1. Clone the monorepo.
2. Install JavaScript dependencies.
3. Create a Python virtual environment for backend services.
4. Start PostgreSQL and Redis through Docker Compose.
5. Run database migrations.
6. Start `services/core`.
7. Start `apps/studio` in development mode.
8. Connect a local repository and run indexing.

## Recommended first demo flow

1. Open a sample repo.
2. Ask the architect agent for a project summary.
3. Create a small implementation task.
4. Let the coder agent produce a diff.
5. Review Guard checks.
6. Approve the task.
