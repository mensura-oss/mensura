# Mensura — Plugin SDK Specification

## Goals

The plugin SDK enables third-party extensions without modifying the core platform. Plugins should be installable, permissioned, versioned, and safely isolated where possible.

## Plugin types

- Tool plugin.
- MCP connector plugin.
- Agent pack plugin.
- Prompt pack plugin.
- UI extension plugin.
- Template/plugin scaffold.

## Manifest example

```json
{
  "name": "mensura-plugin-example",
  "version": "0.1.0",
  "displayName": "Example Plugin",
  "type": "tool",
  "permissions": ["workspace.read", "workspace.write", "network.http"],
  "entry": "dist/index.js",
  "compatibility": {
    "mensura": ">=0.1.0"
  }
}
```

## Security model

- Explicit permission declarations.
- Installation review prompt.
- Signed release metadata when possible.
- Restricted access to credentials.
- Policy-aware execution.

## SDK packages

- `@mensura/sdk`
- `@mensura/mcp`
- `@mensura/shared-types`

## Lifecycle hooks

- `onInstall`
- `onActivate`
- `onTaskStart`
- `onTaskFinish`
- `onWorkspaceOpen`
- `onDispose`
