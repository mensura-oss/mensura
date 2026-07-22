import type {
  VaultArchitectureSummary,
  VaultIndexSnapshot,
  VaultMemoryItemDetail,
  VaultSearchResponse,
} from "@mensura/shared-types";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { VaultIndexPanel } from "./VaultIndexPanel";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const indexId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";
const memoryItemId = "8f2b6d4a-1c3e-4f5a-9b7c-0d1e2f3a4b5c";
const chunkId = "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e";

const snapshot: VaultIndexSnapshot = {
  id: indexId,
  workspaceId,
  status: "ready",
  indexedAt: "2026-07-21T13:00:00Z",
  summary: {
    memoryItemCount: 3,
    chunkCount: 12,
    codeFileCount: 1,
    docFileCount: 1,
    configFileCount: 1,
    totalSizeBytes: 2048,
    skippedCount: 1,
    skippedByReason: [{ value: "empty", count: 1 }],
    languages: [{ value: "Python", count: 1 }],
    skippedSample: [{ path: "empty.py", reason: "empty" }],
  },
};

const searchResponse: VaultSearchResponse = {
  workspaceId,
  indexId,
  query: "authenticate password",
  strategy: "lexical-vector-cosine",
  total: 2,
  returned: 1,
  hits: [
    {
      memoryItemId,
      chunkId,
      path: "src/auth.py",
      sourceType: "code",
      language: "Python",
      chunkIndex: 0,
      startLine: 1,
      endLine: 2,
      score: 0.873421,
      snippet: "def authenticate(username, password):",
    },
  ],
};

const memoryDetail: VaultMemoryItemDetail = {
  item: {
    id: memoryItemId,
    workspaceId,
    indexId,
    path: "src/auth.py",
    sourceType: "code",
    language: "Python",
    digest: `sha256:${"a".repeat(64)}`,
    sizeBytes: 96,
    chunkCount: 1,
    indexedAt: "2026-07-21T13:00:00Z",
  },
  chunks: [
    {
      id: chunkId,
      memoryItemId,
      chunkIndex: 0,
      startLine: 1,
      endLine: 2,
      charCount: 64,
      digest: `sha256:${"b".repeat(64)}`,
      text: "def authenticate(username, password):\n    return verify(username, password)\n",
    },
  ],
};

const architecture: VaultArchitectureSummary = {
  workspaceId,
  indexId,
  generatedAt: "2026-07-21T13:00:00Z",
  fileCount: 3,
  codeFileCount: 1,
  docFileCount: 1,
  configFileCount: 1,
  totalSizeBytes: 2048,
  languages: [{ value: "Python", count: 1 }],
  modules: [
    { name: "src", path: "src", fileCount: 1, totalSizeBytes: 96, primaryLanguage: "Python" },
    { name: "docs", path: "docs", fileCount: 1, totalSizeBytes: 40, primaryLanguage: "Markdown" },
  ],
  technologies: ["Python"],
  entryPoints: [],
};

function notBuiltProblem() {
  return new CoreApiError({
    type: "urn:mensura:problem:vault-index-not-built",
    title: "Vault index not built",
    status: 404,
    detail: "No Vault index exists for this workspace. Index the workspace first.",
  });
}

describe("VaultIndexPanel", () => {
  it("guides the user without requesting Core when no workspace is active", () => {
    const getVaultIndex = vi.fn(() => Promise.resolve(snapshot));
    const client = createTestClient({ getVaultIndex });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={null} />, client);

    expect(
      screen.getByText("Select an active workspace to index and search its Vault memory."),
    ).toBeVisible();
    expect(getVaultIndex).not.toHaveBeenCalled();
  });

  it("treats an absent index as a neutral not-indexed state", async () => {
    const client = createTestClient({
      getVaultIndex: () => Promise.reject(notBuiltProblem()),
    });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={workspaceId} />, client);

    expect(
      await screen.findByText(
        /This workspace is not indexed yet\. Index it to enable search/,
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Index workspace" })).toBeVisible();
    expect(screen.queryByText("Vault index not built")).not.toBeInTheDocument();
  });

  it("indexes the workspace and then shows an indexed status with counts", async () => {
    const user = userEvent.setup();
    let resolveIndex!: (value: VaultIndexSnapshot) => void;
    const indexVaultWorkspace = vi.fn(
      () =>
        new Promise<VaultIndexSnapshot>((resolve) => {
          resolveIndex = resolve;
        }),
    );
    const client = createTestClient({
      getVaultIndex: () => Promise.reject(notBuiltProblem()),
      indexVaultWorkspace,
    });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={workspaceId} />, client);
    await user.click(await screen.findByRole("button", { name: "Index workspace" }));

    expect(screen.getByRole("button", { name: "Indexing…" })).toBeDisabled();
    expect(screen.getByText(/reading and chunking workspace files/)).toBeVisible();

    resolveIndex(snapshot);

    expect(await screen.findByRole("button", { name: "Re-index" })).toBeVisible();
    expect(screen.getByText("Indexed")).toBeVisible();
    expect(within(screen.getByText("Memory items").parentElement!).getByText("3")).toBeVisible();
    expect(within(screen.getByText("Chunks").parentElement!).getByText("12")).toBeVisible();
    expect(indexVaultWorkspace).toHaveBeenCalledWith(workspaceId);
  });

  it("renders ranked search results with path, line range, and snippet", async () => {
    const user = userEvent.setup();
    const searchVault = vi.fn(() => Promise.resolve(searchResponse));
    const client = createTestClient({
      getVaultIndex: () => Promise.resolve(snapshot),
      searchVault,
    });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={workspaceId} />, client);

    const input = await screen.findByLabelText("Vault search query");
    await user.type(input, "authenticate password");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("src/auth.py")).toBeVisible();
    expect(screen.getByText("def authenticate(username, password):")).toBeVisible();
    expect(screen.getByText(/^lines 1.2$/)).toBeVisible();
    expect(screen.getByText("#1")).toBeVisible();
    expect(searchVault).toHaveBeenCalledWith(workspaceId, {
      query: "authenticate password",
      limit: 20,
    });
  });

  it("opens the chunk detail for a search result (file navigation)", async () => {
    const user = userEvent.setup();
    const getVaultMemoryItem = vi.fn(() => Promise.resolve(memoryDetail));
    const client = createTestClient({
      getVaultIndex: () => Promise.resolve(snapshot),
      searchVault: () => Promise.resolve(searchResponse),
      getVaultMemoryItem,
    });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={workspaceId} />, client);

    const input = await screen.findByLabelText("Vault search query");
    await user.type(input, "authenticate");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await user.click(await screen.findByRole("button", { name: /src\/auth\.py/ }));

    expect(getVaultMemoryItem).toHaveBeenCalledWith(memoryItemId);
    expect(await screen.findByText(/return verify\(username, password\)/)).toBeVisible();
    expect(screen.getByText("Match")).toBeVisible();
  });

  it("shows a no-results empty state and suggests refining the query", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      getVaultIndex: () => Promise.resolve(snapshot),
      searchVault: () =>
        Promise.resolve({ ...searchResponse, total: 0, returned: 0, hits: [] }),
    });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={workspaceId} />, client);

    const input = await screen.findByLabelText("Vault search query");
    await user.type(input, "nonexistent-symbol");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText(/No matching chunks found/)).toBeVisible();
  });

  it("generates and displays an architecture summary on demand", async () => {
    const user = userEvent.setup();
    const summarizeVaultWorkspace = vi.fn(() => Promise.resolve(architecture));
    const client = createTestClient({
      getVaultIndex: () => Promise.resolve(snapshot),
      summarizeVaultWorkspace,
    });

    renderWithAppProviders(<VaultIndexPanel activeWorkspaceId={workspaceId} />, client);

    await user.click(await screen.findByRole("button", { name: "Generate summary" }));

    expect(await screen.findByText("Technologies")).toBeVisible();
    expect(screen.getByText("src")).toBeVisible();
    expect(screen.getByText("docs")).toBeVisible();
    expect(summarizeVaultWorkspace).toHaveBeenCalledWith(workspaceId);
  });
});
