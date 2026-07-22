import { QueryClient } from "@tanstack/react-query";

export function createStudioQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        staleTime: 5_000,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export const queryKeys = {
  application: (applicationId: string) =>
    ["core", "applications", applicationId] as const,
  backup: (backupId: string) => ["core", "backups", backupId] as const,
  backups: ["core", "backups"] as const,
  changeProposal: (proposalId: string) =>
    ["core", "change-proposals", proposalId] as const,
  changeProposalVerifications: (proposalId: string) =>
    ["core", "change-proposals", proposalId, "verifications"] as const,
  changeProposals: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "change-proposals"] as const,
  contextPack: (workspaceId: string, contextPackId: string) =>
    ["core", "workspaces", workspaceId, "context-packs", contextPackId] as const,
  contextPackCandidates: (workspaceId: string, inventoryId: string) =>
    [
      "core",
      "workspaces",
      workspaceId,
      "context-packs",
      "candidates",
      inventoryId,
    ] as const,
  contextPacks: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "context-packs"] as const,
  guardLatest: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "guard", "runs", "latest"] as const,
  health: ["core", "health"] as const,
  job: (jobId: string) => ["core", "jobs", jobId] as const,
  jobs: ["core", "jobs"] as const,
  providers: ["core", "providers"] as const,
  run: (runId: string) => ["core", "runs", runId] as const,
  task: (taskId: string) => ["core", "tasks", taskId] as const,
  vaultFilePreview: (workspaceId: string, path: string) =>
    ["core", "workspaces", workspaceId, "vault", "files", "content", path] as const,
  vaultFiles: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "vault", "files"] as const,
  vaultIndex: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "vault", "index"] as const,
  vaultInventory: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "vault", "inventory"] as const,
  vaultMemoryItem: (memoryItemId: string) =>
    ["core", "vault", "memory", memoryItemId] as const,
  verification: (verificationId: string) =>
    ["core", "verifications", verificationId] as const,
  undo: (undoId: string) => ["core", "undos", undoId] as const,
  workspaceApplications: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "applications"] as const,
  workspaceUndos: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "undos"] as const,
  workspaceRepository: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "repository"] as const,
  workspaceTasks: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "tasks"] as const,
  workspaces: ["core", "workspaces"] as const,
};
