import type {
  ContextPackSummary,
  Run,
  TaskCollection,
  TaskSummary,
} from "@mensura/shared-types";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { TaskBoardPanel } from "./TaskBoardPanel";

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

function task(overrides: Partial<TaskSummary> & Pick<TaskSummary, "id" | "title" | "status">): TaskSummary {
  return {
    workspaceId,
    description: "",
    assignedRole: null,
    createdAt: "2026-07-21T10:00:00Z",
    updatedAt: "2026-07-21T10:00:00Z",
    latestRun: null,
    ...overrides,
  };
}

const collection: TaskCollection = {
  total: 3,
  items: [
    task({ id: "t1", title: "Draft the plan", status: "draft" }),
    task({
      id: "t2",
      title: "Running now",
      status: "running",
      latestRun: {
        id: "r2",
        status: "running",
        createdAt: "2026-07-21T11:00:00Z",
        updatedAt: "2026-07-21T11:00:00Z",
      },
    }),
    task({
      id: "t3",
      title: "All done",
      description: "Shipped it.",
      status: "approved",
      latestRun: {
        id: "r3",
        status: "succeeded",
        createdAt: "2026-07-21T12:00:00Z",
        updatedAt: "2026-07-21T12:05:00Z",
      },
    }),
  ],
};

function column(title: string): HTMLElement {
  return screen
    .getByText(title)
    .closest(".workspace-board__column") as HTMLElement;
}

function card(title: string): HTMLElement {
  return screen
    .getByText(title)
    .closest(".workspace-board__card") as HTMLElement;
}

describe("TaskBoardPanel", () => {
  it("fetches real Core tasks and groups them into Backlog / In progress / Done", async () => {
    const client = createTestClient({
      listWorkspaceTasks: () => Promise.resolve(collection),
    });

    renderWithAppProviders(
      <TaskBoardPanel workspaceId={workspaceId} />,
      client,
    );

    // Wait for the async query to resolve before locating columns.
    await screen.findByText("Draft the plan");
    expect(within(column("Backlog")).getByText("Draft the plan")).toBeVisible();
    expect(within(column("In progress")).getByText("Running now")).toBeVisible();
    expect(within(column("Done")).getByText("All done")).toBeVisible();
    expect(screen.getByText("Shipped it.")).toBeVisible();
    // Each card keeps its exact task status badge.
    expect(screen.getByText("approved")).toBeVisible();
    // Total count is surfaced honestly in the heading.
    expect(screen.getByText("3 tasks")).toBeVisible();
  });

  it("renders a compact latest-run badge only for tasks that have run", async () => {
    const client = createTestClient({
      listWorkspaceTasks: () => Promise.resolve(collection),
    });

    renderWithAppProviders(
      <TaskBoardPanel workspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByText("run: running")).toBeVisible();
    expect(screen.getByText("run: succeeded")).toBeVisible();
    // The never-run backlog task shows no run badge.
    expect(screen.queryByText("run: queued")).not.toBeInTheDocument();
    const draftCard = screen
      .getByText("Draft the plan")
      .closest(".workspace-board__card") as HTMLElement;
    expect(within(draftCard).queryByText(/^run:/)).not.toBeInTheDocument();
  });

  it("shows a clear empty state when the workspace has no tasks", async () => {
    const client = createTestClient({
      listWorkspaceTasks: () => Promise.resolve({ items: [], total: 0 }),
    });

    renderWithAppProviders(
      <TaskBoardPanel workspaceId={workspaceId} />,
      client,
    );

    expect(
      await screen.findByText(
        "No tasks yet for this workspace. Create one from the Tasks panel.",
      ),
    ).toBeVisible();
    expect(screen.queryByText("Backlog")).not.toBeInTheDocument();
  });

  it("surfaces a bounded error when Core fails to list tasks", async () => {
    const client = createTestClient({
      listWorkspaceTasks: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:resource-not-found",
            title: "Resource not found",
            status: 404,
            detail: "Workspace was not found.",
          }),
        ),
    });

    renderWithAppProviders(
      <TaskBoardPanel workspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByRole("alert")).toBeVisible();
    expect(screen.getByText("Resource not found")).toBeVisible();
    expect(screen.getByText("Workspace was not found.")).toBeVisible();
    expect(screen.queryByText("Backlog")).not.toBeInTheDocument();
  });

  it("offers an enabled Start run only on eligible cards", async () => {
    const client = createTestClient({
      listWorkspaceTasks: () => Promise.resolve(collection),
    });

    renderWithAppProviders(<TaskBoardPanel workspaceId={workspaceId} />, client);
    await screen.findByText("Draft the plan");

    // draft → eligible; running/approved → disabled with a reason.
    expect(
      within(card("Draft the plan")).getByRole("button", { name: "Start run" }),
    ).toBeEnabled();
    expect(
      within(card("Running now")).getByRole("button", { name: "Start run" }),
    ).toBeDisabled();
    expect(
      within(card("All done")).getByRole("button", { name: "Start run" }),
    ).toBeDisabled();
  });

  it("launches a run from an eligible card and refreshes the board", async () => {
    const user = userEvent.setup();
    const runForTask: Run = {
      id: "9dc58c91-105d-43af-95cb-32e546ce4c9f",
      taskId: "t1",
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
    const listWorkspaceTasks = vi.fn(() => Promise.resolve(collection));
    const createRun = vi.fn(() => Promise.resolve(runForTask));
    const client = createTestClient({
      listWorkspaceTasks,
      listContextPacks: () => Promise.resolve({ items: [contextPack], total: 1 }),
      createRun,
    });

    renderWithAppProviders(<TaskBoardPanel workspaceId={workspaceId} />, client);
    await screen.findByText("Draft the plan");

    const draftCard = card("Draft the plan");
    await user.click(
      within(draftCard).getByRole("button", { name: "Start run" }),
    );
    await user.selectOptions(
      await within(draftCard).findByLabelText("Immutable context pack"),
      contextPackId,
    );
    await user.click(
      within(draftCard).getByRole("button", { name: "Start run" }),
    );

    expect(await within(draftCard).findByText("Run queued.")).toBeVisible();
    // The board reused the existing createRun path for this exact task.
    expect(createRun).toHaveBeenCalledWith("t1", { contextPackId });
    // The board refetched after launch (initial load + post-launch invalidation).
    await waitFor(() =>
      expect(listWorkspaceTasks.mock.calls.length).toBeGreaterThan(1),
    );
  });
});
