import { TASK_STATUSES, type TaskStatus } from "@mensura/shared-types";
import { describe, expect, it } from "vitest";

import { columnForStatus, groupTasksByColumn } from "./taskBoard";

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
