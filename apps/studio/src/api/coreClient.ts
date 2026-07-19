import type {
  CreateWorkspaceRequest,
  HealthResponse,
  ProblemDetails,
  Run,
  Task,
  Workspace,
  WorkspaceCollection,
} from "@mensura/shared-types";
import { isTauri } from "@tauri-apps/api/core";
import { fetch as tauriFetch } from "@tauri-apps/plugin-http";

export type CoreFetcher = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export interface CoreClient {
  readonly baseUrl: string;
  createWorkspace(input: CreateWorkspaceRequest): Promise<Workspace>;
  getHealth(): Promise<HealthResponse>;
  getRun(runId: string): Promise<Run>;
  getTask(taskId: string): Promise<Task>;
  listWorkspaces(): Promise<WorkspaceCollection>;
}

export class CoreApiError extends Error {
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title);
    this.name = "CoreApiError";
    this.problem = problem;
  }
}

function runtimeFetch(input: RequestInfo | URL, init?: RequestInit) {
  if (isTauri()) {
    return tauriFetch(input, init);
  }

  return globalThis.fetch(input, init);
}

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.trim().replace(/\/+$/, "");
}

function isProblemDetails(value: unknown): value is ProblemDetails {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.type === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.status === "number"
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

export function createCoreClient(options?: {
  baseUrl?: string;
  fetcher?: CoreFetcher;
}): CoreClient {
  const baseUrl = normalizeBaseUrl(
    options?.baseUrl ??
      import.meta.env.VITE_MENSURA_CORE_URL ??
      "http://127.0.0.1:8000",
  );
  const fetcher = options?.fetcher ?? runtimeFetch;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;

    try {
      response = await fetcher(`${baseUrl}${path}`, init);
    } catch (cause) {
      throw new Error(`Could not connect to Mensura Core at ${baseUrl}.`, {
        cause,
      });
    }

    const payload = await readJson(response);

    if (!response.ok) {
      if (isProblemDetails(payload)) {
        throw new CoreApiError(payload);
      }

      throw new CoreApiError({
        type: "about:blank",
        title: response.statusText || "Core request failed",
        status: response.status,
        detail: `Mensura Core returned HTTP ${response.status} without a valid Problem Details body.`,
        instance: path,
      });
    }

    return payload as T;
  }

  return {
    baseUrl,
    createWorkspace(input) {
      return request<Workspace>("/api/v1/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
    },
    getHealth() {
      return request<HealthResponse>("/health");
    },
    getRun(runId) {
      return request<Run>(`/api/v1/runs/${encodeURIComponent(runId)}`);
    },
    getTask(taskId) {
      return request<Task>(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
    },
    listWorkspaces() {
      return request<WorkspaceCollection>("/api/v1/workspaces");
    },
  };
}

export const coreClient = createCoreClient();
