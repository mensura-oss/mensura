import type { TaskStatus } from "@mensura/shared-types";

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
