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
});
