import { describe, expect, it } from "vitest";

import {
  FILE_VERIFICATION_REASONS,
  PROPOSAL_VERIFICATION_OUTCOMES,
  PROPOSAL_VERIFICATION_SCHEMA_VERSION,
  PROPOSAL_VERIFICATION_STATUSES,
  VERIFICATION_SANDBOX_KINDS,
  type ProposalVerification,
} from "./verification.js";

describe("proposal verification v1 contracts", () => {
  it("pins the sandbox vocabulary and closed outcomes", () => {
    expect(PROPOSAL_VERIFICATION_SCHEMA_VERSION).toBe("1");
    expect(PROPOSAL_VERIFICATION_STATUSES).toEqual(["passed", "failed"]);
    expect(PROPOSAL_VERIFICATION_OUTCOMES).toEqual([
      "sandbox_verified",
      "guard_failed",
      "materialization_failed",
    ]);
    expect(VERIFICATION_SANDBOX_KINDS).toEqual(["git_worktree"]);
    expect(FILE_VERIFICATION_REASONS).toContain("before_content_mismatch");
  });

  it("keeps lineage, sandbox metadata, and safe diff aggregates explicit", () => {
    const digest = `sha256:${"b".repeat(64)}` as const;
    const verification: ProposalVerification = {
      id: "0a4f4a4e-3f43-4e5d-91cb-9a3ee76146a5",
      schemaVersion: PROPOSAL_VERIFICATION_SCHEMA_VERSION,
      proposalId: "8dbb252e-9e19-4f89-83e4-d4fd0b4615a0",
      runId: "273fa5bc-c63d-49d4-a2db-dc48287784c5",
      taskId: "93e863b4-46dc-48ae-b240-c7de893b03a9",
      workspaceId: "de8b5744-a229-4eb2-8a8b-c9065ff0a849",
      contextPackId: digest,
      status: "passed",
      outcome: "sandbox_verified",
      sandbox: {
        kind: "git_worktree",
        commitId: "c".repeat(40),
        cleanupCompleted: true,
      },
      guard: {
        status: "passed",
        blocking: false,
        summary: {
          totalCount: 2,
          passedCount: 2,
          failedCount: 0,
          errorCount: 0,
          blockingFailures: 0,
          isBlocking: false,
        },
        checks: [
          {
            kind: "lint",
            status: "passed",
            blocking: true,
            summary: "Lint passed.",
            exitCode: 0,
            durationMs: 120,
            outputExcerpt: "",
            outputTruncated: false,
          },
        ],
      },
      fileResults: [
        {
          path: "src/example.ts",
          changeType: "modify",
          beforeDigest: digest,
          afterDigest: digest,
          sandboxDigest: digest,
          appliedInSandbox: true,
          reason: "applied",
        },
      ],
      safeDiff: {
        filesTotal: 1,
        createdCount: 0,
        modifiedCount: 1,
        deletedCount: 0,
        appliedCount: 1,
        unappliedCount: 0,
        proposedBytesTotal: 27,
      },
      createdAt: "2026-07-20T12:00:00Z",
      finishedAt: "2026-07-20T12:00:04Z",
      durationMs: 4_000,
    };

    expect(verification.sandbox.kind).toBe("git_worktree");
    expect(verification.guard?.summary.isBlocking).toBe(false);
    expect(verification.safeDiff.appliedCount).toBe(
      verification.fileResults.length,
    );
  });
});
