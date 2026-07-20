import { describe, expect, it } from "vitest";

import {
  APPLICATION_ARTIFACT_SCHEMA_VERSION,
  APPLICATION_STATUSES,
  APPLICATION_TARGET_KINDS,
  APPLICATION_UNDO_STRATEGIES,
  APPLIED_FILE_REASONS,
  type ApplicationArtifact,
} from "./application.js";

describe("application artifact v1 contracts", () => {
  it("pins the closed application status and target vocabulary", () => {
    expect(APPLICATION_ARTIFACT_SCHEMA_VERSION).toBe("1");
    expect(APPLICATION_STATUSES).toEqual([
      "applied_guard_passed",
      "applied_guard_failed",
      "applied_guard_unavailable",
      "application_failed",
    ]);
    expect(APPLICATION_TARGET_KINDS).toEqual(["live_working_tree"]);
    expect(APPLIED_FILE_REASONS).toEqual([
      "applied",
      "write_failed",
      "not_attempted",
    ]);
    expect(APPLICATION_UNDO_STRATEGIES).toEqual(["restore_prior_content"]);
  });

  it("keeps lineage, applied digests, and undo restoration basis explicit", () => {
    const digest = `sha256:${"a".repeat(64)}` as const;
    const priorDigest = `sha256:${"b".repeat(64)}` as const;
    const application: ApplicationArtifact = {
      id: "0a4f4a4e-3f43-4e5d-91cb-9a3ee76146a5",
      schemaVersion: APPLICATION_ARTIFACT_SCHEMA_VERSION,
      proposalId: "8dbb252e-9e19-4f89-83e4-d4fd0b4615a0",
      verificationId: "273fa5bc-c63d-49d4-a2db-dc48287784c5",
      runId: "93e863b4-46dc-48ae-b240-c7de893b03a9",
      taskId: "de8b5744-a229-4eb2-8a8b-c9065ff0a849",
      workspaceId: "b5f2f9a0-6b8f-4a1d-9d0e-2b2f0a4d5c6e",
      contextPackId: digest,
      status: "applied_guard_passed",
      target: {
        kind: "live_working_tree",
        liveCommitId: "c".repeat(40),
        verificationCommitId: "c".repeat(40),
        headMovedSinceVerification: false,
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
      guardUnavailableReason: null,
      fileResults: [
        {
          path: "src/example.ts",
          changeType: "modify",
          beforeDigest: priorDigest,
          liveBeforeDigest: priorDigest,
          afterDigest: digest,
          appliedDigest: digest,
          applied: true,
          reason: "applied",
        },
      ],
      summary: {
        filesTotal: 1,
        createdCount: 0,
        modifiedCount: 1,
        deletedCount: 0,
        appliedCount: 1,
        failedCount: 0,
      },
      undo: {
        strategy: "restore_prior_content",
        note: "Restore each prior digest to undo this application later.",
        capturedAt: "2026-07-20T12:00:00Z",
        files: [
          {
            path: "src/example.ts",
            changeType: "modify",
            priorExisted: true,
            priorDigest,
            priorContent: "export const value = 1;\n",
            priorContentBytes: 24,
            priorTruncated: false,
            appliedDigest: digest,
          },
        ],
      },
      createdAt: "2026-07-20T12:00:00Z",
      finishedAt: "2026-07-20T12:00:04Z",
      durationMs: 4_000,
    };

    expect(application.target.kind).toBe("live_working_tree");
    expect(application.guard?.status).toBe("passed");
    expect(application.summary.appliedCount).toBe(
      application.fileResults.length,
    );
    expect(application.undo.files[0]?.priorDigest).toBe(priorDigest);
  });
});
