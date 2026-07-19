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
  health: ["core", "health"] as const,
  run: (runId: string) => ["core", "runs", runId] as const,
  task: (taskId: string) => ["core", "tasks", taskId] as const,
  workspaces: ["core", "workspaces"] as const,
};
