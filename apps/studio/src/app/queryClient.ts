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
  run: (runId: string) => ["core", "runs", runId] as const,
  task: (taskId: string) => ["core", "tasks", taskId] as const,
  vaultFilePreview: (workspaceId: string, path: string) =>
    ["core", "workspaces", workspaceId, "vault", "files", "content", path] as const,
  vaultFiles: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "vault", "files"] as const,
  vaultInventory: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "vault", "inventory"] as const,
  workspaceRepository: (workspaceId: string) =>
    ["core", "workspaces", workspaceId, "repository"] as const,
  workspaces: ["core", "workspaces"] as const,
};
