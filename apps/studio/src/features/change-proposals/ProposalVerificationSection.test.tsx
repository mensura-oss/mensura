import type { ChangeProposal, ProposalVerification } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { ProposalVerificationSection } from "./ProposalVerificationSection";

describe("ProposalVerificationSection", () => {
  it("is absent until the proposal is approved", () => {
    renderWithAppProviders(
      <ProposalVerificationSection
        proposal={{ ...approvedProposal, status: "proposed", reviewedAt: null }}
      />,
      createTestClient(),
    );

    expect(screen.queryByText("Proposal verification")).toBeNull();
  });

  it("verifies an approved proposal and shows sandbox, guard, and safe diff results", async () => {
    const user = userEvent.setup();
    const verify = vi.fn(() => Promise.resolve(passedVerification));
    const client = createTestClient({ verifyChangeProposal: verify });

    renderWithAppProviders(
      <ProposalVerificationSection proposal={approvedProposal} />,
      client,
    );

    expect(await screen.findByText("Proposal verification")).toBeVisible();
    expect(
      screen.getByText(/live branch, working\s+tree, and repository files are never written/),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Verify (direct)" }),
    );

    expect(verify).toHaveBeenCalledWith(approvedProposal.id);
    expect(
      await screen.findByText(/materialized cleanly in the temporary sandbox/),
    ).toBeVisible();
    expect(screen.getByText(/Temporary Git worktree of commit/)).toBeVisible();
    expect(screen.getByText("abcdef123456")).toBeVisible();
    expect(screen.getByText(/1\/1\s*applied/)).toBeVisible();
    expect(screen.getByText("Applied in sandbox")).toBeVisible();
    expect(screen.getByText("Guard in sandbox")).toBeVisible();
    expect(screen.getByText(/2 passed · 0 failed/)).toBeVisible();
    expect(
      screen.getByText(/The live repository remains untouched/),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Verify again (direct)" }),
    ).toBeEnabled();
  });

  it("shows a failed guard outcome from an existing verification artifact", async () => {
    const client = createTestClient({
      listChangeProposalVerifications: () =>
        Promise.resolve({ items: [failedVerification], total: 1 }),
    });

    renderWithAppProviders(
      <ProposalVerificationSection proposal={approvedProposal} />,
      client,
    );

    expect(
      await screen.findByText(/but Guard failed against it/),
    ).toBeVisible();
    expect(screen.getByText(/0 passed · 2 failed/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Verify again (direct)" }),
    ).toBeEnabled();
  });

  it("surfaces RFC 9457 verification problems without hiding the action", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      verifyChangeProposal: () =>
        Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:not-a-git-repository",
            title: "Not a Git repository",
            status: 422,
            detail: "Workspace root path '/tmp/example' is not a Git repository.",
          }),
        ),
    });

    renderWithAppProviders(
      <ProposalVerificationSection proposal={approvedProposal} />,
      client,
    );
    await user.click(
      await screen.findByRole("button", { name: "Verify (direct)" }),
    );

    expect(await screen.findByText("Not a Git repository")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Verify (direct)" }),
    ).toBeEnabled();
  });
});

const contextPackId = `sha256:${"b".repeat(64)}` as const;
const digest = `sha256:${"c".repeat(64)}` as const;

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
      afterDigest: digest,
      proposedText: "print('proposed output')",
      proposedTextBytes: 24,
      originalTextBytes: 24,
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
  fileResults: [
    {
      path: "src/example.py",
      changeType: "modify",
      beforeDigest: digest,
      afterDigest: digest,
      sandboxDigest: digest,
      appliedInSandbox: true,
      reason: "applied",
    },
  ],
  safeDiff: {
    filesTotal: 1,
    createdCount: 0,
    modifiedCount: 1,
    deletedCount: 0,
    appliedCount: 1,
    unappliedCount: 0,
    proposedBytesTotal: 24,
  },
  createdAt: "2026-07-20T15:06:00Z",
  finishedAt: "2026-07-20T15:06:03Z",
  durationMs: 3_000,
};

const failedVerification: ProposalVerification = {
  ...passedVerification,
  id: "5f7f8f57-8f4f-4a5c-9d34-49e2a2e1a111",
  status: "failed",
  outcome: "guard_failed",
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
