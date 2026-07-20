import type { ChangeProposalChangeType } from "./change-proposal.js";
import type { ContextPackDigest } from "./context-pack.js";
import type { IsoDateTime } from "./domain.js";
import type {
  GuardCheckKind,
  GuardCheckStatus,
  GuardRunStatus,
  GuardSummary,
} from "./guard.js";

export const PROPOSAL_VERIFICATION_SCHEMA_VERSION = "1" as const;

export const PROPOSAL_VERIFICATION_STATUSES = ["passed", "failed"] as const;
export type ProposalVerificationStatus =
  (typeof PROPOSAL_VERIFICATION_STATUSES)[number];

export const PROPOSAL_VERIFICATION_OUTCOMES = [
  "sandbox_verified",
  "guard_failed",
  "materialization_failed",
] as const;
export type ProposalVerificationOutcome =
  (typeof PROPOSAL_VERIFICATION_OUTCOMES)[number];

export const VERIFICATION_SANDBOX_KINDS = ["git_worktree"] as const;
export type VerificationSandboxKind =
  (typeof VERIFICATION_SANDBOX_KINDS)[number];

export const FILE_VERIFICATION_REASONS = [
  "applied",
  "create_target_exists",
  "target_missing",
  "target_not_a_file",
  "before_content_mismatch",
  "unsafe_path",
] as const;
export type FileVerificationReason =
  (typeof FILE_VERIFICATION_REASONS)[number];

export const VERIFICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS = 2_000;

/** Safe sandbox provenance without exposing temporary filesystem paths. */
export interface VerificationSandboxMetadata {
  kind: VerificationSandboxKind;
  commitId: string;
  cleanupCompleted: boolean;
}

export interface FileVerificationResult {
  path: string;
  changeType: ChangeProposalChangeType;
  beforeDigest: ContextPackDigest | null;
  afterDigest: ContextPackDigest | null;
  sandboxDigest: ContextPackDigest | null;
  appliedInSandbox: boolean;
  reason: FileVerificationReason;
}

export interface VerificationGuardCheck {
  kind: GuardCheckKind;
  status: GuardCheckStatus;
  blocking: boolean;
  summary: string;
  exitCode: number | null;
  durationMs: number;
  outputExcerpt: string;
  outputTruncated: boolean;
}

export interface VerificationGuardResult {
  status: GuardRunStatus;
  blocking: boolean;
  summary: GuardSummary;
  checks: readonly VerificationGuardCheck[];
}

export interface SafeDiffMetadata {
  filesTotal: number;
  createdCount: number;
  modifiedCount: number;
  deletedCount: number;
  appliedCount: number;
  unappliedCount: number;
  proposedBytesTotal: number;
}

export interface ProposalVerification {
  id: string;
  schemaVersion: typeof PROPOSAL_VERIFICATION_SCHEMA_VERSION;
  proposalId: string;
  runId: string;
  taskId: string;
  workspaceId: string;
  contextPackId: ContextPackDigest;
  status: ProposalVerificationStatus;
  outcome: ProposalVerificationOutcome;
  sandbox: VerificationSandboxMetadata;
  guard: VerificationGuardResult | null;
  fileResults: readonly FileVerificationResult[];
  safeDiff: SafeDiffMetadata;
  createdAt: IsoDateTime;
  finishedAt: IsoDateTime;
  durationMs: number;
}

export interface ProposalVerificationCollection {
  items: readonly ProposalVerification[];
  total: number;
}
