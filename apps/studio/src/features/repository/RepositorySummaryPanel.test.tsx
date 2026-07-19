import type { RepositorySummary } from "@mensura/shared-types";
import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { RepositorySummaryPanel } from "./RepositorySummaryPanel";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";

const cleanSummary: RepositorySummary = {
  workspaceId,
  isRepository: true,
  branch: "main",
  isDirty: false,
  stagedCount: 0,
  unstagedCount: 0,
  untrackedCount: 0,
  changedPathsCount: 0,
  diffMetadata: [],
};

describe("RepositorySummaryPanel", () => {
  it("guides the user without requesting Core when no workspace is active", () => {
    const getWorkspaceRepository = vi.fn(() => Promise.resolve(cleanSummary));
    const client = createTestClient({ getWorkspaceRepository });

    renderWithAppProviders(
      <RepositorySummaryPanel activeWorkspaceId={null} />,
      client,
    );

    expect(
      screen.getByText("Select an active workspace to inspect its Git state."),
    ).toBeVisible();
    expect(getWorkspaceRepository).not.toHaveBeenCalled();
  });

  it("shows compact dirty counts and bounds the changed-path list", async () => {
    const diffMetadata: RepositorySummary["diffMetadata"] = Array.from(
      { length: 9 },
      (_, index) => ({
        path: `src/change-${index}.ts`,
        changeType: index === 8 ? "untracked" : "modified",
        staged: index === 0,
      }),
    );
    const client = createTestClient({
      getWorkspaceRepository: () =>
        Promise.resolve({
          ...cleanSummary,
          isDirty: true,
          stagedCount: 1,
          unstagedCount: 7,
          untrackedCount: 1,
          changedPathsCount: 9,
          diffMetadata,
        }),
    });

    renderWithAppProviders(
      <RepositorySummaryPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByText("Dirty")).toBeVisible();
    expect(screen.getByText("main")).toBeVisible();
    expect(within(screen.getByText("Staged").parentElement!).getByText("1")).toBeVisible();
    expect(
      within(screen.getByText("Unstaged").parentElement!).getByText("7"),
    ).toBeVisible();
    expect(screen.getByText("src/change-0.ts")).toBeVisible();
    expect(screen.queryByText("src/change-8.ts")).not.toBeInTheDocument();
    expect(screen.getByText("1 more metadata entry")).toBeVisible();
  });

  it("shows a clean detached repository explicitly", async () => {
    const client = createTestClient({
      getWorkspaceRepository: () =>
        Promise.resolve({ ...cleanSummary, branch: null }),
    });

    renderWithAppProviders(
      <RepositorySummaryPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByText("Detached HEAD")).toBeVisible();
    expect(screen.getByText("Clean")).toBeVisible();
    expect(screen.getByText("No local repository changes.")).toBeVisible();
  });

  it("surfaces a non-repository problem without throwing", async () => {
    const client = createTestClient({
      getWorkspaceRepository: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:not-a-git-repository",
            title: "Not a Git repository",
            status: 422,
            detail: "The selected workspace root is not a Git repository.",
          }),
        ),
    });

    renderWithAppProviders(
      <RepositorySummaryPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByText("Not a Git repository")).toBeVisible();
    expect(screen.getByText("422")).toBeVisible();
    expect(
      screen.getByText("urn:mensura:problem:not-a-git-repository"),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
  });
});
