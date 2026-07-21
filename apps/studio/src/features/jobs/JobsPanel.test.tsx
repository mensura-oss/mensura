import type { Job } from "@mensura/shared-types";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { JobsPanel } from "./JobsPanel";

const baseJob: Job = {
  id: "11111111-2222-3333-4444-555555555555",
  schemaVersion: "1",
  jobType: "proposal_verification",
  targetEntityType: "change_proposal",
  targetEntityId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  workspaceId: "99999999-8888-7777-6666-555555555555",
  status: "succeeded",
  attemptCount: 1,
  payload: {
    proposalId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    verificationId: null,
    applicationId: null,
    label: null,
  },
  resultEntityType: "verification",
  resultEntityId: "cccccccc-dddd-eeee-ffff-000000000000",
  lastError: null,
  createdAt: "2026-07-21T12:00:00Z",
  startedAt: "2026-07-21T12:00:01Z",
  finishedAt: "2026-07-21T12:00:05Z",
};

const failedJob: Job = {
  ...baseJob,
  id: "22222222-3333-4444-5555-666666666666",
  jobType: "application_apply",
  status: "failed",
  resultEntityType: null,
  resultEntityId: null,
  lastError: "Live working tree drifted from the verified basis.",
};

describe("JobsPanel", () => {
  it("renders jobs with status, type, and result", async () => {
    const client = createTestClient({
      listJobs: () => Promise.resolve({ items: [baseJob, failedJob], total: 2 }),
    });

    renderWithAppProviders(<JobsPanel />, client);

    expect(await screen.findByText("Verify proposal")).toBeInTheDocument();
    expect(screen.getByText("Apply proposal")).toBeInTheDocument();
    expect(screen.getByText("succeeded")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(
      screen.getByText(/Produced verification cccccccc/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Live working tree drifted from the verified basis."),
    ).toBeInTheDocument();
  });

  it("shows an empty state when there are no jobs", async () => {
    const client = createTestClient({
      listJobs: () => Promise.resolve({ items: [], total: 0 }),
    });

    renderWithAppProviders(<JobsPanel />, client);

    expect(
      await screen.findByText("No background jobs yet."),
    ).toBeInTheDocument();
  });

  it("enqueues a backup job when the queue button is clicked", async () => {
    const enqueueJob = vi.fn(() =>
      Promise.resolve({
        ...baseJob,
        id: "33333333-4444-5555-6666-777777777777",
        jobType: "backup_create",
        targetEntityType: "database",
        targetEntityId: null,
        status: "queued",
        startedAt: null,
        finishedAt: null,
        resultEntityType: null,
        resultEntityId: null,
      } as Job),
    );
    const client = createTestClient({
      listJobs: () => Promise.resolve({ items: [], total: 0 }),
      enqueueJob,
    });

    renderWithAppProviders(<JobsPanel />, client);
    await screen.findByText("No background jobs yet.");

    await userEvent.click(screen.getByRole("button", { name: "Queue backup job" }));

    await waitFor(() =>
      expect(enqueueJob).toHaveBeenCalledWith({ jobType: "backup_create" }),
    );
  });

  it("surfaces a problem when the jobs list fails to load", async () => {
    const client = createTestClient({
      listJobs: () =>
        Promise.reject(
          new CoreApiError({
            type: "about:blank",
            title: "Internal Server Error",
            status: 500,
            detail: "The server could not complete the request.",
            instance: "/api/v1/jobs",
          }),
        ),
    });

    renderWithAppProviders(<JobsPanel />, client);

    expect(
      await screen.findByText("The server could not complete the request."),
    ).toBeInTheDocument();
  });
});
