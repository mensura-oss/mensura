import { describe, expect, it } from "vitest";

import {
  CHANGE_PROPOSAL_CHANGE_TYPES,
  CHANGE_PROPOSAL_LIMITS,
  CHANGE_PROPOSAL_SCHEMA_VERSION,
  CHANGE_PROPOSAL_STATUSES,
  type ChangeProposal,
} from "./change-proposal.js";

describe("change proposal v1 contracts", () => {
  it("pins the review lifecycle and safe change vocabulary", () => {
    expect(CHANGE_PROPOSAL_SCHEMA_VERSION).toBe("1");
    expect(CHANGE_PROPOSAL_STATUSES).toEqual([
      "proposed",
      "approved",
      "rejected",
    ]);
    expect(CHANGE_PROPOSAL_CHANGE_TYPES).toEqual([
      "create",
      "modify",
      "delete",
    ]);
  });

  it("keeps lineage, review state, digests, and truncation explicit", () => {
    const digest = `sha256:${"a".repeat(64)}` as const;
    const proposal: ChangeProposal = {
      id: "8dbb252e-9e19-4f89-83e4-d4fd0b4615a0",
      schemaVersion: CHANGE_PROPOSAL_SCHEMA_VERSION,
      runId: "273fa5bc-c63d-49d4-a2db-dc48287784c5",
      taskId: "93e863b4-46dc-48ae-b240-c7de893b03a9",
      workspaceId: "de8b5744-a229-4eb2-8a8b-c9065ff0a849",
      contextPackId: digest,
      providerId: "openai",
      promptVersion: "review.v2",
      status: "proposed",
      createdAt: "2026-07-19T12:00:00Z",
      reviewedAt: null,
      summary: "Update one file.",
      rationale: "The immutable context supports this bounded suggestion.",
      fileChanges: [
        {
          path: "src/example.ts",
          changeType: "modify",
          language: "TypeScript",
          beforeDigest: digest,
          afterDigest: digest,
          proposedText: "export const ready = true;\n",
          proposedTextBytes: 27,
          originalTextBytes: 27,
          truncated: false,
        },
      ],
    };

    expect(proposal.reviewedAt).toBeNull();
    expect(proposal.fileChanges[0]?.beforeDigest).toBe(digest);
    expect(CHANGE_PROPOSAL_LIMITS.maxStoredTextBytesPerFile).toBeLessThan(
      CHANGE_PROPOSAL_LIMITS.maxSourceTextBytes,
    );
  });
});
