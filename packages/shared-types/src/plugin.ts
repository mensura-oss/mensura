export const PLUGIN_TYPES = [
  "tool",
  "mcp_connector",
  "agent_pack",
  "prompt_pack",
  "ui_extension",
  "template",
] as const;

export type PluginType = (typeof PLUGIN_TYPES)[number];

export const PLUGIN_PERMISSIONS = [
  "workspace.read",
  "workspace.write",
  "network.http",
  "process.execute",
  "secrets.use",
] as const;

export type PluginPermission = (typeof PLUGIN_PERMISSIONS)[number];

export interface PluginManifest {
  name: string;
  version: string;
  displayName: string;
  type: PluginType;
  permissions: PluginPermission[];
  entry: string;
  compatibility: {
    mensura: string;
  };
}

export interface ValidationIssue {
  path: string;
  message: string;
}

export interface ValidationResult<T> {
  ok: boolean;
  value?: T;
  issues: ValidationIssue[];
}

const semanticVersion = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
const packageName = /^(?:@[a-z0-9][a-z0-9._-]*\/)?[a-z0-9][a-z0-9._-]*$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasSafeRelativeEntry(entry: string): boolean {
  const segments = entry.split(/[\\/]/);
  return entry.length > 0 && !entry.startsWith("/") && !/^[A-Za-z]:/.test(entry) && !segments.includes("..");
}

export function validatePluginManifest(input: unknown): ValidationResult<PluginManifest> {
  const issues: ValidationIssue[] = [];

  if (!isRecord(input)) {
    return { ok: false, issues: [{ path: "$", message: "Manifest must be an object." }] };
  }

  if (typeof input.name !== "string" || !packageName.test(input.name)) {
    issues.push({ path: "name", message: "Name must be a valid lowercase package name." });
  }

  if (typeof input.version !== "string" || !semanticVersion.test(input.version)) {
    issues.push({ path: "version", message: "Version must be a semantic version." });
  }

  if (typeof input.displayName !== "string" || input.displayName.trim().length === 0) {
    issues.push({ path: "displayName", message: "Display name must not be empty." });
  }

  if (typeof input.type !== "string" || !(PLUGIN_TYPES as readonly string[]).includes(input.type)) {
    issues.push({ path: "type", message: "Plugin type is not supported." });
  }

  if (!Array.isArray(input.permissions)) {
    issues.push({ path: "permissions", message: "Permissions must be an array." });
  } else {
    const uniquePermissions = new Set<string>();
    for (const [index, permission] of input.permissions.entries()) {
      if (typeof permission !== "string" || !(PLUGIN_PERMISSIONS as readonly string[]).includes(permission)) {
        issues.push({ path: `permissions.${index}`, message: "Permission is not supported." });
      } else if (uniquePermissions.has(permission)) {
        issues.push({ path: `permissions.${index}`, message: "Permission is duplicated." });
      } else {
        uniquePermissions.add(permission);
      }
    }
  }

  if (typeof input.entry !== "string" || !hasSafeRelativeEntry(input.entry)) {
    issues.push({ path: "entry", message: "Entry must be a safe relative path." });
  }

  if (
    !isRecord(input.compatibility) ||
    typeof input.compatibility.mensura !== "string" ||
    input.compatibility.mensura.trim().length === 0
  ) {
    issues.push({ path: "compatibility.mensura", message: "Mensura compatibility range is required." });
  }

  if (issues.length > 0) {
    return { ok: false, issues };
  }

  return { ok: true, value: input as unknown as PluginManifest, issues: [] };
}
