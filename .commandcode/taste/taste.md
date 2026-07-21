# workflow
- Update docs/agent_memory.md before and after every major implementation step. Confidence: 0.85
- Deliver one observable vertical slice at a time; keep scope minimal and avoid building everything at once. Confidence: 0.80
- Use conventional commits format (feat(scope): description) for all commit messages. Confidence: 0.75
- Run a multi-language verification matrix before every commit: pnpm check (TypeScript + tests + builds + cargo), Python Ruff lint/format + pytest -W error, Rust fmt --check, and git diff --check. Confidence: 0.70

# communication
- Match the user's language: respond in Russian when the user writes in Russian, and in English when the user writes in English. Confidence: 0.65

# architecture
See [architecture/taste.md](architecture/taste.md)
# persistence
See [persistence/taste.md](persistence/taste.md)
# studio
- Use TanStack Query for server state management in Studio; keep local UI state minimal and explicit. Confidence: 0.70

# cli
- Use pnpm as the package manager for the monorepo workspace. Confidence: 0.65

# typescript
- Point shared-package TypeScript `types` exports to `src/index.ts` (not `dist/index.d.ts`) so new contracts are visible to consumers without rebuilding. Confidence: 0.70

- Use Pydantic aliases to keep Python code in snake_case while serializing camelCase JSON on the wire. Confidence: 0.70

# python
- Use `response_model_exclude_none=True` on FastAPI routes to omit null optional fields from JSON responses, matching TypeScript optional property semantics. Confidence: 0.70

# git
- Implement read-only Git inspection behind a protocol interface (GitPython adapter); never expose patches, file contents, or write operations in API responses. Confidence: 0.65

# safety
- Prefer explicit refusal over risky auto-resolution; never silently overwrite drifted or unexpected state. Confidence: 0.60

# verification
- Verify each completed work cycle against a live Core server (curl + real repository) and the native Tauri app bundle (computer-use accessibility tree) before creating the cycle commit. Confidence: 0.80

# architecture
- Use content-derived SHA-256 digests (canonical JSON hashing) for immutable resource identities rather than random UUIDs, so repeating the same input produces the same identity. Confidence: 0.65

# filesystem
- Use fixed, explicit exclusion rules for Vault file inventory rather than interpreting .gitignore; tighten rules with specific path/name patterns when real artifacts are discovered rather than adding broad exclusions. Confidence: 0.65
- Use atomic file writes: same-directory temp file, flush, fsync if practical, atomic replace, explicit cleanup on failure. Confidence: 0.55
