import type { TaskStatus } from "@mensura/shared-types";
import { useMemo } from "react";

import { EmptyState } from "../../components/AsyncState";
import {
  TASK_BOARD_COLUMNS,
  groupTasksByColumn,
  seedWorkspaceTasks,
  type WorkspaceTask,
} from "./localTaskBoard";

const STATUS_BADGE_CLASS: Record<TaskStatus, string> = {
  draft: "badge",
  ready: "badge",
  running: "badge badge--running",
  review: "badge badge--dirty",
  approved: "badge badge--clean",
  rejected: "badge badge--error",
  failed: "badge badge--error",
  cancelled: "badge badge--error",
};

/**
 * A minimal, read-only Kanban board for the active workspace. Tasks default to
 * a deterministic local placeholder set (see {@link seedWorkspaceTasks}); an
 * explicit `tasks` prop overrides them, which is how tests and — eventually —
 * real Core tasks feed the board.
 */
export function TaskBoardPanel({
  workspaceId,
  tasks,
}: {
  workspaceId: string;
  tasks?: readonly WorkspaceTask[];
}) {
  const board = useMemo(
    () => tasks ?? seedWorkspaceTasks(workspaceId),
    [tasks, workspaceId],
  );
  const groups = useMemo(() => groupTasksByColumn(board), [board]);

  return (
    <section className="workspace-board" aria-label="Task board">
      <div className="workspace-board__heading">
        <strong>Task board</strong>
        <span className="badge">Local preview</span>
      </div>
      {board.length === 0 ? (
        <EmptyState>No tasks yet for this workspace.</EmptyState>
      ) : (
        <div className="workspace-board__columns">
          {TASK_BOARD_COLUMNS.map((column) => (
            <div
              key={column.id}
              className="workspace-board__column"
              aria-label={column.title}
            >
              <div className="workspace-board__column-head">
                <span>{column.title}</span>
                <span>{groups[column.id].length}</span>
              </div>
              <ul>
                {groups[column.id].map((task) => (
                  <li key={task.id} className="workspace-board__card">
                    <span className="workspace-board__card-title">
                      {task.title}
                    </span>
                    {task.description ? <p>{task.description}</p> : null}
                    <span className={STATUS_BADGE_CLASS[task.status]}>
                      {task.status}
                    </span>
                  </li>
                ))}
                {groups[column.id].length === 0 ? (
                  <li className="workspace-board__placeholder" aria-hidden="true">
                    —
                  </li>
                ) : null}
              </ul>
            </div>
          ))}
        </div>
      )}
      <p className="workspace-hint">
        Illustrative local tasks — not yet connected to Core tasks or runs.
      </p>
    </section>
  );
}
