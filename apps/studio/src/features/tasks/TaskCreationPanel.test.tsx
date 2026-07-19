import type { Task, Workspace } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { TaskCreationPanel } from "./TaskCreationPanel";

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
  title: "Create the first task",
  description: "Keep the flow vertical.",
  status: "ready",
  assignedRole: "coder",
  createdAt: "2026-07-19T12:00:00Z",
  updatedAt: "2026-07-19T12:00:00Z",
};

describe("TaskCreationPanel", () => {
  it("guides the user when no workspace is active", () => {
    const client = createTestClient();

    renderWithAppProviders(
      <TaskCreationPanel activeWorkspaceId={null} />,
      client,
    );

    expect(
      screen.getByText("Select or create a workspace before creating a task."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Create task" })).toBeNull();
  });

  it("validates the title and creates a ready task", async () => {
    const user = userEvent.setup();
    const createTask = vi.fn(() => Promise.resolve(task));
    const client = createTestClient({
      createTask,
      getTask: () => Promise.resolve(task),
      listWorkspaces: () => Promise.resolve({ items: [workspace], total: 1 }),
    });

    renderWithAppProviders(
      <TaskCreationPanel activeWorkspaceId={workspace.id} />,
      client,
    );

    const titleInput = await screen.findByLabelText("Title");
    await user.type(titleInput, "   ");
    await user.click(screen.getByRole("button", { name: "Create task" }));
    expect(screen.getByText("Enter a task title.")).toBeVisible();
    expect(titleInput).toHaveAttribute("aria-invalid", "true");
    expect(createTask).not.toHaveBeenCalled();

    await user.clear(titleInput);
    await user.type(titleInput, task.title);
    await user.type(screen.getByLabelText("Description"), task.description);
    await user.selectOptions(screen.getByLabelText("Assigned role"), "coder");
    await user.click(screen.getByRole("button", { name: "Create task" }));

    expect(await screen.findByText("Task created and ready.")).toBeVisible();
    expect(screen.getByText(task.title)).toBeVisible();
    expect(createTask).toHaveBeenCalledWith({
      workspaceId: workspace.id,
      title: task.title,
      description: task.description,
      assignedRole: "coder",
    });
    expect(titleInput).toHaveValue("");
  });

  it("keeps entered values when Core rejects task creation", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      createTask: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:resource-not-found",
            title: "Resource not found",
            status: 404,
            detail: "The active workspace was not found.",
          }),
        ),
      listWorkspaces: () => Promise.resolve({ items: [workspace], total: 1 }),
    });

    renderWithAppProviders(
      <TaskCreationPanel activeWorkspaceId={workspace.id} />,
      client,
    );

    const titleInput = await screen.findByLabelText("Title");
    await user.type(titleInput, "Keep this title");
    await user.click(screen.getByRole("button", { name: "Create task" }));

    expect(await screen.findByText("Resource not found")).toBeVisible();
    expect(titleInput).toHaveValue("Keep this title");
  });
});
