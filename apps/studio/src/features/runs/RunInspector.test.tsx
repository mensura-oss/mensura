import type { Run } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { RunInspector } from "./RunInspector";

describe("RunInspector", () => {
  it("renders a queued run returned by Core", async () => {
    const user = userEvent.setup();
    const runId = "e95261af-3350-4e02-98bf-5048d465619e";
    const contextPackId = `sha256:${"b".repeat(64)}` as const;
    const client = createTestClient({
      getRun: () =>
        Promise.resolve({
          id: runId,
          taskId: "7ac70b2e-bd14-41ba-9087-02b46eb7b703",
          contextPackId,
          contextPack: {
            id: contextPackId,
            workspaceId: "5ca252af-76f4-4aed-9718-ff97b610ce90",
            inventoryId: "f6b3c0c2-42a1-4a4d-81f3-82918af050ae",
            schemaVersion: "1" as const,
            fileCount: 3,
            totalFileBytes: 4096,
            totalPreviewBytes: 1536,
          },
          status: "queued",
          execution: null,
          startedAt: null,
          finishedAt: null,
          createdAt: "2026-07-19T11:00:00Z",
          updatedAt: "2026-07-19T11:00:00Z",
        }),
    });

    renderWithAppProviders(<RunInspector />, client);
    await user.type(screen.getByLabelText("Run ID"), runId);
    await user.click(screen.getByRole("button", { name: "Inspect" }));

    expect((await screen.findAllByText("queued"))[0]).toBeVisible();
    expect(
      screen.getByText("7ac70b2e-bd14-41ba-9087-02b46eb7b703"),
    ).toBeVisible();
    expect(screen.getByText(contextPackId)).toBeVisible();
    expect(screen.getByText("3")).toBeVisible();
    expect(screen.getByText("4,096")).toBeVisible();
    expect(screen.getByRole("button", { name: "Execute run" })).toBeEnabled();
  });

  it("shows the running request state and renders a bounded successful result", async () => {
    const user = userEvent.setup();
    const queued = makeRun("queued");
    const succeeded = makeRun("succeeded");
    let latest = queued;
    let resolveExecution!: (run: Run) => void;
    const execution = new Promise<Run>((resolve) => {
      resolveExecution = resolve;
    });
    const executeRun = vi.fn(() =>
      execution.then((run) => {
        latest = run;
        return run;
      }),
    );
    const client = createTestClient({
      getRun: () => Promise.resolve(latest),
      executeRun,
    });

    renderWithAppProviders(<RunInspector />, client);
    await user.type(screen.getByLabelText("Run ID"), queued.id);
    await user.click(screen.getByRole("button", { name: "Inspect" }));
    await user.click(await screen.findByRole("button", { name: "Execute run" }));

    expect(screen.getByRole("button", { name: "Execution running…" })).toBeDisabled();
    expect(
      screen.getByText(/Core is running the provider against the immutable/),
    ).toBeVisible();
    expect(screen.getAllByText("running").length).toBeGreaterThan(0);

    resolveExecution(succeeded);

    expect(await screen.findByText("mensura.builtin")).toBeVisible();
    expect(screen.getByText(/deterministic-review/)).toBeVisible();
    expect(screen.getByText("Review immutable evidence.")).toBeVisible();
    expect(screen.getByText(/Languages: Python/)).toBeVisible();
    expect(screen.getByText("No provider warnings.")).toBeVisible();
    expect(screen.getByText("Review the result.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Execute run" })).toBeNull();
    expect(executeRun).toHaveBeenCalledWith(queued.id);
  });

  it("shows RFC 9457 execution errors beside the persisted failed result", async () => {
    const user = userEvent.setup();
    const queued = makeRun("queued");
    const failed = makeRun("failed");
    let latest = queued;
    const client = createTestClient({
      getRun: () => Promise.resolve(latest),
      executeRun: () => {
        latest = failed;
        return Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:provider-execution-failed",
            title: "Provider execution failed",
            status: 502,
            detail: `Provider execution failed for run '${queued.id}'.`,
          }),
        );
      },
    });

    renderWithAppProviders(<RunInspector />, client);
    await user.type(screen.getByLabelText("Run ID"), queued.id);
    await user.click(screen.getByRole("button", { name: "Inspect" }));
    await user.click(await screen.findByRole("button", { name: "Execute run" }));

    expect((await screen.findAllByText("Provider execution failed"))[0]).toBeVisible();
    expect(
      screen.getByText("The provider adapter could not complete this execution."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Execute run" })).toBeNull();
  });
});

const runId = "e95261af-3350-4e02-98bf-5048d465619e";
const contextPackId = `sha256:${"b".repeat(64)}` as const;

function makeRun(status: "queued" | "succeeded" | "failed"): Run {
  const base: Omit<Run, "status" | "execution" | "startedAt" | "finishedAt"> = {
    id: runId,
    taskId: "7ac70b2e-bd14-41ba-9087-02b46eb7b703",
    contextPackId,
    contextPack: {
      id: contextPackId,
      workspaceId: "5ca252af-76f4-4aed-9718-ff97b610ce90",
      inventoryId: "f6b3c0c2-42a1-4a4d-81f3-82918af050ae",
      schemaVersion: "1",
      fileCount: 3,
      totalFileBytes: 4096,
      totalPreviewBytes: 1536,
    },
    createdAt: "2026-07-19T11:00:00Z",
    updatedAt: "2026-07-19T11:00:01Z",
  };
  if (status === "queued") {
    return {
      ...base,
      status,
      execution: null,
      startedAt: null,
      finishedAt: null,
    };
  }

  const provider = {
    providerId: "mensura.builtin",
    adapterId: "deterministic-review",
    adapterVersion: "1.0.0",
    model: null,
  };
  if (status === "failed") {
    return {
      ...base,
      status,
      startedAt: "2026-07-19T11:00:00Z",
      finishedAt: "2026-07-19T11:00:01Z",
      execution: {
        provider,
        durationMs: 12,
        result: null,
        failure: {
          code: "provider_execution_failed",
          summary: "The provider adapter could not complete this execution.",
        },
      },
    };
  }
  return {
    ...base,
    status,
    startedAt: "2026-07-19T11:00:00Z",
    finishedAt: "2026-07-19T11:00:01Z",
    execution: {
      provider,
      durationMs: 12,
      failure: null,
      result: {
        schemaVersion: "1",
        taskSummary: "Review immutable evidence.",
        interpretedIntent: "Inspect the selected files without changing them.",
        context: {
          contextPackId,
          inventoryId: base.contextPack.inventoryId,
          fileCount: 3,
          textFileCount: 3,
          binaryFileCount: 0,
          totalFileBytes: 4096,
          totalPreviewBytes: 1536,
          truncatedTextFileCount: 0,
          languages: ["Python"],
        },
        warnings: [],
        recommendedNextSteps: ["Review the result."],
      },
    },
  };
}
