import type { Workspace } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestClient, renderWithAppProviders } from "../../test/render";
import { WorkspacesPanel } from "./WorkspacesPanel";

const createdWorkspace: Workspace = {
  id: "64e1bdad-dc85-45e0-92bd-0327dde5e398",
  name: "Mensura",
  rootPath: "/code/mensura",
  createdAt: "2026-07-19T11:00:00Z",
  updatedAt: "2026-07-19T11:00:00Z",
};

describe("WorkspacesPanel", () => {
  it("renders the empty state and creates a workspace", async () => {
    const user = userEvent.setup();
    let items: readonly Workspace[] = [];
    const listWorkspaces = vi.fn(() =>
      Promise.resolve({ items, total: items.length }),
    );
    const createWorkspace = vi.fn(() => {
      items = [createdWorkspace];
      return Promise.resolve(createdWorkspace);
    });
    const client = createTestClient({ createWorkspace, listWorkspaces });

    renderWithAppProviders(<WorkspacesPanel />, client);

    expect(await screen.findByText(/No workspaces yet/)).toBeVisible();
    await user.type(screen.getByLabelText("Name"), "Mensura");
    await user.type(screen.getByLabelText("Root path"), "/code/mensura");
    await user.click(screen.getByRole("button", { name: "Create workspace" }));

    expect(await screen.findByText("/code/mensura")).toBeVisible();
    expect(createWorkspace).toHaveBeenCalledWith({
      name: "Mensura",
      rootPath: "/code/mensura",
    });
    expect(listWorkspaces).toHaveBeenCalledTimes(2);
  });
});
