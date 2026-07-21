import type { IsoDateTime } from "./domain.js";

export const BACKUP_ARTIFACT_SCHEMA_VERSION = "1" as const;

export const BACKUP_STATUSES = ["completed", "failed"] as const;
export type BackupStatus = (typeof BACKUP_STATUSES)[number];

export interface BackupArtifact {
  id: string;
  schemaVersion: typeof BACKUP_ARTIFACT_SCHEMA_VERSION;
  createdAt: IsoDateTime;
  dbVersion: string | null;
  fileSizeBytes: number;
  sha256Hex: string;
  storagePath: string;
  status: BackupStatus;
  label: string | null;
  errorMessage: string | null;
}

export interface CreateBackupRequest {
  label?: string | null;
}

export interface BackupCollection {
  items: readonly BackupArtifact[];
  total: number;
}

export interface RestoreBackupResponse {
  message: string;
}
