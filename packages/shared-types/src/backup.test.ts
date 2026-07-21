import { describe, expect, it } from "vitest";
import {
  BACKUP_ARTIFACT_SCHEMA_VERSION,
  BACKUP_STATUSES,
} from "./backup.js";
import type {
  BackupArtifact,
  BackupCollection,
} from "./backup.js";

describe("Backup contracts", () => {
  const baseArtifact: BackupArtifact = {
    id: "a1b2c3d4-e5f6-7890-abcd-ef0123456789",
    schemaVersion: "1",
    createdAt: "2026-07-20T12:00:00Z",
    dbVersion: "abc123def",
    fileSizeBytes: 1024,
    sha256Hex: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    storagePath: "backup-2026-07-20T120000Z-a1b2c3d4.db",
    status: "completed",
    label: "before migration",
    errorMessage: null,
  };

  it("pins BACKUP_ARTIFACT_SCHEMA_VERSION to 1", () => {
    expect(BACKUP_ARTIFACT_SCHEMA_VERSION).toBe("1");
  });

  it("has a closed BackupStatus set", () => {
    expect(BACKUP_STATUSES).toEqual(["completed", "failed"]);
  });

  it("validates a completed backup artifact", () => {
    expect(baseArtifact.status).toBe("completed");
    expect(baseArtifact.sha256Hex).toHaveLength(64);
    expect(baseArtifact.fileSizeBytes).toBe(1024);
  });

  it("validates a failed backup artifact", () => {
    const artifact: BackupArtifact = {
      ...baseArtifact,
      status: "failed",
      sha256Hex: "",
      fileSizeBytes: 0,
      storagePath: "",
      errorMessage: "Database connection lost during backup.",
    };

    expect(artifact.status).toBe("failed");
    expect(artifact.sha256Hex).toBe("");
    expect(artifact.fileSizeBytes).toBe(0);
    expect(artifact.errorMessage).toBeTruthy();
  });

  it("validates backup without label", () => {
    const artifact: BackupArtifact = {
      ...baseArtifact,
      label: null,
    };

    expect(artifact.label).toBeNull();
  });

  it("validates backup without dbVersion", () => {
    const artifact: BackupArtifact = {
      ...baseArtifact,
      dbVersion: null,
    };

    expect(artifact.dbVersion).toBeNull();
  });

  it("validates an empty backup collection", () => {
    const collection: BackupCollection = {
      items: [],
      total: 0,
    };

    expect(collection.items).toHaveLength(0);
    expect(collection.total).toBe(0);
  });

  it("validates a populated backup collection", () => {
    const collection: BackupCollection = {
      items: [baseArtifact],
      total: 1,
    };

    expect(collection.items[0]?.id).toBe(baseArtifact.id);
    expect(collection.total).toBe(1);
  });
});
