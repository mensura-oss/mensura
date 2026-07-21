import type { EntityId, IsoDateTime } from "./domain.js";

export const JOB_SCHEMA_VERSION = "1" as const;

export const JOB_STATUSES = [
  "queued",
  "running",
  "succeeded",
  "failed",
] as const;
export type JobStatus = (typeof JOB_STATUSES)[number];

export const JOB_TYPES = [
  "proposal_verification",
  "application_apply",
  "application_undo",
  "backup_create",
] as const;
export type JobType = (typeof JOB_TYPES)[number];

export const JOB_TARGET_TYPES = [
  "change_proposal",
  "application",
  "database",
] as const;
export type JobTargetType = (typeof JOB_TARGET_TYPES)[number];

/**
 * Bounded reference data a job needs to execute. Never contains artifact
 * bodies, file contents, diffs, or patches — only identifiers and a label.
 */
export interface JobPayload {
  proposalId: EntityId | null;
  verificationId: EntityId | null;
  applicationId: EntityId | null;
  label: string | null;
}

/**
 * A durable, persisted unit of orchestration. A job runs an existing
 * long-running operation (verify/apply/undo/backup) asynchronously and records
 * its lifecycle. Job success means the operation ran to completion and produced
 * its artifact; the artifact's own status still records the domain outcome.
 */
export interface Job {
  id: EntityId;
  schemaVersion: typeof JOB_SCHEMA_VERSION;
  jobType: JobType;
  targetEntityType: JobTargetType;
  targetEntityId: EntityId | null;
  workspaceId: EntityId | null;
  status: JobStatus;
  attemptCount: number;
  payload: JobPayload;
  resultEntityType: string | null;
  resultEntityId: EntityId | null;
  lastError: string | null;
  createdAt: IsoDateTime;
  startedAt: IsoDateTime | null;
  finishedAt: IsoDateTime | null;

  /** If this job is a retry, the id of the job it was created from. */
  retryOfJobId: EntityId | null;
  /** The original (root) job in a retry chain, or this job itself if it's the root. */
  rootJobId: EntityId | null;
  /** Whether this failed job is eligible for explicit user-initiated retry. */
  retryEligible: boolean;
  /** How many explicit retry children have been spawned from this job. */
  retryCount: number;
}

export interface JobCollection {
  items: readonly Job[];
  total: number;
}

export interface EnqueueVerificationJobRequest {
  jobType: "proposal_verification";
  proposalId: EntityId;
}

export interface EnqueueApplyJobRequest {
  jobType: "application_apply";
  proposalId: EntityId;
  verificationId: EntityId;
}

export interface EnqueueUndoJobRequest {
  jobType: "application_undo";
  applicationId: EntityId;
}

export interface EnqueueBackupJobRequest {
  jobType: "backup_create";
  label?: string | null;
}

export type EnqueueJobRequest =
  | EnqueueVerificationJobRequest
  | EnqueueApplyJobRequest
  | EnqueueUndoJobRequest
  | EnqueueBackupJobRequest;
