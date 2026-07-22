import type { RunStatus, TaskStatus } from "@mensura/shared-types";

export type TaskBoardColumnId = "backlog" | "in-progress" | "done";

export interface TaskBoardColumn {
  id: TaskBoardColumnId;
  title: string;
  /** Core task statuses that land in this column. */
  statuses: readonly TaskStatus[];
}

/**
 * A three-column Kanban shape. The eight Core task statuses collapse into these
 * columns; each card still shows its exact status as a badge so the collapse is
 * never lossy to the reader.
 */
export const TASK_BOARD_COLUMNS: readonly TaskBoardColumn[] = [
  { id: "backlog", title: "Backlog", statuses: ["draft", "ready"] },
  { id: "in-progress", title: "In progress", statuses: ["running", "review"] },
  {
    id: "done",
    title: "Done",
    statuses: ["approved", "rejected", "failed", "cancelled"],
  },
];

export function columnForStatus(status: TaskStatus): TaskBoardColumnId {
  const column = TASK_BOARD_COLUMNS.find((candidate) =>
    candidate.statuses.includes(status),
  );
  return column ? column.id : "backlog";
}

/**
 * Task statuses from which a run may be launched off the board. Launching a run
 * is the board's one write action; every other status is read-only here. A task
 * in `draft`/`ready` has not yet progressed into an active/terminal lifecycle, so
 * it is the honest point to dispatch work into the existing run flow.
 */
export const START_RUN_ELIGIBLE_STATUSES: readonly TaskStatus[] = [
  "draft",
  "ready",
];

/** Run statuses that mean a run is still in flight for a task. */
const ACTIVE_RUN_STATUSES: readonly RunStatus[] = ["queued", "running"];

export interface StartRunEligibility {
  eligible: boolean;
  /** A short, bounded reason shown when the action is disabled; `null` when eligible. */
  reason: string | null;
}

/**
 * Decide whether the board may launch a run for a task, and why not when it may
 * not. Eligibility is a client-side affordance layered on the existing run flow:
 * Core does not gate `createRun` on task status, it only rejects a missing or
 * mismatched context pack. A task is launchable only from an eligible status
 * (see {@link START_RUN_ELIGIBLE_STATUSES}) that does not already have a run in
 * flight — the latter is the honest in-flight guard, since creating a run leaves
 * `task.status` unchanged and only attaches a `latestRun`.
 */
export function startRunEligibility(task: {
  status: TaskStatus;
  latestRun?: { status: RunStatus } | null;
}): StartRunEligibility {
  if (!START_RUN_ELIGIBLE_STATUSES.includes(task.status)) {
    return {
      eligible: false,
      reason: `This task is ${task.status} and cannot start a new run.`,
    };
  }
  const latestRun = task.latestRun;
  if (latestRun && ACTIVE_RUN_STATUSES.includes(latestRun.status)) {
    return {
      eligible: false,
      reason: `A run is already ${latestRun.status} for this task.`,
    };
  }
  return { eligible: true, reason: null };
}

export type GroupedTasks<T> = Record<TaskBoardColumnId, T[]>;

/**
 * Group any status-bearing tasks (Core `TaskSummary` in production) into the
 * three board columns, preserving input order within each column.
 */
export function groupTasksByColumn<T extends { status: TaskStatus }>(
  tasks: readonly T[],
): GroupedTasks<T> {
  const groups: GroupedTasks<T> = { backlog: [], "in-progress": [], done: [] };
  for (const task of tasks) {
    groups[columnForStatus(task.status)].push(task);
  }
  return groups;
}
