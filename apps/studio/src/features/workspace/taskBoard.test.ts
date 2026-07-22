import {
  TASK_STATUSES,
  type RunStatus,
  type TaskStatus,
} from "@mensura/shared-types";
import { describe, expect, it } from "vitest";

import {
  columnForStatus,
  groupTasksByColumn,
  startRunEligibility,
} from "./taskBoard";

describe("task board status mapping", () => {
  it("maps each Core task status to its documented column", () => {
    const expected: Record<TaskStatus, string> = {
      draft: "backlog",
      ready: "backlog",
      running: "in-progress",
      review: "in-progress",
      approved: "done",
      rejected: "done",
      failed: "done",
      cancelled: "done",
    };
    for (const status of TASK_STATUSES) {
      expect(columnForStatus(status)).toBe(expected[status]);
    }
  });

  it("assigns every Core status to exactly one of the three columns", () => {
    for (const status of TASK_STATUSES) {
      expect(["backlog", "in-progress", "done"]).toContain(
        columnForStatus(status),
      );
    }
  });

  it("groups tasks into their mapped columns, preserving order", () => {
    const grouped = groupTasksByColumn([
      { id: "a", status: "ready" },
      { id: "b", status: "running" },
      { id: "c", status: "approved" },
      { id: "d", status: "draft" },
      { id: "e", status: "failed" },
    ]);

    expect(grouped.backlog.map((task) => task.id)).toEqual(["a", "d"]);
    expect(grouped["in-progress"].map((task) => task.id)).toEqual(["b"]);
    expect(grouped.done.map((task) => task.id)).toEqual(["c", "e"]);
  });

  it("returns empty columns for no tasks", () => {
    const grouped = groupTasksByColumn([]);
    expect(grouped).toEqual({ backlog: [], "in-progress": [], done: [] });
  });
});

describe("startRunEligibility", () => {
  it("allows launching a run from draft or ready with no active run", () => {
    expect(startRunEligibility({ status: "draft", latestRun: null })).toEqual({
      eligible: true,
      reason: null,
    });
    expect(startRunEligibility({ status: "ready", latestRun: null })).toEqual({
      eligible: true,
      reason: null,
    });
  });

  it("still allows launching when the latest run is already terminal", () => {
    for (const status of ["succeeded", "failed"] satisfies RunStatus[]) {
      expect(
        startRunEligibility({ status: "ready", latestRun: { status } }).eligible,
      ).toBe(true);
    }
  });

  it("disallows launching from every non-backlog status with a bounded reason", () => {
    const ineligible: TaskStatus[] = [
      "running",
      "review",
      "approved",
      "rejected",
      "failed",
      "cancelled",
    ];
    for (const status of ineligible) {
      const result = startRunEligibility({ status, latestRun: null });
      expect(result.eligible).toBe(false);
      expect(result.reason).toContain(status);
    }
  });

  it("disallows launching while a run is already queued or running (in-flight guard)", () => {
    for (const status of ["queued", "running"] satisfies RunStatus[]) {
      const result = startRunEligibility({
        status: "ready",
        latestRun: { status },
      });
      expect(result.eligible).toBe(false);
      expect(result.reason).toContain(status);
    }
  });

  it("covers every Core task status with a defined decision", () => {
    for (const status of TASK_STATUSES) {
      expect(typeof startRunEligibility({ status, latestRun: null }).eligible).toBe(
        "boolean",
      );
    }
  });
});
