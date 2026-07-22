import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WorkspaceTask } from "./localTaskBoard";
import { TaskBoardPanel } from "./TaskBoardPanel";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";

const tasks: WorkspaceTask[] = [
  { id: "t1", title: "Draft the plan", status: "draft" },
  { id: "t2", title: "Running now", status: "running" },
  { id: "t3", title: "All done", description: "Shipped it.", status: "approved" },
];

function column(title: string): HTMLElement {
  return screen
    .getByText(title)
    .closest(".workspace-board__column") as HTMLElement;
}

describe("TaskBoardPanel", () => {
  it("groups tasks into Backlog / In progress / Done columns", () => {
    render(<TaskBoardPanel workspaceId={workspaceId} tasks={tasks} />);

    expect(within(column("Backlog")).getByText("Draft the plan")).toBeVisible();
    expect(within(column("In progress")).getByText("Running now")).toBeVisible();
    expect(within(column("Done")).getByText("All done")).toBeVisible();
    expect(screen.getByText("Shipped it.")).toBeVisible();
    // Each card keeps its exact status badge.
    expect(screen.getByText("approved")).toBeVisible();
  });

  it("shows a clear empty state when there are no tasks", () => {
    render(<TaskBoardPanel workspaceId={workspaceId} tasks={[]} />);

    expect(screen.getByText("No tasks yet for this workspace.")).toBeVisible();
    expect(screen.queryByText("Backlog")).not.toBeInTheDocument();
  });

  it("falls back to deterministic local placeholder tasks", () => {
    render(<TaskBoardPanel workspaceId={workspaceId} />);

    expect(screen.getByText("Index the repository into Vault")).toBeVisible();
    expect(
      screen.getByText(
        "Illustrative local tasks — not yet connected to Core tasks or runs.",
      ),
    ).toBeVisible();
  });
});
