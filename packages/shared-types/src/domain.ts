import type {
  ContextPackDigest,
  ContextPackReference,
} from "./context-pack.js";

export type EntityId = string;
export type IsoDateTime = string;

export const AGENT_ROLES = [
  "architect",
  "research",
  "coder",
  "refactor",
  "test",
  "reviewer",
  "security",
  "devops",
  "docs",
  "release",
] as const;

export type AgentRole = (typeof AGENT_ROLES)[number];

export interface Workspace {
  id: EntityId;
  name: string;
  rootPath: string;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
}

export const TASK_STATUSES = [
  "draft",
  "ready",
  "running",
  "review",
  "approved",
  "rejected",
  "failed",
  "cancelled",
] as const;

export type TaskStatus = (typeof TASK_STATUSES)[number];

export interface Task {
  id: EntityId;
  workspaceId: EntityId;
  projectId?: EntityId;
  title: string;
  description: string;
  status: TaskStatus;
  assignedRole?: AgentRole | null;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
}

export const RUN_STATUSES = [
  "queued",
  "planning",
  "executing",
  "checking",
  "awaiting_approval",
  "completed",
  "failed",
  "cancelled",
] as const;

export type RunStatus = (typeof RUN_STATUSES)[number];

export interface Run {
  id: EntityId;
  taskId: EntityId;
  contextPackId: ContextPackDigest;
  contextPack: ContextPackReference;
  status: RunStatus;
  startedAt?: IsoDateTime | null;
  finishedAt?: IsoDateTime | null;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
}

export const CHECK_KINDS = [
  "format",
  "lint",
  "unit_test",
  "integration_test",
  "secret_scan",
  "dependency_scan",
  "risk_score",
  "approval",
] as const;

export type CheckKind = (typeof CHECK_KINDS)[number];
export type CheckStatus = "passed" | "failed" | "error" | "skipped";

export interface CheckResult {
  id: EntityId;
  runId: EntityId;
  kind: CheckKind;
  status: CheckStatus;
  blocking: boolean;
  summary: string;
  details?: string;
  command?: string;
  durationMs?: number;
  createdAt: IsoDateTime;
}

export interface AgentResult {
  taskSummary: string;
  actionsTaken: readonly string[];
  filesChanged: readonly string[];
  rationale: string;
  knownRisks: readonly string[];
  nextSuggestedStep: string;
}
