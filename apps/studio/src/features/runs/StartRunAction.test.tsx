import type { Run } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { StartRunAction } from "./StartRunAction";

const taskId = "20c74e92-d9fc-4e65-bfbb-4924cc181ed1";
const run: Run = {
  id: "9dc58c91-105d-43af-95cb-32e546ce4c9f",
  taskId,
  status: "queued",
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
    const client = createTestClient({ createRun, getRun });

    renderWithAppProviders(<StartRunAction taskId={taskId} />, client);
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText("Run created and queued.")).toBeVisible();
    expect(screen.getByText("queued")).toBeVisible();
    expect(screen.getByText(run.id)).toBeVisible();
    expect(createRun).toHaveBeenCalledWith(taskId);
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
    });

    renderWithAppProviders(<StartRunAction taskId={taskId} />, client);
    await user.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText("Resource not found")).toBeVisible();
    expect(screen.getByText("The task was not found.")).toBeVisible();
  });
});
