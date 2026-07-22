import { describe, expect, it } from "vitest";

import {
  VAULT_INDEX_STATUSES,
  VAULT_SEARCH_STRATEGY,
  VAULT_SKIP_REASONS,
  VAULT_SOURCE_TYPES,
} from "./vault-index.js";
import type {
  VaultArchitectureSummary,
  VaultIndexSnapshot,
  VaultMemoryItemDetail,
  VaultSearchResponse,
} from "./vault-index.js";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const indexId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";
const memoryItemId = "8f2b6d4a-1c3e-4f5a-9b7c-0d1e2f3a4b5c";

describe("Vault index contracts", () => {
  it("closes the source-type set to code/doc/config", () => {
    expect(VAULT_SOURCE_TYPES).toEqual(["code", "doc", "config"]);
  });

  it("keeps the index lifecycle intentionally minimal", () => {
    expect(VAULT_INDEX_STATUSES).toEqual(["ready"]);
  });

  it("enumerates the honest skip reasons", () => {
    expect(VAULT_SKIP_REASONS).toContain("binary");
    expect(VAULT_SKIP_REASONS).toContain("too_large");
    expect(VAULT_SKIP_REASONS).toContain("empty");
  });

  it("names the retrieval strategy as a lexical vector model, not neural", () => {
    expect(VAULT_SEARCH_STRATEGY).toBe("lexical-vector-cosine");
  });

  it("shapes an index snapshot with denormalized counts", () => {
    const snapshot: VaultIndexSnapshot = {
      id: indexId,
      workspaceId,
      status: "ready",
      indexedAt: "2026-07-21T12:00:00Z",
      summary: {
        memoryItemCount: 3,
        chunkCount: 12,
        codeFileCount: 1,
        docFileCount: 1,
        configFileCount: 1,
        totalSizeBytes: 2048,
        skippedCount: 1,
        skippedByReason: [{ value: "empty", count: 1 }],
        languages: [{ value: "Python", count: 1 }],
        skippedSample: [{ path: "empty.py", reason: "empty" }],
      },
    };

    expect(snapshot.summary.memoryItemCount).toBe(3);
    expect(snapshot.summary.skippedSample[0]?.reason).toBe("empty");
  });

  it("shapes a ranked search response carrying file context per hit", () => {
    const response: VaultSearchResponse = {
      workspaceId,
      indexId,
      query: "authenticate password",
      strategy: VAULT_SEARCH_STRATEGY,
      total: 2,
      returned: 1,
      hits: [
        {
          memoryItemId,
          chunkId: "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
          path: "src/auth.py",
          sourceType: "code",
          language: "Python",
          chunkIndex: 0,
          startLine: 1,
          endLine: 2,
          score: 0.87,
          snippet: "def authenticate(username, password): ...",
        },
      ],
    };

    expect(response.hits[0]?.path).toBe("src/auth.py");
    expect(response.hits[0]?.startLine).toBe(1);
    expect(response.returned).toBe(1);
  });

  it("shapes a memory item detail with its chunks", () => {
    const detail: VaultMemoryItemDetail = {
      item: {
        id: memoryItemId,
        workspaceId,
        indexId,
        path: "src/auth.py",
        sourceType: "code",
        language: "Python",
        digest: "sha256:" + "a".repeat(64),
        sizeBytes: 96,
        chunkCount: 1,
        indexedAt: "2026-07-21T12:00:00Z",
      },
      chunks: [
        {
          id: "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
          memoryItemId,
          chunkIndex: 0,
          startLine: 1,
          endLine: 2,
          charCount: 64,
          digest: "sha256:" + "b".repeat(64),
          text: "def authenticate(username, password):\n    return verify(...)\n",
        },
      ],
    };

    expect(detail.chunks).toHaveLength(detail.item.chunkCount);
  });

  it("shapes an architecture summary with modules and technologies", () => {
    const summary: VaultArchitectureSummary = {
      workspaceId,
      indexId,
      generatedAt: "2026-07-21T12:00:00Z",
      fileCount: 3,
      codeFileCount: 1,
      docFileCount: 1,
      configFileCount: 1,
      totalSizeBytes: 2048,
      languages: [{ value: "Python", count: 1 }],
      modules: [
        {
          name: "src",
          path: "src",
          fileCount: 1,
          totalSizeBytes: 96,
          primaryLanguage: "Python",
        },
      ],
      technologies: ["Python"],
      entryPoints: ["src/main.py"],
    };

    expect(summary.modules[0]?.name).toBe("src");
    expect(summary.technologies).toContain("Python");
  });
});
