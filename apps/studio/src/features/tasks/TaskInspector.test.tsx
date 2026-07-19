import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { TaskInspector } from "./TaskInspector";

describe("TaskInspector", () => {
  it("surfaces validation Problem Details", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      getTask: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:validation-error",
            title: "Request validation failed",
            status: 422,
            detail: "The request contains invalid values.",
            errors: [
              {
                pointer: "/path/task_id",
                detail: "Input should be a valid UUID",
              },
            ],
          }),
        ),
    });

    renderWithAppProviders(<TaskInspector />, client);
    await user.type(screen.getByLabelText("Task ID"), "not-a-uuid");
    await user.click(screen.getByRole("button", { name: "Inspect" }));

    expect(await screen.findByText("Request validation failed")).toBeVisible();
    expect(screen.getByText("/path/task_id")).toBeVisible();
    expect(screen.getByText(/Input should be a valid UUID/)).toBeVisible();
  });

  it("starts a run from a looked-up task", async () => {
    const user = userEvent.setup();
    const taskId = "20c74e92-d9fc-4e65-bfbb-4924cc181ed1";
    const runId = "9dc58c91-105d-43af-95cb-32e546ce4c9f";
    const task = {
      id: taskId,
      workspaceId: "5ca252af-76f4-4aed-9718-ff97b610ce90",
      title: "Looked-up task",
      description: "",
      status: "ready" as const,
      assignedRole: null,
      createdAt: "2026-07-19T12:00:00Z",
      updatedAt: "2026-07-19T12:00:00Z",
    };
    const run = {
      id: runId,
      taskId,
      status: "queued" as const,
      startedAt: null,
      finishedAt: null,
      createdAt: "2026-07-19T12:05:00Z",
      updatedAt: "2026-07-19T12:05:00Z",
    };
    const client = createTestClient({
      createRun: () => Promise.resolve(run),
      getRun: () => Promise.resolve(run),
      getTask: () => Promise.resolve(task),
    });

    renderWithAppProviders(<TaskInspector />, client);
    await user.type(screen.getByLabelText("Task ID"), taskId);
    await user.click(screen.getByRole("button", { name: "Inspect" }));
    await screen.findByText("Looked-up task");
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText("Run created and queued.")).toBeVisible();
    expect(screen.getByText(runId)).toBeVisible();
  });
});
