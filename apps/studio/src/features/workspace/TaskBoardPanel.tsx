import type { RunStatus, TaskStatus } from "@mensura/shared-types";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { StartRunControl } from "./StartRunControl";
import { TASK_BOARD_COLUMNS, groupTasksByColumn } from "./taskBoard";

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

const RUN_STATUS_BADGE_CLASS: Record<RunStatus, string> = {
  queued: "badge",
  running: "badge badge--running",
  succeeded: "badge badge--succeeded",
  failed: "badge badge--failed",
};

/**
 * A minimal, read-only Kanban board for the active workspace, backed by real
 * Core tasks (`GET /workspaces/{id}/tasks`). The eight Core task statuses
 * collapse into three columns (see {@link TASK_BOARD_COLUMNS}); each card keeps
 * its exact status badge and, when present, a compact latest-run badge. Creating
 * and editing tasks stays in the dedicated Tasks panel — this is a read surface.
 */
export function TaskBoardPanel({ workspaceId }: { workspaceId: string }) {
  const client = useCoreClient();

  const tasks = useQuery({
    queryKey: queryKeys.workspaceTasks(workspaceId),
    queryFn: () => client.listWorkspaceTasks(workspaceId),
    retry: false,
  });

  const groups = useMemo(
    () => groupTasksByColumn(tasks.data?.items ?? []),
    [tasks.data],
  );

  return (
    <section className="workspace-board" aria-label="Task board">
      <div className="workspace-board__heading">
        <strong>Task board</strong>
        {tasks.isSuccess ? (
          <span className="badge">
            {tasks.data.total} {tasks.data.total === 1 ? "task" : "tasks"}
          </span>
        ) : null}
      </div>

      {tasks.isPending ? <LoadingState>Loading tasks…</LoadingState> : null}

      {tasks.isError ? <ProblemDetailsView error={tasks.error} /> : null}

      {tasks.isSuccess && tasks.data.items.length === 0 ? (
        <EmptyState>
          No tasks yet for this workspace. Create one from the Tasks panel.
        </EmptyState>
      ) : null}

      {tasks.isSuccess && tasks.data.items.length > 0 ? (
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
                    <span className="workspace-board__card-badges">
                      <span className={STATUS_BADGE_CLASS[task.status]}>
                        {task.status}
                      </span>
                      {task.latestRun ? (
                        <span
                          className={RUN_STATUS_BADGE_CLASS[task.latestRun.status]}
                          title="Latest run status"
                        >
                          run: {task.latestRun.status}
                        </span>
                      ) : null}
                    </span>
                    <StartRunControl key={task.id} task={task} />
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
      ) : null}

      <p className="workspace-hint">
        Real Core tasks and their latest run status for this workspace. Launch a
        run on an eligible task with <strong>Start run</strong>; task creation,
        editing, status changes, and drag-and-drop stay in the dedicated panels.
      </p>
    </section>
  );
}
