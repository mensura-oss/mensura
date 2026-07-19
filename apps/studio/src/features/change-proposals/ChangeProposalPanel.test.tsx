import type { ChangeProposal, Run } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { ChangeProposalPanel } from "./ChangeProposalPanel";

describe("ChangeProposalPanel", () => {
  it("reopens bounded file details and records approval without apply language", async () => {
    const user = userEvent.setup();
    const approve = vi.fn(() =>
      Promise.resolve({
        ...proposal,
        status: "approved" as const,
        reviewedAt: "2026-07-19T15:01:00Z",
      }),
    );
    const client = createTestClient({
      listChangeProposals: () => Promise.resolve({ items: [proposal], total: 1 }),
      approveChangeProposal: approve,
    });

    renderWithAppProviders(<ChangeProposalPanel run={run} />, client);

    expect(await screen.findByText("Update the bounded example.")).toBeVisible();
    expect(screen.getByText(/will not apply, stage, commit/)).toBeVisible();
    expect(screen.getByText("print('proposed output')")).not.toBeVisible();
    await user.click(screen.getByText("src/example.py"));
    expect(screen.getByText("print('proposed output')")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Approve proposal" }));

    expect(await screen.findByText(/No repository changes were applied/)).toBeVisible();
    expect(approve).toHaveBeenCalledWith(proposal.id);
    expect(screen.queryByRole("button", { name: "Reject proposal" })).toBeNull();
  });

  it("creates an idempotent artifact and can explicitly reject it", async () => {
    const user = userEvent.setup();
    const create = vi.fn(() => Promise.resolve({ proposal, created: true }));
    const reject = vi.fn(() =>
      Promise.resolve({
        ...proposal,
        status: "rejected" as const,
        reviewedAt: "2026-07-19T15:02:00Z",
      }),
    );
    const client = createTestClient({
      listChangeProposals: () => Promise.resolve({ items: [], total: 0 }),
      createChangeProposal: create,
      rejectChangeProposal: reject,
    });

    renderWithAppProviders(<ChangeProposalPanel run={run} />, client);
    await user.click(await screen.findByRole("button", { name: "Create proposal" }));

    expect(await screen.findByText(proposal.summary)).toBeVisible();
    expect(create).toHaveBeenCalledWith(run.id);
    await user.click(screen.getByRole("button", { name: "Reject proposal" }));
    expect(await screen.findByText(/Review recorded as/)).toBeVisible();
    expect(reject).toHaveBeenCalledWith(proposal.id);
  });

  it("surfaces an RFC 9457 creation problem without hiding the run", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      listChangeProposals: () => Promise.resolve({ items: [], total: 0 }),
      createChangeProposal: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:change-proposal-output-invalid",
            title: "Change proposal output is invalid",
            status: 422,
            detail: "The stored proposal contains an unsafe path.",
          }),
        ),
    });

    renderWithAppProviders(<ChangeProposalPanel run={run} />, client);
    await user.click(await screen.findByRole("button", { name: "Create proposal" }));

    expect(await screen.findByText("Change proposal output is invalid")).toBeVisible();
    expect(screen.getByText("The stored proposal contains an unsafe path.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Create proposal" })).toBeEnabled();
  });
});

const contextPackId = `sha256:${"b".repeat(64)}` as const;
const beforeDigest = `sha256:${"c".repeat(64)}` as const;
const afterDigest = `sha256:${"d".repeat(64)}` as const;

const run: Run = {
  id: "d384b8df-9da6-4df0-b5ec-76e3ed6a9e17",
  taskId: "76f8e15a-c555-45f6-96f1-bdb2234731fc",
  contextPackId,
  contextPack: {
    id: contextPackId,
    workspaceId: "54bad86e-0030-4a67-877f-c4f209f4c83e",
    inventoryId: "01949000-63df-447d-b212-6db48c731d0a",
    schemaVersion: "1",
    fileCount: 1,
    totalFileBytes: 24,
    totalPreviewBytes: 24,
  },
  status: "succeeded",
  startedAt: "2026-07-19T15:00:00Z",
  finishedAt: "2026-07-19T15:00:01Z",
  createdAt: "2026-07-19T15:00:00Z",
  updatedAt: "2026-07-19T15:00:01Z",
  execution: {
    provider: {
      providerId: "mensura.builtin",
      providerKind: "deterministic",
      adapterId: "deterministic-review",
      adapterVersion: "1.0.0",
      model: null,
      promptVersion: "review.v2",
    },
    durationMs: 1,
    failure: null,
    result: {
      schemaVersion: "2",
      taskSummary: "Update the example.",
      interpretedIntent: "Propose one bounded edit.",
      context: {
        contextPackId,
        inventoryId: "01949000-63df-447d-b212-6db48c731d0a",
        fileCount: 1,
        textFileCount: 1,
        binaryFileCount: 0,
        totalFileBytes: 24,
        totalPreviewBytes: 24,
        truncatedTextFileCount: 0,
        languages: ["Python"],
      },
      warnings: [],
      recommendedNextSteps: ["Review the proposal."],
      proposalDraft: {
        summary: "Update the bounded example.",
        rationale: "The immutable evidence supports this suggestion.",
        fileChanges: [],
      },
    },
  },
};

const proposal: ChangeProposal = {
  id: "16c031b4-d65d-4e20-964f-ded028adca33",
  schemaVersion: "1",
  runId: run.id,
  taskId: run.taskId,
  workspaceId: run.contextPack.workspaceId,
  contextPackId,
  providerId: "mensura.builtin",
  promptVersion: "review.v2",
  status: "proposed",
  createdAt: "2026-07-19T15:00:02Z",
  reviewedAt: null,
  summary: "Update the bounded example.",
  rationale: "The immutable task and captured text identify this file.",
  fileChanges: [
    {
      path: "src/example.py",
      changeType: "modify",
      language: "Python",
      beforeDigest,
      afterDigest,
      proposedText: "print('proposed output')",
      proposedTextBytes: 24,
      originalTextBytes: 24,
      truncated: false,
    },
  ],
};
