import type { ChangeProposalChangeType } from "./change-proposal.js";
import type { ContextPackDigest } from "./context-pack.js";
import type { IsoDateTime } from "./domain.js";
import type {
  GuardCheckKind,
  GuardCheckStatus,
  GuardRunStatus,
  GuardSummary,
} from "./guard.js";

export const APPLICATION_ARTIFACT_SCHEMA_VERSION = "1" as const;

/**
 * Closed set of persisted application outcomes. An artifact exists only when the
 * live working tree was actually written; pre-write refusals are RFC 9457
 * problems instead. Guard failure after apply is never hidden.
 */
export const APPLICATION_STATUSES = [
  "applied_guard_passed",
  "applied_guard_failed",
  "applied_guard_unavailable",
  "application_failed",
] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

export const APPLICATION_TARGET_KINDS = ["live_working_tree"] as const;
export type ApplicationTargetKind = (typeof APPLICATION_TARGET_KINDS)[number];

export const APPLIED_FILE_REASONS = [
  "applied",
  "write_failed",
  "not_attempted",
] as const;
export type AppliedFileReason = (typeof APPLIED_FILE_REASONS)[number];

export const APPLICATION_UNDO_STRATEGIES = ["restore_prior_content"] as const;
export type ApplicationUndoStrategy =
  (typeof APPLICATION_UNDO_STRATEGIES)[number];

export const APPLICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS = 2_000;
export const APPLICATION_UNDO_CONTENT_MAX_BYTES_PER_FILE = 65_536;

/** Safe live-target provenance without exposing absolute filesystem paths. */
export interface ApplicationTargetMetadata {
  kind: ApplicationTargetKind;
  liveCommitId: string;
  verificationCommitId: string;
  headMovedSinceVerification: boolean;
}

export interface AppliedFileResult {
  path: string;
  changeType: ChangeProposalChangeType;
  /** Expected pre-apply digest captured with the proposal (null for create). */
  beforeDigest: ContextPackDigest | null;
  /** Digest observed on the live tree immediately before writing. */
  liveBeforeDigest: ContextPackDigest | null;
  /** Expected post-apply digest from the verified proposal (null for delete). */
  afterDigest: ContextPackDigest | null;
  /** Digest of the bytes actually written (null for delete / unwritten). */
  appliedDigest: ContextPackDigest | null;
  applied: boolean;
  reason: AppliedFileReason;
}

export interface ApplicationGuardCheck {
  kind: GuardCheckKind;
  status: GuardCheckStatus;
  blocking: boolean;
  summary: string;
  exitCode: number | null;
  durationMs: number;
  outputExcerpt: string;
  outputTruncated: boolean;
}

export interface ApplicationGuardResult {
  status: GuardRunStatus;
  blocking: boolean;
  summary: GuardSummary;
  checks: readonly ApplicationGuardCheck[];
}

export interface ApplicationSummary {
  filesTotal: number;
  createdCount: number;
  modifiedCount: number;
  deletedCount: number;
  appliedCount: number;
  failedCount: number;
}

/**
 * Bounded per-file restoration basis for a future undo feature. Undo execution
 * is intentionally not implemented yet.
 */
export interface ApplicationUndoFileEntry {
  path: string;
  changeType: ChangeProposalChangeType;
  priorExisted: boolean;
  priorDigest: ContextPackDigest | null;
  priorContent: string | null;
  priorContentBytes: number;
  priorTruncated: boolean;
  appliedDigest: ContextPackDigest | null;
}

export interface ApplicationUndoMetadata {
  strategy: ApplicationUndoStrategy;
  note: string;
  capturedAt: IsoDateTime;
  files: readonly ApplicationUndoFileEntry[];
}

export interface ApplicationArtifact {
  id: string;
  schemaVersion: typeof APPLICATION_ARTIFACT_SCHEMA_VERSION;
  proposalId: string;
  verificationId: string;
  runId: string;
  taskId: string;
  workspaceId: string;
  contextPackId: ContextPackDigest;
  status: ApplicationStatus;
  target: ApplicationTargetMetadata;
  guard: ApplicationGuardResult | null;
  guardUnavailableReason: string | null;
  fileResults: readonly AppliedFileResult[];
  summary: ApplicationSummary;
  undo: ApplicationUndoMetadata;
  createdAt: IsoDateTime;
  finishedAt: IsoDateTime;
  durationMs: number;
}

export interface ApplicationCollection {
  items: readonly ApplicationArtifact[];
  total: number;
}

export interface ApplyChangeProposalRequest {
  verificationId: string;
}
