import type { EntityId, IsoDateTime } from "./domain.js";

export const GUARD_CHECK_KINDS = ["lint", "test"] as const;
export type GuardCheckKind = (typeof GUARD_CHECK_KINDS)[number];

export const GUARD_CHECK_STATUSES = ["passed", "failed", "error"] as const;
export type GuardCheckStatus = (typeof GUARD_CHECK_STATUSES)[number];

export const GUARD_RUN_STATUSES = ["passed", "failed"] as const;
export type GuardRunStatus = (typeof GUARD_RUN_STATUSES)[number];

export interface GuardRunRequest {
  checks?: readonly GuardCheckKind[];
}

export interface GuardCheckResult {
  kind: GuardCheckKind;
  status: GuardCheckStatus;
  blocking: boolean;
  summary: string;
  command: readonly string[];
  exitCode: number | null;
  durationMs: number;
  stdout: string;
  stderr: string;
  outputTruncated: boolean;
}

export interface GuardSummary {
  totalCount: number;
  passedCount: number;
  failedCount: number;
  errorCount: number;
  blockingFailures: number;
  isBlocking: boolean;
}

export interface GuardRunResponse {
  id: EntityId;
  workspaceId: EntityId;
  status: GuardRunStatus;
  blocking: boolean;
  summary: GuardSummary;
  checks: readonly GuardCheckResult[];
  startedAt: IsoDateTime;
  completedAt: IsoDateTime;
  durationMs: number;
}
