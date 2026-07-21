import type { ChangeProposalChangeType } from "./change-proposal.js";
import type { ContextPackDigest } from "./context-pack.js";
import type { IsoDateTime } from "./domain.js";
import type {
  GuardCheckKind,
  GuardCheckStatus,
  GuardRunStatus,
  GuardSummary,
} from "./guard.js";

export const UNDO_ARTIFACT_SCHEMA_VERSION = "1" as const;

export const UNDO_STATUSES = [
  "undone_guard_passed",
  "undone_guard_failed",
  "undo_refused",
  "undo_failed",
] as const;
export type UndoStatus = (typeof UNDO_STATUSES)[number];

export const UNDO_FILE_ACTIONS = [
  "restored",
  "deleted",
  "refused",
  "failed",
] as const;
export type UndoFileAction = (typeof UNDO_FILE_ACTIONS)[number];

export interface UndoFileOutcome {
  path: string;
  changeType: ChangeProposalChangeType;
  undone: boolean;
  action: UndoFileAction;
  expectedAppliedDigest: ContextPackDigest | null;
  observedLiveDigest: ContextPackDigest | null;
  priorDigestRestored: ContextPackDigest | null;
  reason: string;
}

export interface UndoGuardCheck {
  kind: GuardCheckKind;
  status: GuardCheckStatus;
  blocking: boolean;
  summary: string;
  exitCode: number | null;
  durationMs: number;
  outputExcerpt: string;
  outputTruncated: boolean;
}

export interface UndoGuardResult {
  status: GuardRunStatus;
  blocking: boolean;
  summary: GuardSummary;
  checks: readonly UndoGuardCheck[];
}

export interface UndoArtifact {
  id: string;
  schemaVersion: typeof UNDO_ARTIFACT_SCHEMA_VERSION;
  applicationId: string;
  proposalId: string;
  workspaceId: string;
  status: UndoStatus;
  fileOutcomes: readonly UndoFileOutcome[];
  guard: UndoGuardResult | null;
  guardUnavailableReason: string | null;
  createdAt: IsoDateTime;
  finishedAt: IsoDateTime;
  durationMs: number;
}

export interface UndoCollection {
  items: readonly UndoArtifact[];
  total: number;
}
