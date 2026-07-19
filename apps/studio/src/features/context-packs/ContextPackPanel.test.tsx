import type {
  ContextPackCollection,
  ContextPackManifest,
  CreateContextPackResponse,
  VaultFileCollection,
  VaultInventorySnapshot,
} from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { ContextPackPanel } from "./ContextPackPanel";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const inventoryId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";
const packId = `sha256:${"a".repeat(64)}` as const;

const inventory: VaultInventorySnapshot = {
  id: inventoryId,
  workspaceId,
  status: "ready",
  builtAt: "2026-07-19T13:00:00Z",
  summary: {
    includedFileCount: 2,
    excludedEntryCount: 3,
    textFileCount: 1,
    binaryFileCount: 1,
    totalSizeBytes: 20_012,
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
      sizeBytes: 12,
    },
    {
      path: "README.md",
      name: "README.md",
      extension: ".md",
      language: "Markdown",
      kind: "text",
      sizeBytes: 20_000,
    },
  ],
  total: 2,
  returned: 2,
};

const manifest: ContextPackManifest = {
  id: packId,
  digest: packId,
  workspaceId,
  inventoryId,
  schemaVersion: "1",
  limits: {
    maxFiles: 50,
    maxPreviewBytesPerFile: 16 * 1024,
    maxTotalPreviewBytes: 256 * 1024,
  },
  summary: {
    fileCount: 2,
    textFileCount: 1,
    binaryFileCount: 1,
    totalFileBytes: 20_012,
    totalPreviewBytes: 16 * 1024,
    truncatedTextFileCount: 1,
  },
  files: [
    {
      ...files.items[0]!,
      contentDigest: `sha256:${"b".repeat(64)}`,
      captureMode: "metadata_only",
      encoding: null,
      previewText: null,
      previewBytes: 0,
      totalBytes: 12,
      truncated: false,
    },
    {
      ...files.items[1]!,
      contentDigest: `sha256:${"c".repeat(64)}`,
      captureMode: "text_preview",
      encoding: "utf-8",
      previewText: "bounded evidence",
      previewBytes: 16 * 1024,
      totalBytes: 20_000,
      truncated: true,
    },
  ],
};

const collection: ContextPackCollection = {
  items: [
    {
      id: manifest.id,
      digest: manifest.digest,
      workspaceId,
      inventoryId,
      schemaVersion: "1",
      summary: manifest.summary,
    },
  ],
  total: 1,
};

function inventoryNotBuilt() {
  return new CoreApiError({
    type: "urn:mensura:problem:vault-inventory-not-built",
    title: "Vault inventory not built",
    status: 404,
    detail: "No Vault inventory exists for this workspace.",
  });
}

describe("ContextPackPanel", () => {
  it("guides the user without making requests when no workspace is active", () => {
    const getVaultInventory = vi.fn(() => Promise.resolve(inventory));
    const client = createTestClient({ getVaultInventory });

    renderWithAppProviders(<ContextPackPanel activeWorkspaceId={null} />, client);

    expect(
      screen.getByText(
        "Select an active workspace before assembling immutable context.",
      ),
    ).toBeVisible();
    expect(getVaultInventory).not.toHaveBeenCalled();
  });

  it("treats an absent inventory as neutral guidance", async () => {
    const client = createTestClient({
      getVaultInventory: () => Promise.reject(inventoryNotBuilt()),
      listContextPacks: () => Promise.resolve({ items: [], total: 0 }),
    });

    renderWithAppProviders(
      <ContextPackPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(
      await screen.findByText(
        "Build a Vault inventory above before selecting context files.",
      ),
    ).toBeVisible();
    expect(screen.queryByText("Vault inventory not built")).not.toBeInTheDocument();
  });

  it("shows exact selection and immediately reviews the created immutable manifest", async () => {
    const user = userEvent.setup();
    let resolveCreate!: (value: CreateContextPackResponse) => void;
    const createContextPack = vi.fn(
      () =>
        new Promise<CreateContextPackResponse>((resolve) => {
          resolveCreate = resolve;
        }),
    );
    const client = createTestClient({
      createContextPack,
      getVaultInventory: () => Promise.resolve(inventory),
      listContextPacks: () => Promise.resolve({ items: [], total: 0 }),
      listVaultFiles: () => Promise.resolve(files),
    });

    renderWithAppProviders(
      <ContextPackPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    await user.click(await screen.findByRole("checkbox", { name: /assets\/logo\.png/ }));
    await user.click(screen.getByRole("checkbox", { name: /README\.md/ }));

    expect(screen.getByText("2 selected")).toBeVisible();
    expect(screen.getByText("Preview upper bound 16.0 KiB")).toBeVisible();
    expect(screen.getByText("metadata only")).toBeVisible();
    expect(screen.getByText("bounded preview")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Create immutable pack" }));

    expect(screen.getByRole("button", { name: "Creating pack…" })).toBeDisabled();
    expect(
      screen.getByText("Core is hashing files and capturing bounded evidence…"),
    ).toBeVisible();
    expect(createContextPack).toHaveBeenCalledWith(workspaceId, {
      paths: ["assets/logo.png", "README.md"],
    });

    resolveCreate({ contextPack: manifest, created: true });

    expect(await screen.findByText("Context pack created and locked.")).toBeVisible();
    expect(screen.getByText("Immutable context pack")).toBeVisible();
    expect(screen.getByText("Locked")).toBeVisible();
    expect(screen.getByText(packId)).toBeVisible();
    expect(screen.getByText("Metadata only")).toBeVisible();
    expect(screen.getByText("Text preview · truncated")).toBeVisible();
    expect(screen.queryByText("bounded evidence")).not.toBeInTheDocument();
  });

  it("opens a listed context pack in read-only mode", async () => {
    const user = userEvent.setup();
    const getContextPack = vi.fn(() => Promise.resolve(manifest));
    const client = createTestClient({
      getContextPack,
      getVaultInventory: () => Promise.resolve(inventory),
      listContextPacks: () => Promise.resolve(collection),
      listVaultFiles: () => Promise.resolve(files),
    });

    renderWithAppProviders(
      <ContextPackPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    await user.click(await screen.findByRole("button", { name: /sha256:aaaaaaaaaaaa/ }));

    expect(await screen.findByText("Immutable context pack")).toBeVisible();
    expect(getContextPack).toHaveBeenCalledWith(workspaceId, packId);
    expect(screen.getByText(inventoryId)).toBeVisible();
  });

  it("surfaces an RFC 9457 creation refusal next to the action", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      createContextPack: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:context-pack-file-changed",
            title: "Context-pack file changed",
            status: 409,
            detail: "Refresh the inventory before creating a context pack.",
          }),
        ),
      getVaultInventory: () => Promise.resolve(inventory),
      listContextPacks: () => Promise.resolve({ items: [], total: 0 }),
      listVaultFiles: () => Promise.resolve(files),
    });

    renderWithAppProviders(
      <ContextPackPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    await user.click(await screen.findByRole("checkbox", { name: /README\.md/ }));
    await user.click(screen.getByRole("button", { name: "Create immutable pack" }));

    expect(await screen.findByText("Context-pack file changed")).toBeVisible();
    expect(screen.getByText("409")).toBeVisible();
    expect(screen.getByRole("checkbox", { name: /README\.md/ })).toBeChecked();
  });
});
