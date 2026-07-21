import type {
  ApplicationArtifact,
  ChangeProposal,
  ProposalVerification,
} from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { ProposalApplicationSection } from "./ProposalApplicationSection";

describe("ProposalApplicationSection", () => {
  it("is absent until the proposal is approved", () => {
    renderWithAppProviders(
      <ProposalApplicationSection
        proposal={{ ...approvedProposal, status: "proposed", reviewedAt: null }}
      />,
      createTestClient(),
    );

    expect(
      screen.queryByRole("heading", { name: "Apply to live working tree" }),
    ).toBeNull();
  });

  it("applies verified content to the live tree and shows the result", async () => {
    const user = userEvent.setup();
    const applyChangeProposal = vi.fn(() => Promise.resolve(passedApplication));
    const client = createTestClient({
      applyChangeProposal,
      listChangeProposalVerifications: () =>
        Promise.resolve({ items: [passedVerification], total: 1 }),
    });

    renderWithAppProviders(
      <ProposalApplicationSection proposal={approvedProposal} />,
      client,
    );

    expect(
      await screen.findByText(
        /does not commit, stage, or push, and no model provider is involved/,
      ),
    ).toBeVisible();
    const applyButton = await screen.findByRole("button", {
      name: "Apply (direct)",
    });
    await user.click(applyButton);

    expect(applyChangeProposal).toHaveBeenCalledWith(approvedProposal.id, {
      verificationId: passedVerification.id,
    });
    expect(
      await screen.findByText(
        /written to the live working tree and Guard passed/,
      ),
    ).toBeVisible();
    expect(screen.getByText("Guard on live tree")).toBeVisible();
    expect(screen.getByText(/2 passed · 0 failed/)).toBeVisible();
    expect(screen.getByText(/Restoration data captured for 1 file/)).toBeVisible();
    expect(
      screen.getByText(/No commit, stage, or push was performed/),
    ).toBeVisible();
  });

  it("blocks applying until a verification passes", async () => {
    renderWithAppProviders(
      <ProposalApplicationSection proposal={approvedProposal} />,
      createTestClient(),
    );

    expect(
      await screen.findByText(/unavailable until this approved proposal has a passing/),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Apply (direct)" }),
    ).toBeNull();
  });

  it("renders an existing application with a live Guard failure", async () => {
    const client = createTestClient({
      listWorkspaceApplications: () =>
        Promise.resolve({ items: [guardFailedApplication], total: 1 }),
    });

    renderWithAppProviders(
      <ProposalApplicationSection proposal={approvedProposal} />,
      client,
    );

    expect(
      await screen.findByText(/but Guard failed against it/),
    ).toBeVisible();
    expect(screen.getByText(/0 passed · 2 failed/)).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Apply (direct)" }),
    ).toBeNull();
  });

  it("surfaces RFC 9457 drift problems without hiding the action", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      listChangeProposalVerifications: () =>
        Promise.resolve({ items: [passedVerification], total: 1 }),
      applyChangeProposal: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:application-live-drift",
            title: "Live working tree drifted from the verified basis",
            status: 409,
            detail:
              "Live file 'src/example.py' has drifted from the verified materialization basis.",
          }),
        ),
    });

    renderWithAppProviders(
      <ProposalApplicationSection proposal={approvedProposal} />,
      client,
    );
    await user.click(
      await screen.findByRole("button", { name: "Apply (direct)" }),
    );

    expect(
      await screen.findByText("Live working tree drifted from the verified basis"),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Apply (direct)" }),
    ).toBeEnabled();
  });
});

const contextPackId = `sha256:${"b".repeat(64)}` as const;
const digest = `sha256:${"c".repeat(64)}` as const;
const appliedDigest = `sha256:${"d".repeat(64)}` as const;

const approvedProposal: ChangeProposal = {
  id: "16c031b4-d65d-4e20-964f-ded028adca33",
  schemaVersion: "1",
  runId: "d384b8df-9da6-4df0-b5ec-76e3ed6a9e17",
  taskId: "76f8e15a-c555-45f6-96f1-bdb2234731fc",
  workspaceId: "54bad86e-0030-4a67-877f-c4f209f4c83e",
  contextPackId,
  providerId: "mensura.builtin",
  promptVersion: "review.v2",
  status: "approved",
  createdAt: "2026-07-20T15:00:02Z",
  reviewedAt: "2026-07-20T15:05:00Z",
  summary: "Update the bounded example.",
  rationale: "The immutable task and captured text identify this file.",
  fileChanges: [
    {
      path: "src/example.py",
      changeType: "modify",
      language: "Python",
      beforeDigest: digest,
      afterDigest: appliedDigest,
      proposedText: "print('applied output')",
      proposedTextBytes: 23,
      originalTextBytes: 23,
      truncated: false,
    },
  ],
};

const passedVerification: ProposalVerification = {
  id: "e35a1f57-13b1-4d6a-b4b5-2b71ecb18b6e",
  schemaVersion: "1",
  proposalId: approvedProposal.id,
  runId: approvedProposal.runId,
  taskId: approvedProposal.taskId,
  workspaceId: approvedProposal.workspaceId,
  contextPackId,
  status: "passed",
  outcome: "sandbox_verified",
  sandbox: {
    kind: "git_worktree",
    commitId: `abcdef123456${"0".repeat(28)}`,
    cleanupCompleted: true,
  },
  guard: null,
  fileResults: [],
  safeDiff: {
    filesTotal: 1,
    createdCount: 0,
    modifiedCount: 1,
    deletedCount: 0,
    appliedCount: 1,
    unappliedCount: 0,
    proposedBytesTotal: 23,
  },
  createdAt: "2026-07-20T15:06:00Z",
  finishedAt: "2026-07-20T15:06:03Z",
  durationMs: 3_000,
};

const passedApplication: ApplicationArtifact = {
  id: "9f2b6a10-2c8e-4a2f-9c1d-7f0a3b4c5d6e",
  schemaVersion: "1",
  proposalId: approvedProposal.id,
  verificationId: passedVerification.id,
  runId: approvedProposal.runId,
  taskId: approvedProposal.taskId,
  workspaceId: approvedProposal.workspaceId,
  contextPackId,
  status: "applied_guard_passed",
  target: {
    kind: "live_working_tree",
    liveCommitId: `abcdef123456${"0".repeat(28)}`,
    verificationCommitId: `abcdef123456${"0".repeat(28)}`,
    headMovedSinceVerification: false,
  },
  guard: {
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
        exitCode: 0,
        durationMs: 12,
        outputExcerpt: "",
        outputTruncated: false,
      },
      {
        kind: "test",
        status: "passed",
        blocking: true,
        summary: "Tests passed.",
        exitCode: 0,
        durationMs: 30,
        outputExcerpt: "2 passed",
        outputTruncated: false,
      },
    ],
  },
  guardUnavailableReason: null,
  fileResults: [
    {
      path: "src/example.py",
      changeType: "modify",
      beforeDigest: digest,
      liveBeforeDigest: digest,
      afterDigest: appliedDigest,
      appliedDigest,
      applied: true,
      reason: "applied",
    },
  ],
  summary: {
    filesTotal: 1,
    createdCount: 0,
    modifiedCount: 1,
    deletedCount: 0,
    appliedCount: 1,
    failedCount: 0,
  },
  undo: {
    strategy: "restore_prior_content",
    note: "Restore each prior digest to undo this application later.",
    capturedAt: "2026-07-20T15:10:00Z",
    files: [
      {
        path: "src/example.py",
        changeType: "modify",
        priorExisted: true,
        priorDigest: digest,
        priorContent: "print('immutable input')",
        priorContentBytes: 24,
        priorTruncated: false,
        appliedDigest,
      },
    ],
  },
  createdAt: "2026-07-20T15:10:00Z",
  finishedAt: "2026-07-20T15:10:02Z",
  durationMs: 2_000,
};

const guardFailedApplication: ApplicationArtifact = {
  ...passedApplication,
  id: "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  status: "applied_guard_failed",
  guard: {
    status: "failed",
    blocking: true,
    summary: {
      totalCount: 2,
      passedCount: 0,
      failedCount: 2,
      errorCount: 0,
      blockingFailures: 2,
      isBlocking: true,
    },
    checks: [
      {
        kind: "lint",
        status: "failed",
        blocking: true,
        summary: "Lint failed with 2 diagnostics.",
        exitCode: 1,
        durationMs: 15,
        outputExcerpt: "2 diagnostics",
        outputTruncated: false,
      },
      {
        kind: "test",
        status: "failed",
        blocking: true,
        summary: "Tests failed with exit code 1.",
        exitCode: 1,
        durationMs: 42,
        outputExcerpt: "1 failed",
        outputTruncated: false,
      },
    ],
  },
};
