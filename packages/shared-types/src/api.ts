import type { AgentRole, Workspace } from "./domain.js";
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
