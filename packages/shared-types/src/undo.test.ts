import { describe, expect, it } from "vitest";
import {
  UNDO_ARTIFACT_SCHEMA_VERSION,
  UNDO_FILE_ACTIONS,
  UNDO_STATUSES,
} from "./undo.js";
import type {
  UndoArtifact,
  UndoFileOutcome,
  UndoGuardResult,
} from "./undo.js";

describe("Undo contracts", () => {
  const baseArtifact: UndoArtifact = {
    id: "d6e7f8a9-b0c1-2d3e-4f5a-6b7c8d9e0f1a",
    schemaVersion: "1",
    applicationId: "a1b2c3d4-e5f6-7890-abcd-ef0123456789",
    proposalId: "b2c3d4e5-f6a7-8901-bcde-f01234567890",
    workspaceId: "c3d4e5f6-a7b8-9012-cdef-012345678901",
    status: "undone_guard_passed",
    fileOutcomes: [],
    guard: null,
    guardUnavailableReason: null,
    createdAt: "2026-07-20T12:00:00Z",
    finishedAt: "2026-07-20T12:00:01Z",
    durationMs: 100,
  };

  it("pins UNDO_ARTIFACT_SCHEMA_VERSION to 1", () => {
    expect(UNDO_ARTIFACT_SCHEMA_VERSION).toBe("1");
  });

  it("has a closed UndoStatus set", () => {
    expect(UNDO_STATUSES).toEqual([
      "undone_guard_passed",
      "undone_guard_failed",
      "undo_refused",
      "undo_failed",
    ]);
  });

  it("has a closed UndoFileAction set", () => {
    expect(UNDO_FILE_ACTIONS).toEqual([
      "restored",
      "deleted",
      "refused",
      "failed",
    ]);
  });

  it("validates an undo artifact with restored and deleted outcomes", () => {
    const outcomes: UndoFileOutcome[] = [
      {
        path: "src/example.py",
        changeType: "modify",
        undone: true,
        action: "restored",
        expectedAppliedDigest:
          "sha256:abc123def456",
        observedLiveDigest:
          "sha256:abc123def456",
        priorDigestRestored:
          "sha256:def456abc123",
        reason: "Prior content restored atomically.",
      },
      {
        path: "docs/new-note.txt",
        changeType: "create",
        undone: true,
        action: "deleted",
        expectedAppliedDigest:
          "sha256:111222333444",
        observedLiveDigest:
          "sha256:111222333444",
        priorDigestRestored: null,
        reason: "Created file removed.",
      },
    ];

    const artifact: UndoArtifact = {
      ...baseArtifact,
      fileOutcomes: outcomes,
    };

    expect(artifact.fileOutcomes).toHaveLength(2);
    expect(artifact.fileOutcomes[0]?.action).toBe("restored");
    expect(artifact.fileOutcomes[1]?.action).toBe("deleted");
    expect(artifact.status).toBe("undone_guard_passed");
  });

  it("validates a refused undo artifact", () => {
    const artifact: UndoArtifact = {
      ...baseArtifact,
      status: "undo_refused",
      fileOutcomes: [],
    };

    expect(artifact.status).toBe("undo_refused");
    expect(artifact.fileOutcomes).toHaveLength(0);
  });

  it("validates an undo artifact with post-undo guard", () => {
    const guard: UndoGuardResult = {
      status: "passed",
      blocking: false,
      summary: {
        passedCount: 2,
        failedCount: 0,
        errorCount: 0,
        totalCount: 2,
        isBlocking: false,
      },
      checks: [
        {
          kind: "lint",
          status: "passed",
          blocking: false,
          summary: "Lint passed.",
          exitCode: 0,
          durationMs: 50,
          outputExcerpt: "All checks passed!",
          outputTruncated: false,
        },
      ],
    };

    const artifact: UndoArtifact = {
      ...baseArtifact,
      guard,
      fileOutcomes: [
        {
          path: "src/example.py",
          changeType: "modify",
          undone: true,
          action: "restored",
          expectedAppliedDigest: "sha256:abc",
          observedLiveDigest: "sha256:abc",
          priorDigestRestored: "sha256:def",
          reason: "Restored",
        },
      ],
    };

    expect(artifact.guard?.status).toBe("passed");
    expect(artifact.guard?.checks).toHaveLength(1);
  });

  it("validates guard unavailable reason when guard is null", () => {
    const artifact: UndoArtifact = {
      ...baseArtifact,
      status: "undone_guard_failed",
      guard: null,
      guardUnavailableReason: "Guard config was removed after undo.",
    };

    expect(artifact.guard).toBeNull();
    expect(artifact.guardUnavailableReason).toBeTruthy();
  });

  it("validates undo_failed with partial outcomes", () => {
    const artifact: UndoArtifact = {
      ...baseArtifact,
      status: "undo_failed",
      fileOutcomes: [
        {
          path: "src/example.py",
          changeType: "modify",
          undone: true,
          action: "restored",
          expectedAppliedDigest: "sha256:abc",
          observedLiveDigest: "sha256:abc",
          priorDigestRestored: "sha256:def",
          reason: "Restored",
        },
        {
          path: "docs/new-note.txt",
          changeType: "create",
          undone: false,
          action: "failed",
          expectedAppliedDigest: "sha256:111",
          observedLiveDigest: "sha256:111",
          priorDigestRestored: null,
          reason: "os.unlink failed",
        },
      ],
    };

    expect(artifact.status).toBe("undo_failed");
    expect(artifact.fileOutcomes[0]?.undone).toBe(true);
    expect(artifact.fileOutcomes[1]?.undone).toBe(false);
  });
});
