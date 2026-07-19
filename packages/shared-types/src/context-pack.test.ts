import { describe, expect, it } from "vitest";

import {
  CONTEXT_PACK_CAPTURE_MODES,
  CONTEXT_PACK_SCHEMA_VERSION,
} from "./context-pack.js";
import type { CreateRunRequest, Run } from "./index.js";

describe("context pack v1 contracts", () => {
  it("pins the canonical manifest schema version", () => {
    expect(CONTEXT_PACK_SCHEMA_VERSION).toBe("1");
  });

  it("makes captured text and metadata-only binary evidence explicit", () => {
    expect(CONTEXT_PACK_CAPTURE_MODES).toEqual(["text_preview", "metadata_only"]);
  });

  it("requires an immutable context-pack binding on queued runs", () => {
    const contextPackId = `sha256:${"a".repeat(64)}` as const;
    const request: CreateRunRequest = { contextPackId };
    const run: Run = {
      id: "run-id",
      taskId: "task-id",
      contextPackId,
      contextPack: {
        id: contextPackId,
        workspaceId: "workspace-id",
        inventoryId: "inventory-id",
        schemaVersion: CONTEXT_PACK_SCHEMA_VERSION,
        fileCount: 2,
        totalFileBytes: 1024,
        totalPreviewBytes: 512,
      },
      status: "queued",
      execution: null,
      startedAt: null,
      finishedAt: null,
      createdAt: "2026-07-19T12:00:00Z",
      updatedAt: "2026-07-19T12:00:00Z",
    };

    expect(request.contextPackId).toBe(contextPackId);
    expect(run.contextPack.id).toBe(run.contextPackId);
    expect(run.contextPack.fileCount).toBe(2);
  });
});
