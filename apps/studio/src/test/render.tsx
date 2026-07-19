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
    createGuardRun: () => Promise.reject(new Error("Not implemented in test")),
    createRun: () => Promise.reject(new Error("Not implemented in test")),
    createTask: () => Promise.reject(new Error("Not implemented in test")),
    createWorkspace: () => Promise.reject(new Error("Not implemented in test")),
    getHealth: () => Promise.reject(new Error("Not implemented in test")),
    getLatestGuardRun: () => Promise.reject(new Error("Not implemented in test")),
    getRun: () => Promise.reject(new Error("Not implemented in test")),
    getTask: () => Promise.reject(new Error("Not implemented in test")),
    getWorkspaceRepository: () =>
      Promise.reject(new Error("Not implemented in test")),
    listWorkspaces: () => Promise.reject(new Error("Not implemented in test")),
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
