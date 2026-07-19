import type { Workspace } from "./domain.js";

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
