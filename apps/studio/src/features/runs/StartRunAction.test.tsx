import type { ContextPackSummary, Run } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { StartRunAction } from "./StartRunAction";

const taskId = "20c74e92-d9fc-4e65-bfbb-4924cc181ed1";
const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const contextPackId = `sha256:${"a".repeat(64)}` as const;
const contextPack: ContextPackSummary = {
  id: contextPackId,
  digest: contextPackId,
  workspaceId,
  inventoryId: "f6b3c0c2-42a1-4a4d-81f3-82918af050ae",
  schemaVersion: "1",
  summary: {
    fileCount: 2,
    textFileCount: 2,
    binaryFileCount: 0,
    totalFileBytes: 2048,
    totalPreviewBytes: 1024,
    truncatedTextFileCount: 0,
  },
};
const run: Run = {
  id: "9dc58c91-105d-43af-95cb-32e546ce4c9f",
  taskId,
  contextPackId,
  contextPack: {
    id: contextPackId,
    workspaceId,
    inventoryId: contextPack.inventoryId,
    schemaVersion: "1",
    fileCount: 2,
    totalFileBytes: 2048,
    totalPreviewBytes: 1024,
  },
  status: "queued",
  execution: null,
  startedAt: null,
  finishedAt: null,
  createdAt: "2026-07-19T12:05:00Z",
  updatedAt: "2026-07-19T12:05:00Z",
};

describe("StartRunAction", () => {
  it("creates, refreshes, and displays a queued run", async () => {
    const user = userEvent.setup();
    const createRun = vi.fn(() => Promise.resolve(run));
    const getRun = vi.fn(() => Promise.resolve(run));
    const client = createTestClient({
      createRun,
      getRun,
      listContextPacks: () =>
        Promise.resolve({ items: [contextPack], total: 1 }),
    });

    renderWithAppProviders(
      <StartRunAction taskId={taskId} workspaceId={workspaceId} />,
      client,
    );
    const startButton = await screen.findByRole("button", { name: "Start run" });
    expect(startButton).toBeDisabled();
    await user.selectOptions(
      await screen.findByLabelText("Immutable context pack"),
      contextPackId,
    );
    expect(screen.getByText(contextPackId)).toBeVisible();
    expect(screen.getByText(/2 files · 2.0 KiB file data/)).toBeVisible();
    await user.click(startButton);

    expect(
      await screen.findByText("Run created and queued with immutable context."),
    ).toBeVisible();
    expect(screen.getAllByText("queued")[0]).toBeVisible();
    expect(screen.getByText(run.id)).toBeVisible();
    expect(createRun).toHaveBeenCalledWith(taskId, { contextPackId });
    expect(getRun).toHaveBeenCalledWith(run.id);
  });

  it("shows Core Problem Details when run creation fails", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      createRun: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:resource-not-found",
            title: "Resource not found",
            status: 404,
            detail: "The task was not found.",
          }),
        ),
      listContextPacks: () =>
        Promise.resolve({ items: [contextPack], total: 1 }),
    });

    renderWithAppProviders(
      <StartRunAction taskId={taskId} workspaceId={workspaceId} />,
      client,
    );
    await user.selectOptions(
      await screen.findByLabelText("Immutable context pack"),
      contextPackId,
    );
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText("Resource not found")).toBeVisible();
    expect(screen.getByText("The task was not found.")).toBeVisible();
    expect(screen.getByLabelText("Immutable context pack")).toHaveValue(
      contextPackId,
    );
  });

  it("shows guidance and no run action when the workspace has no packs", async () => {
    const client = createTestClient({
      listContextPacks: () => Promise.resolve({ items: [], total: 0 }),
    });

    renderWithAppProviders(
      <StartRunAction taskId={taskId} workspaceId={workspaceId} />,
      client,
    );

    expect(
      await screen.findByText(/Create and review an immutable context pack/),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Start run" })).toBeNull();
  });
});
