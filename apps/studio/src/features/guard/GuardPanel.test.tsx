import type { GuardRunResponse } from "@mensura/shared-types";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { GuardPanel } from "./GuardPanel";

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";

const passedRun: GuardRunResponse = {
  id: "cce3fd08-ea41-45b0-ac24-d0349acb18b8",
  workspaceId,
  status: "passed",
  blocking: false,
  summary: {
    totalCount: 2,
    passedCount: 2,
    failedCount: 0,
    errorCount: 0,
    blockingFailures: 0,
    isBlocking: false,
  },
  checks: [
    {
      kind: "lint",
      status: "passed",
      blocking: true,
      summary: "Lint passed.",
      command: ["python", "-m", "ruff", "check", "."],
      exitCode: 0,
      durationMs: 120,
      stdout: "[]\n",
      stderr: "",
      outputTruncated: false,
    },
    {
      kind: "test",
      status: "passed",
      blocking: true,
      summary: "Tests passed.",
      command: ["python", "-m", "pytest", "-q"],
      exitCode: 0,
      durationMs: 880,
      stdout: "34 passed\n",
      stderr: "",
      outputTruncated: false,
    },
  ],
  startedAt: "2026-07-19T13:00:00Z",
  completedAt: "2026-07-19T13:00:01Z",
  durationMs: 1000,
};

function noRunError() {
  return new CoreApiError({
    type: "urn:mensura:problem:guard-run-not-found",
    title: "Guard run not found",
    status: 404,
    detail: "No completed Guard run exists for this workspace.",
  });
}

describe("GuardPanel", () => {
  it("does not request Guard state without an active workspace", () => {
    const getLatestGuardRun = vi.fn(() => Promise.resolve(passedRun));
    const client = createTestClient({ getLatestGuardRun });

    renderWithAppProviders(<GuardPanel activeWorkspaceId={null} />, client);

    expect(
      screen.getByText("Select an active workspace to run Guard checks."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Run checks" })).toBeNull();
    expect(getLatestGuardRun).not.toHaveBeenCalled();
  });

  it("shows an expected empty state when no completed run exists", async () => {
    const client = createTestClient({
      getLatestGuardRun: () => Promise.reject(noRunError()),
    });

    renderWithAppProviders(
      <GuardPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(
      await screen.findByText(
        "No Guard run yet. Run the configured lint and test checks.",
      ),
    ).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("runs checks manually and renders the passing result", async () => {
    const user = userEvent.setup();
    let latestRun: GuardRunResponse | null = null;
    let resolveRun: (run: GuardRunResponse) => void = () => undefined;
    const pendingRun = new Promise<GuardRunResponse>((resolve) => {
      resolveRun = resolve;
    });
    const createGuardRun = vi.fn(() => pendingRun);
    const client = createTestClient({
      createGuardRun,
      getLatestGuardRun: () =>
        latestRun ? Promise.resolve(latestRun) : Promise.reject(noRunError()),
    });

    renderWithAppProviders(
      <GuardPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    await screen.findByText("No Guard run yet. Run the configured lint and test checks.");
    await user.click(screen.getByRole("button", { name: "Run checks" }));
    expect(screen.getByRole("button", { name: "Running checks…" })).toBeDisabled();
    expect(
      screen.getByText("Core is running configured lint and test commands…"),
    ).toBeVisible();

    latestRun = passedRun;
    resolveRun(passedRun);

    expect(await screen.findByText("Passed", { selector: "strong" })).toBeVisible();
    expect(screen.getByText("Non-blocking")).toBeVisible();
    expect(screen.getByText("Lint passed.")).toBeVisible();
    expect(screen.getByText("Tests passed.")).toBeVisible();
    expect(screen.getAllByText("Captured output")).toHaveLength(2);
    expect(createGuardRun).toHaveBeenCalledWith(workspaceId, {});
    expect(
      within(screen.getByText("Passed", { selector: "dt" }).parentElement!).getByText(
        "2",
      ),
    ).toBeVisible();
  });

  it("makes a blocking failure obvious and keeps output compact", async () => {
    const failedRun: GuardRunResponse = {
      ...passedRun,
      status: "failed",
      blocking: true,
      summary: {
        totalCount: 1,
        passedCount: 0,
        failedCount: 1,
        errorCount: 0,
        blockingFailures: 1,
        isBlocking: true,
      },
      checks: [
        {
          ...passedRun.checks[0]!,
          status: "failed",
          summary: "Lint failed with 2 diagnostics.",
          exitCode: 1,
          outputTruncated: true,
        },
      ],
    };
    const client = createTestClient({
      getLatestGuardRun: () => Promise.resolve(failedRun),
    });

    renderWithAppProviders(
      <GuardPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    expect(await screen.findByText("Failed", { selector: "strong" })).toBeVisible();
    expect(screen.getByText("Blocking")).toBeVisible();
    expect(screen.getByText("Lint failed with 2 diagnostics.")).toBeVisible();
    expect(screen.getByText("output truncated")).toBeVisible();
    expect(screen.getByText("Captured output").closest("details")).not.toHaveAttribute(
      "open",
    );
  });

  it("surfaces configuration problems next to the manual action", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      createGuardRun: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:guard-configuration-not-found",
            title: "Guard configuration not found",
            status: 404,
            detail: "Create .mensura/guard.json before running checks.",
          }),
        ),
      getLatestGuardRun: () => Promise.reject(noRunError()),
    });

    renderWithAppProviders(
      <GuardPanel activeWorkspaceId={workspaceId} />,
      client,
    );

    await screen.findByText("No Guard run yet. Run the configured lint and test checks.");
    await user.click(screen.getByRole("button", { name: "Run checks" }));

    expect(await screen.findByText("Guard configuration not found")).toBeVisible();
    expect(
      screen.getByText("urn:mensura:problem:guard-configuration-not-found"),
    ).toBeVisible();
  });
});
