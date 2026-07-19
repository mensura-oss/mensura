# Mensura — Monorepo Structure

```text
mensura/
  .github/
    workflows/
  apps/
    studio/
    web/
    docs/
  services/
    core/
    vault/
    guard/
    hub/
    voice/
  packages/
    ui/
    config/
    sdk/
    mcp/
    prompts/
    shared-types/
    test-utils/
  infra/
    docker/
    k8s/
    terraform/
  examples/
  scripts/
  docs/
    architecture/
    product/
    setup/
    governance/
```

## Notes

- `apps/studio` contains the Tauri desktop app.
- `services/core` contains orchestration and runtime APIs.
- `services/vault` contains indexing and retrieval logic.
- `services/guard` contains quality and security policy services.
- `services/hub` contains plugin and connector registry logic.
- `packages/sdk` contains the public developer SDK.
- `packages/mcp` contains MCP adapters and helpers[cite:31].
