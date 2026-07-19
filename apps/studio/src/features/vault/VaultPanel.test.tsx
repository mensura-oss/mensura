import type {
  VaultFileCollection,
  VaultFilePreview,
  VaultInventorySnapshot,
} from "@mensura/shared-types";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { VaultPanel } from "./VaultPanel";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const inventoryId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";

const snapshot: VaultInventorySnapshot = {
  id: inventoryId,
  workspaceId,
  status: "ready",
  builtAt: "2026-07-19T13:00:00Z",
  summary: {
    includedFileCount: 2,
    excludedEntryCount: 7,
    textFileCount: 1,
    binaryFileCount: 1,
    totalSizeBytes: 1036,
    extensions: [
      { value: ".md", count: 1 },
      { value: ".png", count: 1 },
    ],
    languages: [{ value: "Markdown", count: 1 }],
  },
};

const files: VaultFileCollection = {
  inventoryId,
  workspaceId,
  items: [
    {
      path: "assets/logo.png",
      name: "logo.png",
      extension: ".png",
      language: null,
      kind: "binary",
      sizeBytes: 1024,
    },
    {
      path: "README.md",
      name: "README.md",
      extension: ".md",
      language: "Markdown",
      kind: "text",
      sizeBytes: 12,
    },
  ],
  total: 2,
  returned: 2,
};

const preview: VaultFilePreview = {
  inventoryId,
  workspaceId,
  file: files.items[1]!,
  encoding: "utf-8",
  text: "# Mensura\n",
  previewBytes: 10,
  totalBytes: 12,
  truncated: true,
};

function notBuiltProblem() {
  return new CoreApiError({
    type: "urn:mensura:problem:vault-inventory-not-built",
    title: "Vault inventory not built",
    status: 404,
    detail: "No Vault inventory exists for this workspace.",
  });
}

describe("VaultPanel", () => {
  it("guides the user without requesting Core when no workspace is active", () => {
    const getVaultInventory = vi.fn(() => Promise.resolve(snapshot));
    const client = createTestClient({ getVaultInventory });

    renderWithAppProviders(<VaultPanel activeWorkspaceId={null} />, client);

    expect(
      screen.getByText("Select an active workspace to build its Vault inventory."),
    ).toBeVisible();
    expect(getVaultInventory).not.toHaveBeenCalled();
  });

  it("treats absent inventory as a neutral build state", async () => {
    const client = createTestClient({
      getVaultInventory: () => Promise.reject(notBuiltProblem()),
    });

    renderWithAppProviders(<VaultPanel activeWorkspaceId={workspaceId} />, client);

    expect(
      await screen.findByText(
        "No Vault inventory yet. Build one to inspect repository files.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Build inventory" })).toBeVisible();
    expect(screen.queryByText("Vault inventory not built")).not.toBeInTheDocument();
  });

  it("shows a pending build and then the refreshed inventory", async () => {
    const user = userEvent.setup();
    let resolveBuild!: (value: VaultInventorySnapshot) => void;
    const buildVaultInventory = vi.fn(
      () =>
        new Promise<VaultInventorySnapshot>((resolve) => {
          resolveBuild = resolve;
        }),
    );
    const listVaultFiles = vi.fn(() => Promise.resolve(files));
    const client = createTestClient({
      buildVaultInventory,
      getVaultInventory: () => Promise.reject(notBuiltProblem()),
      listVaultFiles,
    });

    renderWithAppProviders(<VaultPanel activeWorkspaceId={workspaceId} />, client);
    await user.click(await screen.findByRole("button", { name: "Build inventory" }));

    expect(screen.getByRole("button", { name: "Building inventory…" })).toBeDisabled();
    expect(
      screen.getByText("Core is traversing the workspace with fixed exclusion rules…"),
    ).toBeVisible();

    resolveBuild(snapshot);

    expect(await screen.findByRole("button", { name: "Refresh inventory" })).toBeVisible();
    expect(await screen.findByText("README.md")).toBeVisible();
    expect(buildVaultInventory).toHaveBeenCalledWith(workspaceId);
    expect(listVaultFiles).toHaveBeenCalledWith(workspaceId, { limit: 200 });
  });

  it("renders compact counts and retrieves a selected text preview", async () => {
    const user = userEvent.setup();
    const getVaultFilePreview = vi.fn(() => Promise.resolve(preview));
    const client = createTestClient({
      getVaultFilePreview,
      getVaultInventory: () => Promise.resolve(snapshot),
      listVaultFiles: () => Promise.resolve(files),
    });

    renderWithAppProviders(<VaultPanel activeWorkspaceId={workspaceId} />, client);

    expect(await screen.findByText("Markdown 1")).toBeVisible();
    expect(
      within(screen.getByText("Included").parentElement!).getByText("2"),
    ).toBeVisible();
    expect(
      within(screen.getByText("Excluded").parentElement!).getByText("7"),
    ).toBeVisible();

    await user.click(await screen.findByRole("button", { name: /README\.md/ }));

    expect(await screen.findByText("# Mensura")).toBeVisible();
    expect(screen.getByText("12 B")).toBeVisible();
    expect(screen.getByText("10 B of 12 B · truncated")).toBeVisible();
    expect(getVaultFilePreview).toHaveBeenCalledWith(workspaceId, "README.md");
  });

  it("shows binary metadata without requesting a preview", async () => {
    const user = userEvent.setup();
    const getVaultFilePreview = vi.fn(() => Promise.resolve(preview));
    const client = createTestClient({
      getVaultFilePreview,
      getVaultInventory: () => Promise.resolve(snapshot),
      listVaultFiles: () => Promise.resolve(files),
    });

    renderWithAppProviders(<VaultPanel activeWorkspaceId={workspaceId} />, client);
    await user.click(await screen.findByRole("button", { name: /assets\/logo\.png/ }));

    expect(
      screen.getByText(
        "Binary files are inventoried as metadata, but text preview is unavailable.",
      ),
    ).toBeVisible();
    expect(getVaultFilePreview).not.toHaveBeenCalled();
  });

  it("keeps an RFC 9457 preview refusal local to the inspector", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      getVaultFilePreview: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:vault-file-excluded",
            title: "Vault file access excluded",
            status: 403,
            detail: "The selected path is no longer safe to preview.",
          }),
        ),
      getVaultInventory: () => Promise.resolve(snapshot),
      listVaultFiles: () => Promise.resolve(files),
    });

    renderWithAppProviders(<VaultPanel activeWorkspaceId={workspaceId} />, client);
    await user.click(await screen.findByRole("button", { name: /README\.md/ }));

    expect(await screen.findByText("Vault file access excluded")).toBeVisible();
    expect(screen.getByText("403")).toBeVisible();
    expect(screen.getAllByText("README.md")).toHaveLength(2);
  });
});
