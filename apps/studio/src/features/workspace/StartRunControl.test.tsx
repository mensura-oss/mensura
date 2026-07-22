import type { ContextPackSummary, Run, TaskSummary } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { StartRunControl } from "./StartRunControl";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const taskId = "20c74e92-d9fc-4e65-bfbb-4924cc181ed1";
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

const queuedRun: Run = {
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
  createdAt: "2026-07-22T12:05:00Z",
  updatedAt: "2026-07-22T12:05:00Z",
};

function task(
  overrides: Partial<TaskSummary> & Pick<TaskSummary, "status">,
): TaskSummary {
  return {
    id: taskId,
    workspaceId,
    title: "A task",
    description: "",
    assignedRole: null,
    createdAt: "2026-07-21T10:00:00Z",
    updatedAt: "2026-07-21T10:00:00Z",
    latestRun: null,
    ...overrides,
  };
}

describe("StartRunControl", () => {
  it("launches a run for an eligible task through the existing createRun flow", async () => {
    const user = userEvent.setup();
    const createRun = vi.fn(() => Promise.resolve(queuedRun));
    const listContextPacks = vi.fn(() =>
      Promise.resolve({ items: [contextPack], total: 1 }),
    );
    const client = createTestClient({ createRun, listContextPacks });

    renderWithAppProviders(
      <StartRunControl task={task({ status: "ready" })} />,
      client,
    );

    // Collapsed by default: the pack list is not fetched until the user opens it.
    expect(listContextPacks).not.toHaveBeenCalled();
    const startButton = screen.getByRole("button", { name: "Start run" });
    expect(startButton).toBeEnabled();
    await user.click(startButton);

    await user.selectOptions(
      await screen.findByLabelText("Immutable context pack"),
      contextPackId,
    );
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText("Run queued.")).toBeVisible();
    expect(createRun).toHaveBeenCalledWith(taskId, { contextPackId });
    expect(listContextPacks).toHaveBeenCalledWith(workspaceId);
  });

  it("disables Start run with a bounded reason for an ineligible status", () => {
    renderWithAppProviders(
      <StartRunControl task={task({ status: "approved" })} />,
      createTestClient(),
    );

    expect(screen.getByRole("button", { name: "Start run" })).toBeDisabled();
    expect(
      screen.getByText(/this task is approved and cannot start a new run/i),
    ).toBeVisible();
  });

  it("disables Start run while a run is already in flight for the task", () => {
    renderWithAppProviders(
      <StartRunControl
        task={task({
          status: "ready",
          latestRun: {
            id: "r-active",
            status: "queued",
            createdAt: "2026-07-22T12:00:00Z",
            updatedAt: "2026-07-22T12:00:00Z",
          },
        })}
      />,
      createTestClient(),
    );

    expect(screen.getByRole("button", { name: "Start run" })).toBeDisabled();
    expect(screen.getByText(/a run is already queued for this task/i)).toBeVisible();
  });

  it("guides the user to create a context pack when the workspace has none", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      listContextPacks: () => Promise.resolve({ items: [], total: 0 }),
    });

    renderWithAppProviders(
      <StartRunControl task={task({ status: "draft" })} />,
      client,
    );

    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(
      await screen.findByText(/No immutable context pack yet/),
    ).toBeVisible();
    // The confirm button is present but cannot launch without a pack.
    expect(screen.getByRole("button", { name: "Start run" })).toBeDisabled();
  });

  it("surfaces bounded Problem Details when the launch fails and keeps the picker", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      listContextPacks: () => Promise.resolve({ items: [contextPack], total: 1 }),
      createRun: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:context-pack-not-found",
            title: "Context pack not found",
            status: 404,
            detail: "The selected pack is no longer available.",
          }),
        ),
    });

    renderWithAppProviders(
      <StartRunControl task={task({ status: "ready" })} />,
      client,
    );

    await user.click(screen.getByRole("button", { name: "Start run" }));
    await user.selectOptions(
      await screen.findByLabelText("Immutable context pack"),
      contextPackId,
    );
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText("Context pack not found")).toBeVisible();
    expect(
      screen.getByText("The selected pack is no longer available."),
    ).toBeVisible();
    // The picker stays open so the user can retry or cancel — no run was queued.
    expect(screen.getByLabelText("Immutable context pack")).toBeVisible();
    expect(screen.queryByText("Run queued.")).not.toBeInTheDocument();
  });

  it("shows an in-flight Starting… state while the request is pending", async () => {
    const user = userEvent.setup();
    let resolveRun: (run: Run) => void = () => {};
    const client = createTestClient({
      listContextPacks: () => Promise.resolve({ items: [contextPack], total: 1 }),
      createRun: () =>
        new Promise<Run>((resolve) => {
          resolveRun = resolve;
        }),
    });

    renderWithAppProviders(
      <StartRunControl task={task({ status: "ready" })} />,
      client,
    );

    await user.click(screen.getByRole("button", { name: "Start run" }));
    await user.selectOptions(
      await screen.findByLabelText("Immutable context pack"),
      contextPackId,
    );
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByRole("button", { name: "Starting…" })).toBeDisabled();

    resolveRun(queuedRun);
    expect(await screen.findByText("Run queued.")).toBeVisible();
  });
});
