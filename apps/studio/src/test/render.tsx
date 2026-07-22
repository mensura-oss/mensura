import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

import { CoreClientProvider } from "../api/CoreClientProvider";
import type { CoreClient } from "../api/coreClient";

export function createTestClient(
  overrides: Partial<CoreClient> = {},
): CoreClient {
  return {
    baseUrl: "http://127.0.0.1:8000",
    applyChangeProposal: () => Promise.reject(new Error("Not implemented in test")),
    approveChangeProposal: () => Promise.reject(new Error("Not implemented in test")),
    buildVaultInventory: () => Promise.reject(new Error("Not implemented in test")),
    getApplication: () => Promise.reject(new Error("Not implemented in test")),
    listWorkspaceApplications: () => Promise.resolve({ items: [], total: 0 }),
    undoApplication: () => Promise.reject(new Error("Not implemented in test")),
    getUndo: () => Promise.reject(new Error("Not implemented in test")),
    listWorkspaceUndos: () => Promise.resolve({ items: [], total: 0 }),
    createBackup: () => Promise.reject(new Error("Not implemented in test")),
    listBackups: () => Promise.reject(new Error("Not implemented in test")),
    getBackup: () => Promise.reject(new Error("Not implemented in test")),
    restoreBackup: () => Promise.reject(new Error("Not implemented in test")),
    enqueueJob: () => Promise.reject(new Error("Not implemented in test")),
    listJobs: () => Promise.resolve({ items: [], total: 0 }),
    getJob: () => Promise.reject(new Error("Not implemented in test")),
    retryJob: () => Promise.reject(new Error("Not implemented in test")),
    configureOpenAIProvider: () =>
      Promise.reject(new Error("Not implemented in test")),
    createContextPack: () => Promise.reject(new Error("Not implemented in test")),
    createChangeProposal: () => Promise.reject(new Error("Not implemented in test")),
    createGuardRun: () => Promise.reject(new Error("Not implemented in test")),
    createRun: () => Promise.reject(new Error("Not implemented in test")),
    createTask: () => Promise.reject(new Error("Not implemented in test")),
    createWorkspace: () => Promise.reject(new Error("Not implemented in test")),
    executeRun: () => Promise.reject(new Error("Not implemented in test")),
    getHealth: () => Promise.reject(new Error("Not implemented in test")),
    getContextPack: () => Promise.reject(new Error("Not implemented in test")),
    getChangeProposal: () => Promise.reject(new Error("Not implemented in test")),
    getChangeProposalVerification: () =>
      Promise.reject(new Error("Not implemented in test")),
    getLatestGuardRun: () => Promise.reject(new Error("Not implemented in test")),
    getRun: () => Promise.reject(new Error("Not implemented in test")),
    getTask: () => Promise.reject(new Error("Not implemented in test")),
    getVaultFilePreview: () => Promise.reject(new Error("Not implemented in test")),
    getVaultInventory: () => Promise.reject(new Error("Not implemented in test")),
    indexVaultWorkspace: () => Promise.reject(new Error("Not implemented in test")),
    getVaultIndex: () => Promise.reject(new Error("Not implemented in test")),
    searchVault: () => Promise.reject(new Error("Not implemented in test")),
    getVaultMemoryItem: () => Promise.reject(new Error("Not implemented in test")),
    summarizeVaultWorkspace: () =>
      Promise.reject(new Error("Not implemented in test")),
    getWorkspaceRepository: () =>
      Promise.reject(new Error("Not implemented in test")),
    listContextPacks: () => Promise.reject(new Error("Not implemented in test")),
    listChangeProposals: () => Promise.resolve({ items: [], total: 0 }),
    listChangeProposalVerifications: () => Promise.resolve({ items: [], total: 0 }),
    listProviders: () => Promise.resolve({
      items: [
        {
          id: "mensura.builtin",
          name: "Deterministic review",
          kind: "deterministic",
          configured: true,
          model: null,
          promptVersion: "review.v2",
        },
        {
          id: "openai",
          name: "OpenAI",
          kind: "real",
          configured: false,
          model: null,
          promptVersion: "review.v2",
        },
      ],
      total: 2,
    }),
    listWorkspaces: () => Promise.reject(new Error("Not implemented in test")),
    listVaultFiles: () => Promise.reject(new Error("Not implemented in test")),
    rejectChangeProposal: () => Promise.reject(new Error("Not implemented in test")),
    verifyChangeProposal: () => Promise.reject(new Error("Not implemented in test")),
    ...overrides,
  };
}

export function renderWithAppProviders(
  ui: ReactElement,
  client: CoreClient,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <CoreClientProvider client={client}>{ui}</CoreClientProvider>
    </QueryClientProvider>,
    options,
  );
}
