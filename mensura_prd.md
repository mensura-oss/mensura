# Mensura — Product Requirements Document

## Overview

Mensura is a fully open-source platform for AI-assisted software development focused on professional developers, technical teams, and maintainers. The product combines a desktop workspace, agent orchestration backend, project memory, quality policies, and plugin extensibility into a self-host-first system[cite:31][cite:72][cite:85].

## Problem statement

Current AI coding tools often optimize for speed and novelty but under-serve engineering discipline. Developers need reproducible runs, code review visibility, persistent project memory, tool interoperability, and enforceable quality policies across agent workflows[cite:79][cite:85].

## Goals

- Provide a unified agentic development workspace.
- Reduce the friction of using multiple AI coding tools together.
- Increase confidence in AI-generated changes.
- Support local and self-hosted deployment.
- Make integration with external tools open and standard-based through MCP[cite:31].

## Users

### Primary
- Individual developers.
- OSS maintainers.
- Small teams.
- Technical founders.

### Secondary
- Educators.
- Students.
- DevOps-minded teams.

## User stories

- As a developer, I want to assign a task to an AI agent and review a clear diff before accepting changes.
- As a maintainer, I want tests and security checks to run automatically on AI changes.
- As a team lead, I want a shared project memory that helps agents understand the codebase.
- As a self-hosting user, I want to run the full platform without a proprietary cloud.
- As a power user, I want to connect my own tools and providers through a standard integration layer.

## Product modules

### Mensura Studio
- Workspace UI.
- Editor.
- Terminal.
- Kanban.
- Chat.
- Diff viewer.
- Logs.

### Mensura Core
- Planner.
- Orchestrator.
- Execution engine.
- Model router.
- Run history.

### Mensura Vault
- Code indexing.
- Semantic search.
- Docs ingestion.
- Decision memory.
- Graph relations.

### Mensura Guard
- Policy checks.
- Test gates.
- Security checks.
- Audit log.
- Approval flow.

### Mensura Hub
- Plugins.
- Connectors.
- Templates.
- Agent packs.

## Functional requirements

### FR-1 Workspace
- The system must provide a desktop workspace with editor, terminal, repository tree, task board, and agent chat.
- The system should support multiple simultaneous agent sessions.

### FR-2 Repository support
- The system must connect to a local Git repository.
- The system must show branch state, changes, and diff previews.

### FR-3 Agent orchestration
- The system must support task planning and multi-step execution.
- The system should support parallel agents for independent subtasks.
- The system must persist run history.

### FR-4 Memory
- The system must index repository files and project documents.
- The system must support semantic retrieval of project context.
- The system should link memory items to tasks and runs.

### FR-5 Governance
- The system must support pre-completion lint/test checks.
- The system must support approval gates for sensitive paths.
- The system should score change risk.

### FR-6 Extensibility
- The system must expose an MCP-compatible interface for tools/resources/prompts[cite:31][cite:74].
- The system should provide a plugin SDK.

### FR-7 Self-hosting
- The system must be deployable locally or via Docker Compose.
- The system should support multi-user team deployments.

## Non-functional requirements

- Fast local startup.
- Reliable persistence of run history.
- Transparent logs.
- Secure defaults.
- Cross-platform desktop support.
- Extensible architecture.
- Graceful degradation when an external model provider fails.

## Acceptance criteria

- A user can connect a repo, ask an agent to modify code, review a diff, run checks, and approve a task end-to-end.
- A team can self-host Core, share Vault memory, and enforce Guard policies.
- A plugin can be installed without patching the core codebase.

## Release scope

### MVP
- Desktop app.
- Basic repo indexing.
- One orchestration path.
- Diff review.
- Guard lint/test integration.
- BYOK LLM support.

### Post-MVP
- Plugin marketplace.
- Team mode.
- Knowledge graph UI.
- Voice.
- Remote runners.

## KPIs

- Setup time under 15 minutes for local install.
- Successful first task completion rate.
- Ratio of accepted vs rejected agent diffs.
- Average time from task creation to review-ready diff.
- Growth in community plugins.
