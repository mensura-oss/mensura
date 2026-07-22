import type {
  ApplicationArtifact,
  ApplicationCollection,
  ApplyChangeProposalRequest,
  BackupArtifact,
  BackupCollection,
  ChangeProposal,
  ChangeProposalCollection,
  ContextPackCollection,
  ContextPackManifest,
  CreateBackupRequest,
  CreateWorkspaceRequest,
  CreateTaskRequest,
  CreateContextPackRequest,
  CreateContextPackResponse,
  CreateChangeProposalResponse,
  CreateRunRequest,
  EnqueueJobRequest,
  HealthResponse,
  GuardRunRequest,
  GuardRunResponse,
  Job,
  JobCollection,
  ProblemDetails,
  ProposalVerification,
  ProposalVerificationCollection,
  ProviderCollection,
  ProviderDescriptor,
  ConfigureOpenAIProviderRequest,
  ExecuteRunRequest,
  RepositorySummary,
  RestoreBackupResponse,
  Run,
  Task,
  UndoArtifact,
  UndoCollection,
  VaultArchitectureSummary,
  VaultFileCollection,
  VaultFilePreview,
  VaultIndexSnapshot,
  VaultInventorySnapshot,
  VaultMemoryItemDetail,
  VaultSearchOptions,
  VaultSearchResponse,
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
  createContextPack(
    workspaceId: string,
    input: CreateContextPackRequest,
  ): Promise<CreateContextPackResponse>;
  createChangeProposal(runId: string): Promise<CreateChangeProposalResponse>;
  approveChangeProposal(proposalId: string): Promise<ChangeProposal>;
  rejectChangeProposal(proposalId: string): Promise<ChangeProposal>;
  applyChangeProposal(
    proposalId: string,
    input: ApplyChangeProposalRequest,
  ): Promise<ApplicationArtifact>;
  getApplication(applicationId: string): Promise<ApplicationArtifact>;
  listWorkspaceApplications(workspaceId: string): Promise<ApplicationCollection>;
  undoApplication(applicationId: string): Promise<UndoArtifact>;
  getUndo(undoId: string): Promise<UndoArtifact>;
  listWorkspaceUndos(workspaceId: string): Promise<UndoCollection>;
  createBackup(input?: CreateBackupRequest): Promise<BackupArtifact>;
  listBackups(): Promise<BackupCollection>;
  getBackup(backupId: string): Promise<BackupArtifact>;
  restoreBackup(backupId: string): Promise<RestoreBackupResponse>;
  enqueueJob(input: EnqueueJobRequest): Promise<Job>;
  listJobs(): Promise<JobCollection>;
  getJob(jobId: string): Promise<Job>;
  retryJob(jobId: string): Promise<Job>;
  createRun(taskId: string, input: CreateRunRequest): Promise<Run>;
  executeRun(runId: string, input: ExecuteRunRequest): Promise<Run>;
  configureOpenAIProvider(
    input: ConfigureOpenAIProviderRequest,
  ): Promise<ProviderDescriptor>;
  createGuardRun(
    workspaceId: string,
    input?: GuardRunRequest,
  ): Promise<GuardRunResponse>;
  createTask(input: CreateTaskRequest): Promise<Task>;
  createWorkspace(input: CreateWorkspaceRequest): Promise<Workspace>;
  buildVaultInventory(workspaceId: string): Promise<VaultInventorySnapshot>;
  indexVaultWorkspace(workspaceId: string): Promise<VaultIndexSnapshot>;
  getVaultIndex(workspaceId: string): Promise<VaultIndexSnapshot>;
  searchVault(
    workspaceId: string,
    options: VaultSearchOptions,
  ): Promise<VaultSearchResponse>;
  getVaultMemoryItem(memoryItemId: string): Promise<VaultMemoryItemDetail>;
  summarizeVaultWorkspace(
    workspaceId: string,
  ): Promise<VaultArchitectureSummary>;
  getHealth(): Promise<HealthResponse>;
  getContextPack(
    workspaceId: string,
    contextPackId: string,
  ): Promise<ContextPackManifest>;
  getChangeProposal(proposalId: string): Promise<ChangeProposal>;
  getChangeProposalVerification(
    verificationId: string,
  ): Promise<ProposalVerification>;
  getLatestGuardRun(workspaceId: string): Promise<GuardRunResponse>;
  getRun(runId: string): Promise<Run>;
  getTask(taskId: string): Promise<Task>;
  getVaultFilePreview(workspaceId: string, path: string): Promise<VaultFilePreview>;
  getVaultInventory(workspaceId: string): Promise<VaultInventorySnapshot>;
  getWorkspaceRepository(workspaceId: string): Promise<RepositorySummary>;
  listVaultFiles(
    workspaceId: string,
    options?: { query?: string; extension?: string; limit?: number },
  ): Promise<VaultFileCollection>;
  listContextPacks(workspaceId: string): Promise<ContextPackCollection>;
  listChangeProposals(workspaceId: string): Promise<ChangeProposalCollection>;
  listChangeProposalVerifications(
    proposalId: string,
  ): Promise<ProposalVerificationCollection>;
  listWorkspaces(): Promise<WorkspaceCollection>;
  listProviders(): Promise<ProviderCollection>;
  verifyChangeProposal(proposalId: string): Promise<ProposalVerification>;
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
    approveChangeProposal(proposalId) {
      return request<ChangeProposal>(
        `/api/v1/change-proposals/${encodeURIComponent(proposalId)}/approve`,
        { method: "POST" },
      );
    },
    applyChangeProposal(proposalId, input) {
      return request<ApplicationArtifact>(
        `/api/v1/change-proposals/${encodeURIComponent(proposalId)}/apply`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        },
      );
    },
    getApplication(applicationId) {
      return request<ApplicationArtifact>(
        `/api/v1/applications/${encodeURIComponent(applicationId)}`,
      );
    },
    listWorkspaceApplications(workspaceId) {
      return request<ApplicationCollection>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/applications`,
      );
    },
    undoApplication(applicationId) {
      return request<UndoArtifact>(
        `/api/v1/applications/${encodeURIComponent(applicationId)}/undo`,
        { method: "POST" },
      );
    },
    getUndo(undoId) {
      return request<UndoArtifact>(
        `/api/v1/undos/${encodeURIComponent(undoId)}`,
      );
    },
    listWorkspaceUndos(workspaceId) {
      return request<UndoCollection>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/undos`,
      );
    },
    createBackup(input = {}) {
      return request<BackupArtifact>("/api/v1/backups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
    },
    listBackups() {
      return request<BackupCollection>("/api/v1/backups");
    },
    getBackup(backupId) {
      return request<BackupArtifact>(
        `/api/v1/backups/${encodeURIComponent(backupId)}`,
      );
    },
    restoreBackup(backupId) {
      return request<RestoreBackupResponse>(
        `/api/v1/backups/${encodeURIComponent(backupId)}/restore`,
        { method: "POST" },
      );
    },
    enqueueJob(input) {
      return request<Job>("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
    },
    listJobs() {
      return request<JobCollection>("/api/v1/jobs");
    },
    getJob(jobId) {
      return request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}`);
    },
    retryJob(jobId) {
      return request<Job>(
        `/api/v1/jobs/${encodeURIComponent(jobId)}/retry`,
        { method: "POST" },
      );
    },
    buildVaultInventory(workspaceId) {
      return request<VaultInventorySnapshot>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/vault/inventory`,
        { method: "POST" },
      );
    },
    indexVaultWorkspace(workspaceId) {
      return request<VaultIndexSnapshot>("/api/v1/vault/index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspaceId }),
      });
    },
    getVaultIndex(workspaceId) {
      return request<VaultIndexSnapshot>(
        `/api/v1/vault/indexes/${encodeURIComponent(workspaceId)}`,
      );
    },
    searchVault(workspaceId, options) {
      const body: {
        workspaceId: string;
        query: string;
        limit?: number;
        sourceType?: string;
      } = { workspaceId, query: options.query };
      if (options.limit !== undefined) body.limit = options.limit;
      if (options.sourceType !== undefined) body.sourceType = options.sourceType;
      return request<VaultSearchResponse>("/api/v1/vault/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    },
    getVaultMemoryItem(memoryItemId) {
      return request<VaultMemoryItemDetail>(
        `/api/v1/vault/memory/${encodeURIComponent(memoryItemId)}`,
      );
    },
    summarizeVaultWorkspace(workspaceId) {
      return request<VaultArchitectureSummary>("/api/v1/vault/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspaceId }),
      });
    },
    createGuardRun(workspaceId, input = {}) {
      return request<GuardRunResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/guard/runs`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        },
      );
    },
    createContextPack(workspaceId, input) {
      return request<CreateContextPackResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/context-packs`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        },
      );
    },
    createChangeProposal(runId) {
      return request<CreateChangeProposalResponse>(
        `/api/v1/runs/${encodeURIComponent(runId)}/change-proposals`,
        { method: "POST" },
      );
    },
    createRun(taskId, input) {
      return request<Run>(
        `/api/v1/tasks/${encodeURIComponent(taskId)}/runs`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        },
      );
    },
    createTask(input) {
      return request<Task>("/api/v1/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
    },
    executeRun(runId, input) {
      return request<Run>(
        `/api/v1/runs/${encodeURIComponent(runId)}/execute`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        },
      );
    },
    configureOpenAIProvider(input) {
      return request<ProviderDescriptor>("/api/v1/providers/openai/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
    },
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
    getContextPack(workspaceId, contextPackId) {
      return request<ContextPackManifest>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/context-packs/${encodeURIComponent(contextPackId)}`,
      );
    },
    getChangeProposal(proposalId) {
      return request<ChangeProposal>(
        `/api/v1/change-proposals/${encodeURIComponent(proposalId)}`,
      );
    },
    getChangeProposalVerification(verificationId) {
      return request<ProposalVerification>(
        `/api/v1/verifications/${encodeURIComponent(verificationId)}`,
      );
    },
    getLatestGuardRun(workspaceId) {
      return request<GuardRunResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/guard/runs/latest`,
      );
    },
    getRun(runId) {
      return request<Run>(`/api/v1/runs/${encodeURIComponent(runId)}`);
    },
    getTask(taskId) {
      return request<Task>(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
    },
    getVaultFilePreview(workspaceId, path) {
      const search = new URLSearchParams({ path });
      return request<VaultFilePreview>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/vault/files/content?${search.toString()}`,
      );
    },
    getVaultInventory(workspaceId) {
      return request<VaultInventorySnapshot>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/vault/inventory`,
      );
    },
    getWorkspaceRepository(workspaceId) {
      return request<RepositorySummary>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/repository`,
      );
    },
    listWorkspaces() {
      return request<WorkspaceCollection>("/api/v1/workspaces");
    },
    listProviders() {
      return request<ProviderCollection>("/api/v1/providers");
    },
    listContextPacks(workspaceId) {
      return request<ContextPackCollection>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/context-packs`,
      );
    },
    listChangeProposals(workspaceId) {
      return request<ChangeProposalCollection>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/change-proposals`,
      );
    },
    listChangeProposalVerifications(proposalId) {
      return request<ProposalVerificationCollection>(
        `/api/v1/change-proposals/${encodeURIComponent(proposalId)}/verifications`,
      );
    },
    listVaultFiles(workspaceId, options = {}) {
      const search = new URLSearchParams();
      if (options.query) search.set("query", options.query);
      if (options.extension) search.set("extension", options.extension);
      if (options.limit !== undefined) search.set("limit", String(options.limit));
      const suffix = search.size ? `?${search.toString()}` : "";
      return request<VaultFileCollection>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/vault/files${suffix}`,
      );
    },
    rejectChangeProposal(proposalId) {
      return request<ChangeProposal>(
        `/api/v1/change-proposals/${encodeURIComponent(proposalId)}/reject`,
        { method: "POST" },
      );
    },
    verifyChangeProposal(proposalId) {
      return request<ProposalVerification>(
        `/api/v1/change-proposals/${encodeURIComponent(proposalId)}/verify`,
        { method: "POST" },
      );
    },
  };
}

export const coreClient = createCoreClient();
