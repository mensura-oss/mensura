import type {
  AgentRole,
  IsoDateTime,
  RunStatus,
  Task,
  Workspace,
} from "./domain.js";
import type { ContextPackDigest } from "./context-pack.js";

export interface HealthResponse {
  status: "ok";
  service: "mensura-core";
  version: string;
}

export interface WorkspaceCollection {
  items: readonly Workspace[];
  total: number;
}

export interface CreateWorkspaceRequest {
  name: string;
  rootPath: string;
}

export interface CreateTaskRequest {
  workspaceId: string;
  title: string;
  description: string;
  assignedRole?: AgentRole;
}

/** Compact latest-run status for a task, for workspace board/list views. */
export interface TaskRunSummary {
  id: string;
  status: RunStatus;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
}

/** A workspace task plus its latest run's compact status, for board/list views. */
export interface TaskSummary extends Task {
  latestRun: TaskRunSummary | null;
}

export interface TaskCollection {
  items: readonly TaskSummary[];
  total: number;
}

export interface CreateRunRequest {
  contextPackId: ContextPackDigest;
}

export interface ProblemFieldError {
  detail: string;
  pointer: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  errors?: readonly ProblemFieldError[];
}
