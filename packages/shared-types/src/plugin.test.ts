import { describe, expect, it } from "vitest";

import { validatePluginManifest } from "./plugin.js";

const validManifest = {
  name: "mensura-plugin-example",
  version: "0.1.0",
  displayName: "Example Plugin",
  type: "tool",
  permissions: ["workspace.read", "network.http"],
  entry: "dist/index.js",
  compatibility: { mensura: ">=0.1.0" },
};

describe("validatePluginManifest", () => {
  it("accepts a supported, permission-declaring manifest", () => {
    const result = validatePluginManifest(validManifest);

    expect(result.ok).toBe(true);
    expect(result.value).toEqual(validManifest);
    expect(result.issues).toEqual([]);
  });

  it("rejects unknown permissions and path traversal", () => {
    const result = validatePluginManifest({
      ...validManifest,
      permissions: ["network.raw"],
      entry: "../outside.js",
    });

    expect(result.ok).toBe(false);
    expect(result.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ path: "permissions.0" }),
        expect.objectContaining({ path: "entry" }),
      ]),
    );
  });

  it("rejects duplicate permissions", () => {
    const result = validatePluginManifest({
      ...validManifest,
      permissions: ["workspace.read", "workspace.read"],
    });

    expect(result.ok).toBe(false);
    expect(result.issues).toContainEqual({
      path: "permissions.1",
      message: "Permission is duplicated.",
    });
  });

  it("rejects non-object input with a root issue", () => {
    expect(validatePluginManifest(null)).toEqual({
      ok: false,
      issues: [{ path: "$", message: "Manifest must be an object." }],
    });
  });
});
