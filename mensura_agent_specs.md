# Mensura — Agent Specifications

## Architect agent
- Reads repository structure.
- Builds architecture summary.
- Proposes implementation plan.
- Identifies impacted modules.

## Research agent
- Reads documentation and code comments.
- Extracts relevant patterns and APIs.
- Produces implementation notes.

## Coder agent
- Edits files.
- Creates implementation diffs.
- Explains modified files and intent.

## Test agent
- Writes unit/integration tests.
- Updates fixtures.
- Verifies likely edge cases.

## Reviewer agent
- Critiques the diff.
- Flags style, safety, and maintainability issues.
- Requests revision if needed.

## Security agent
- Detects secrets, risky code paths, dangerous dependencies.
- Interacts with Guard for policy escalation.

## DevOps agent
- Updates Docker, CI, environment templates, deployment docs.
- Proposes rollout steps.

## Docs agent
- Updates README, architecture docs, changelog, and inline explanations.

## Shared contract

Every agent should return:
- task summary;
- actions taken;
- files changed;
- rationale;
- known risks;
- next suggested step.
