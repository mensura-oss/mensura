import type { Run, Task, Workspace } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createTestClient, renderWithAppProviders } from "../test/render";
import { CoreApiError } from "../api/coreClient";
import { App } from "./App";
import { ACTIVE_WORKSPACE_STORAGE_KEY } from "./useActiveWorkspaceId";

const workspace: Workspace = {
  id: "5ca252af-76f4-4aed-9718-ff97b610ce90",
  name: "Mensura",
  rootPath: "/code/mensura",
  createdAt: "2026-07-19T11:00:00Z",
  updatedAt: "2026-07-19T11:00:00Z",
};

const task: Task = {
  id: "20c74e92-d9fc-4e65-bfbb-4924cc181ed1",
  workspaceId: workspace.id,
  title: "Deliver the first task flow",
  description: "Create a task and queued run from Studio.",
  status: "ready",
  assignedRole: null,
  createdAt: "2026-07-19T12:00:00Z",
  updatedAt: "2026-07-19T12:00:00Z",
};

const contextPackId = `sha256:${"c".repeat(64)}` as const;
const contextPack = {
  id: contextPackId,
  digest: contextPackId,
  workspaceId: workspace.id,
  inventoryId: "f6b3c0c2-42a1-4a4d-81f3-82918af050ae",
  schemaVersion: "1" as const,
  summary: {
    fileCount: 1,
    textFileCount: 1,
    binaryFileCount: 0,
    totalFileBytes: 128,
    totalPreviewBytes: 128,
    truncatedTextFileCount: 0,
  },
};

const run: Run = {
  id: "9dc58c91-105d-43af-95cb-32e546ce4c9f",
  taskId: task.id,
  contextPackId,
  contextPack: {
    id: contextPackId,
    workspaceId: workspace.id,
    inventoryId: contextPack.inventoryId,
    schemaVersion: "1",
    fileCount: 1,
    totalFileBytes: 128,
    totalPreviewBytes: 128,
  },
  status: "queued",
  execution: null,
  startedAt: null,
  finishedAt: null,
  createdAt: "2026-07-19T12:05:00Z",
  updatedAt: "2026-07-19T12:05:00Z",
};

describe("App task flow", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("creates and selects a workspace, creates a task, and starts a queued run", async () => {
    const user = userEvent.setup();
    let workspaces: readonly Workspace[] = [];
    const createWorkspace = vi.fn(() => {
      workspaces = [workspace];
      return Promise.resolve(workspace);
    });
    const createTask = vi.fn(() => Promise.resolve(task));
    const createRun = vi.fn(() => Promise.resolve(run));
    const client = createTestClient({
      createRun,
      createTask,
      createWorkspace,
      getHealth: () =>
        Promise.resolve({
          status: "ok",
          service: "mensura-core",
          version: "0.1.0",
        }),
      getRun: () => Promise.resolve(run),
      getLatestGuardRun: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:guard-run-not-found",
            title: "Guard run not found",
            status: 404,
          }),
        ),
      getTask: () => Promise.resolve(task),
      getVaultInventory: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:vault-inventory-not-built",
            title: "Vault inventory not built",
            status: 404,
          }),
        ),
      getWorkspaceRepository: () =>
        Promise.reject(
          new Error("Repository inspection is independently unavailable."),
        ),
      listWorkspaces: () =>
        Promise.resolve({ items: workspaces, total: workspaces.length }),
      listContextPacks: () =>
        Promise.resolve({ items: [contextPack], total: 1 }),
    });

    renderWithAppProviders(<App />, client);

    await user.type(screen.getByLabelText("Name"), workspace.name);
    await user.type(screen.getByLabelText("Root path"), workspace.rootPath);
    await user.click(screen.getByRole("button", { name: "Create workspace" }));

    expect(await screen.findByText("Active workspace")).toBeVisible();
    expect(window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY)).toBe(
      workspace.id,
    );

    await user.type(screen.getByLabelText("Title"), task.title);
    await user.type(screen.getByLabelText("Description"), task.description);
    await user.click(screen.getByRole("button", { name: "Create task" }));

    expect(await screen.findByText("Task created and ready.")).toBeVisible();
    expect(screen.getByText(task.title)).toBeVisible();
    expect(
      screen.getByText("Repository inspection is independently unavailable."),
    ).toBeVisible();

    await user.selectOptions(
      screen.getByLabelText("Immutable context pack"),
      contextPackId,
    );
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(
      await screen.findByText("Run created and queued with immutable context."),
    ).toBeVisible();
    expect(screen.getByText(run.id)).toBeVisible();
    expect(createWorkspace).toHaveBeenCalledTimes(1);
    expect(createTask).toHaveBeenCalledWith({
      workspaceId: workspace.id,
      title: task.title,
      description: task.description,
    });
    expect(createRun).toHaveBeenCalledWith(task.id, { contextPackId });
  });
});
