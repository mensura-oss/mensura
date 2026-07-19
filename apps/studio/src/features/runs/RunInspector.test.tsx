import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { createTestClient, renderWithAppProviders } from "../../test/render";
import { RunInspector } from "./RunInspector";

describe("RunInspector", () => {
  it("renders a queued run returned by Core", async () => {
    const user = userEvent.setup();
    const runId = "e95261af-3350-4e02-98bf-5048d465619e";
    const client = createTestClient({
      getRun: () =>
        Promise.resolve({
          id: runId,
          taskId: "7ac70b2e-bd14-41ba-9087-02b46eb7b703",
          status: "queued",
          startedAt: null,
          finishedAt: null,
          createdAt: "2026-07-19T11:00:00Z",
          updatedAt: "2026-07-19T11:00:00Z",
        }),
    });

    renderWithAppProviders(<RunInspector />, client);
    await user.type(screen.getByLabelText("Run ID"), runId);
    await user.click(screen.getByRole("button", { name: "Inspect" }));

    expect(await screen.findByText("queued")).toBeVisible();
    expect(
      screen.getByText("7ac70b2e-bd14-41ba-9087-02b46eb7b703"),
    ).toBeVisible();
  });
});
