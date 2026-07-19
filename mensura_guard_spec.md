# Mensura — Guard Specification

## Purpose

Mensura Guard ensures that AI-assisted development remains reviewable, testable, and policy-compliant.

## Main capabilities

- Run format/lint/test steps before task completion.
- Block risky changes until approved.
- Scan for secrets and obvious vulnerabilities.
- Produce structured check results.
- Persist audit logs.
- Enforce repository path policies.

## Policy examples

- Changes to `auth/`, `billing/`, or `infra/production/` require explicit human approval.
- Any change that fails tests cannot be marked complete.
- Any change that introduces a detected secret is blocked.
- Any plugin requiring network access must declare it before installation.

## Check pipeline

1. Format.
2. Lint.
3. Unit tests.
4. Integration tests if configured.
5. Secret scan.
6. Dependency/security scan.
7. Risk scoring.
8. Final approval state.
