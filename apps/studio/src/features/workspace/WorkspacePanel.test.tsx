import type {
  RepositorySummary,
  VaultFileCollection,
  VaultFilePreview,
  VaultIndexSnapshot,
  VaultInventorySnapshot,
} from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { WorkspacePanel } from "./WorkspacePanel";

vi.mock("./MonacoCodeViewer", async () => {
  const { createElement } = await import("react");
  return {
    default: (props: {
      value: string;
      language: string;
      highlight?: { startLine: number; endLine: number } | null;
    }) =>
      createElement(
        "pre",
        {
          "data-testid": "monaco",
          "data-highlight": props.highlight
            ? `${props.highlight.startLine}-${props.highlight.endLine}`
            : "",
        },
        props.value,
      ),
  };
});

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const inventoryId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";

const inventory: VaultInventorySnapshot = {
  id: inventoryId,
  workspaceId,
  status: "ready",
  builtAt: "2026-07-19T13:00:00Z",
  summary: {
    includedFileCount: 2,
    excludedEntryCount: 3,
    textFileCount: 2,
    binaryFileCount: 0,
    totalSizeBytes: 84,
    extensions: [],
    languages: [],
  },
};

const files: VaultFileCollection = {
  inventoryId,
  workspaceId,
  items: [
    {
      path: "src/app.ts",
      name: "app.ts",
      extension: ".ts",
      language: "TypeScript",
      kind: "text",
      sizeBytes: 42,
    },
    {
      path: "README.md",
      name: "README.md",
      extension: ".md",
      language: "Markdown",
      kind: "text",
      sizeBytes: 42,
    },
  ],
  total: 2,
  returned: 2,
};

const index: VaultIndexSnapshot = {
  id: "3f7b6b8a-2c1d-4e9a-9b2f-1c0a5d6e7f80",
  workspaceId,
  status: "ready",
  indexedAt: "2026-07-20T09:00:00Z",
  summary: {
    memoryItemCount: 2,
    chunkCount: 4,
    codeFileCount: 1,
    docFileCount: 1,
    configFileCount: 0,
    totalSizeBytes: 84,
    skippedCount: 0,
    skippedByReason: [],
    languages: [],
    skippedSample: [],
  },
};

const repository: RepositorySummary = {
  workspaceId,
  isRepository: true,
  branch: "main",
  isDirty: false,
  stagedCount: 0,
  unstagedCount: 0,
  untrackedCount: 0,
  changedPathsCount: 0,
  diffMetadata: [],
};

function preview(text: string): VaultFilePreview {
  return {
    inventoryId,
    workspaceId,
    file: files.items[0]!,
    encoding: "utf-8",
    text,
    previewBytes: text.length,
    totalBytes: text.length,
    truncated: false,
  };
}

function problem(type: string, status: number) {
  return new CoreApiError({ type, title: type, status });
}

const notBuiltInventory = () =>
  Promise.reject(problem("urn:mensura:problem:vault-inventory-not-built", 404));
const notBuiltIndex = () =>
  Promise.reject(problem("urn:mensura:problem:vault-index-not-built", 404));
const notAGitRepo = () =>
  Promise.reject(problem("urn:mensura:problem:not-a-git-repository", 409));

describe("WorkspacePanel", () => {
  it("guides the user when no workspace is active", () => {
    renderWithAppProviders(
      <WorkspacePanel activeWorkspaceId={null} />,
      createTestClient(),
    );

    expect(
      screen.getByText(
        "Open a workspace to browse its repository, view files, and see its task board.",
      ),
    ).toBeVisible();
  });

  it("prompts to build the file tree and still shows repo status and the board", async () => {
    const client = createTestClient({
      getWorkspaceRepository: notAGitRepo,
      getVaultIndex: notBuiltIndex,
      getVaultInventory: notBuiltInventory,
    });

    renderWithAppProviders(
      <WorkspacePanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(
      await screen.findByText(
        "Build the workspace file tree to browse the repository and open files in the editor.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Build file tree" })).toBeVisible();
    // "Connect a repository" style hint for a non-git workspace.
    expect(
      screen.getByText(
        "Not a Git repository — connect one to enable repository features.",
      ),
    ).toBeVisible();
    // The local task board is independent of the inventory.
    expect(screen.getByText("Index the repository into Vault")).toBeVisible();
  });

  it("renders the tree, an Indexed-by-Vault badge, and opens a file into the editor", async () => {
    const user = userEvent.setup();
    const getVaultFilePreview = vi.fn(() =>
      Promise.resolve(preview("export const answer = 42;\n")),
    );
    const client = createTestClient({
      getWorkspaceRepository: () => Promise.resolve(repository),
      getVaultIndex: () => Promise.resolve(index),
      getVaultInventory: () => Promise.resolve(inventory),
      listVaultFiles: () => Promise.resolve(files),
      getVaultFilePreview,
    });

    renderWithAppProviders(
      <WorkspacePanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByText("Indexed by Vault")).toBeVisible();
    expect(await screen.findByRole("button", { name: "src" })).toBeVisible();

    await user.click(await screen.findByRole("button", { name: /app\.ts/ }));

    const monaco = await screen.findByTestId("monaco");
    expect(monaco).toHaveTextContent("export const answer = 42;");
    expect(getVaultFilePreview).toHaveBeenCalledWith(workspaceId, "src/app.ts");
  });

  it("applies a cross-panel open request with a highlighted line range", async () => {
    const getVaultFilePreview = vi.fn(() =>
      Promise.resolve(preview("a\nb\nc\nd\n")),
    );
    const client = createTestClient({
      getWorkspaceRepository: () => Promise.resolve(repository),
      getVaultIndex: () => Promise.resolve(index),
      getVaultInventory: () => Promise.resolve(inventory),
      listVaultFiles: () => Promise.resolve(files),
      getVaultFilePreview,
    });

    renderWithAppProviders(
      <WorkspacePanel
        activeWorkspaceId={workspaceId}
        openRequest={{ requestId: 1, path: "src/app.ts", startLine: 2, endLine: 3 }}
      />,
      client,
    );

    const monaco = await screen.findByTestId("monaco");
    expect(monaco).toHaveAttribute("data-highlight", "2-3");
    expect(getVaultFilePreview).toHaveBeenCalledWith(workspaceId, "src/app.ts");
  });

  it("shows an empty state when the inventory has no files", async () => {
    const client = createTestClient({
      getWorkspaceRepository: () => Promise.resolve(repository),
      getVaultIndex: notBuiltIndex,
      getVaultInventory: () => Promise.resolve(inventory),
      listVaultFiles: () =>
        Promise.resolve({ ...files, items: [], total: 0, returned: 0 }),
    });

    renderWithAppProviders(
      <WorkspacePanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(
      await screen.findByText("No files were inventoried for this workspace."),
    ).toBeVisible();
    expect(
      screen.getByText("Not indexed by Vault — index it from the Vault memory panel."),
    ).toBeVisible();
  });
});
