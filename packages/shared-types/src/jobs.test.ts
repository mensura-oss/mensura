import { describe, expect, it } from "vitest";
import {
  JOB_SCHEMA_VERSION,
  JOB_STATUSES,
  JOB_TARGET_TYPES,
  JOB_TYPES,
} from "./jobs.js";
import type {
  EnqueueJobRequest,
  Job,
  JobCollection,
} from "./jobs.js";

describe("Job contracts", () => {
  const baseJob: Job = {
    id: "11111111-2222-3333-4444-555555555555",
    schemaVersion: "1",
    jobType: "proposal_verification",
    targetEntityType: "change_proposal",
    targetEntityId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    workspaceId: "99999999-8888-7777-6666-555555555555",
    status: "queued",
    attemptCount: 0,
    payload: {
      proposalId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      verificationId: null,
      applicationId: null,
      label: null,
    },
    resultEntityType: null,
    resultEntityId: null,
    lastError: null,
    createdAt: "2026-07-21T12:00:00Z",
    startedAt: null,
    finishedAt: null,
    retryOfJobId: null,
    rootJobId: null,
    retryEligible: true,
    retryCount: 0,
  };

  it("pins JOB_SCHEMA_VERSION to 1", () => {
    expect(JOB_SCHEMA_VERSION).toBe("1");
  });

  it("has a closed JobStatus set", () => {
    expect(JOB_STATUSES).toEqual(["queued", "running", "succeeded", "failed"]);
  });

  it("has a closed JobType set covering the four queued operations", () => {
    expect(JOB_TYPES).toEqual([
      "proposal_verification",
      "application_apply",
      "application_undo",
      "backup_create",
    ]);
  });

  it("has a closed JobTargetType set", () => {
    expect(JOB_TARGET_TYPES).toEqual([
      "change_proposal",
      "application",
      "database",
    ]);
  });

  it("validates a queued job with only reference-data payload", () => {
    expect(baseJob.status).toBe("queued");
    expect(baseJob.startedAt).toBeNull();
    expect(baseJob.finishedAt).toBeNull();
    expect(baseJob.resultEntityId).toBeNull();
    expect(baseJob.payload.proposalId).toBe(baseJob.targetEntityId);
  });

  it("validates a succeeded job that references its produced artifact", () => {
    const job: Job = {
      ...baseJob,
      status: "succeeded",
      attemptCount: 1,
      startedAt: "2026-07-21T12:00:01Z",
      finishedAt: "2026-07-21T12:00:05Z",
      resultEntityType: "verification",
      resultEntityId: "cccccccc-dddd-eeee-ffff-000000000000",
    };

    expect(job.status).toBe("succeeded");
    expect(job.resultEntityId).toBeTruthy();
    expect(job.lastError).toBeNull();
  });

  it("validates a failed job with a bounded lastError summary", () => {
    const job: Job = {
      ...baseJob,
      status: "failed",
      attemptCount: 1,
      startedAt: "2026-07-21T12:00:01Z",
      finishedAt: "2026-07-21T12:00:02Z",
      lastError: "Live working tree drifted from the verified basis.",
    };

    expect(job.status).toBe("failed");
    expect(job.lastError).toBeTruthy();
    expect(job.resultEntityId).toBeNull();
  });

  it("validates a backup job with no target entity id", () => {
    const job: Job = {
      ...baseJob,
      jobType: "backup_create",
      targetEntityType: "database",
      targetEntityId: null,
      workspaceId: null,
      payload: {
        proposalId: null,
        verificationId: null,
        applicationId: null,
        label: "nightly",
      },
    };

    expect(job.targetEntityId).toBeNull();
    expect(job.payload.label).toBe("nightly");
  });

  it("accepts each enqueue request shape", () => {
    const requests: EnqueueJobRequest[] = [
      { jobType: "proposal_verification", proposalId: baseJob.id },
      {
        jobType: "application_apply",
        proposalId: baseJob.id,
        verificationId: baseJob.id,
      },
      { jobType: "application_undo", applicationId: baseJob.id },
      { jobType: "backup_create", label: "nightly" },
      { jobType: "backup_create" },
    ];

    expect(requests).toHaveLength(5);
    expect(requests[0]?.jobType).toBe("proposal_verification");
  });

  it("validates an empty and populated job collection", () => {
    const empty: JobCollection = { items: [], total: 0 };
    const populated: JobCollection = { items: [baseJob], total: 1 };

    expect(empty.items).toHaveLength(0);
    expect(populated.items[0]?.id).toBe(baseJob.id);
    expect(populated.total).toBe(1);
  });

  it("validates a retry child job with parent and root linkage", () => {
    const retryJob: Job = {
      ...baseJob,
      retryOfJobId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      rootJobId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      retryEligible: true,
      retryCount: 0,
    };

    expect(retryJob.retryOfJobId).toBe("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
    expect(retryJob.rootJobId).toBe("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
    expect(retryJob.retryEligible).toBe(true);
    expect(retryJob.retryCount).toBe(0);
  });

  it("validates a root job that is no longer retry-eligible after spawning a child", () => {
    const exhausted: Job = {
      ...baseJob,
      retryEligible: false,
      retryCount: 1,
    };

    expect(exhausted.retryEligible).toBe(false);
    expect(exhausted.retryCount).toBe(1);
    expect(exhausted.retryOfJobId).toBeNull();
  });

  it("validates retry linkage preserves without leaking into unrelated jobs", () => {
    const unrelated: Job = {
      ...baseJob,
      retryOfJobId: null,
      rootJobId: null,
      retryEligible: true,
      retryCount: 0,
    };

    expect(unrelated.retryOfJobId).toBeNull();
    expect(unrelated.rootJobId).toBeNull();
    expect(unrelated.retryEligible).toBe(true);
    expect(unrelated.retryCount).toBe(0);
  });
});
