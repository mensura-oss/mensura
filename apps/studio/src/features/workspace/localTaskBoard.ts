import type { TaskStatus } from "@mensura/shared-types";

/**
 * A local-only task shape for the Workspace board. It intentionally mirrors the
 * subset of the Core `Task` model the board renders (id, title, description,
 * status) so this can later be swapped for real Core tasks/runs without
 * reshaping the UI. Nothing here is persisted or sent to Core yet.
 */
export interface WorkspaceTask {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
}

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

export type GroupedTasks = Record<TaskBoardColumnId, WorkspaceTask[]>;

export function groupTasksByColumn(
  tasks: readonly WorkspaceTask[],
): GroupedTasks {
  const groups: GroupedTasks = { backlog: [], "in-progress": [], done: [] };
  for (const task of tasks) {
    groups[columnForStatus(task.status)].push(task);
  }
  return groups;
}

/**
 * Deterministic, illustrative tasks for a workspace. These are placeholders
 * that demonstrate the board shape and the everyday Mensura flow; they are not
 * yet backed by Core. The ids are namespaced by workspace so switching
 * workspaces yields a distinct (but stable) set.
 */
export function seedWorkspaceTasks(workspaceId: string): WorkspaceTask[] {
  const id = (suffix: string) => `${workspaceId}:${suffix}`;
  return [
    {
      id: id("index-vault"),
      title: "Index the repository into Vault",
      description: "Build the semantic index so search and context packs work.",
      status: "ready",
    },
    {
      id: id("triage-search"),
      title: "Find the request boundary with Vault search",
      description: "Locate the API layer and open it in the Workspace editor.",
      status: "draft",
    },
    {
      id: id("review-proposal"),
      title: "Review a change proposal",
      description: "Inspect the diff and verification before applying.",
      status: "review",
    },
    {
      id: id("guard-gate"),
      title: "Pass the Guard lint/test gate",
      status: "running",
    },
    {
      id: id("apply-change"),
      title: "Apply an approved change to the working tree",
      description: "With a backup and one-click undo available.",
      status: "approved",
    },
  ];
}
