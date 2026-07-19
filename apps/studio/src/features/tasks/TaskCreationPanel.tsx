import type { AgentRole, CreateTaskRequest } from "@mensura/shared-types";
import { AGENT_ROLES } from "@mensura/shared-types";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { TaskDetails } from "./TaskDetails";

export function TaskCreationPanel({
  activeWorkspaceId,
}: {
  activeWorkspaceId: string | null;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignedRole, setAssignedRole] = useState<AgentRole | "">("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [createdTaskId, setCreatedTaskId] = useState("");
  const workspaces = useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: () => client.listWorkspaces(),
  });
  const activeWorkspace = workspaces.data?.items.find(
    (workspace) => workspace.id === activeWorkspaceId,
  );
  const createdTask = useQuery({
    queryKey: queryKeys.task(createdTaskId),
    queryFn: () => client.getTask(createdTaskId),
    enabled: createdTaskId.length > 0,
    retry: false,
  });
  const createTask = useMutation({
    mutationFn: (input: CreateTaskRequest) => client.createTask(input),
    onSuccess: (task) => {
      queryClient.setQueryData(queryKeys.task(task.id), task);
      setCreatedTaskId(task.id);
      setTitle("");
      setDescription("");
      setAssignedRole("");
      void queryClient.invalidateQueries({ queryKey: queryKeys.task(task.id) });
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTitle = title.trim();

    if (!normalizedTitle) {
      setTitleError("Enter a task title.");
      return;
    }
    if (!activeWorkspaceId) {
      return;
    }

    setTitleError(null);
    const request: CreateTaskRequest = assignedRole
      ? {
          workspaceId: activeWorkspaceId,
          title: normalizedTitle,
          description,
          assignedRole,
        }
      : { workspaceId: activeWorkspaceId, title: normalizedTitle, description };
    createTask.mutate(request);
  }

  return (
    <Panel eyebrow="First task flow" title="Create task">
      {!activeWorkspaceId ? (
        <EmptyState>
          Select or create a workspace before creating a task.
        </EmptyState>
      ) : null}

      {activeWorkspaceId && workspaces.isPending ? (
        <LoadingState>Restoring active workspace…</LoadingState>
      ) : null}

      {activeWorkspaceId && workspaces.isError ? (
        <ProblemDetailsView error={workspaces.error} />
      ) : null}

      {activeWorkspaceId && workspaces.isSuccess && !activeWorkspace ? (
        <EmptyState>
          The selected workspace is no longer available. Choose another workspace.
        </EmptyState>
      ) : null}

      {activeWorkspace ? (
        <>
          <div className="active-workspace" role="status">
            <span>Active workspace</span>
            <strong>{activeWorkspace.name}</strong>
            <code>{activeWorkspace.rootPath}</code>
          </div>

          <form className="task-form" onSubmit={handleSubmit} noValidate>
            <label className="form-field">
              <span>Title</span>
              <input
                value={title}
                onChange={(event) => {
                  setTitle(event.target.value);
                  if (titleError) {
                    setTitleError(null);
                  }
                }}
                aria-invalid={titleError ? "true" : undefined}
                aria-describedby={titleError ? "task-title-error" : undefined}
                maxLength={240}
                required
              />
              {titleError ? (
                <span className="field-error" id="task-title-error" role="alert">
                  {titleError}
                </span>
              ) : null}
            </label>

            <label className="form-field">
              <span>Description</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={3}
                maxLength={10_000}
              />
            </label>

            <label className="form-field">
              <span>Assigned role</span>
              <select
                value={assignedRole}
                onChange={(event) =>
                  setAssignedRole(event.target.value as AgentRole | "")
                }
              >
                <option value="">Unassigned</option>
                {AGENT_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </label>

            <button
              className="button button--primary"
              type="submit"
              disabled={createTask.isPending}
            >
              {createTask.isPending ? "Creating task…" : "Create task"}
            </button>
          </form>
        </>
      ) : null}

      {createTask.isError ? <ProblemDetailsView error={createTask.error} /> : null}

      {createdTask.isPending && createdTaskId ? (
        <LoadingState>Refreshing created task…</LoadingState>
      ) : null}
      {createdTask.isError ? (
        <ProblemDetailsView error={createdTask.error} />
      ) : null}
      {createdTask.isSuccess ? (
        <div className="result-stack" aria-live="polite">
          <p className="success-message" role="status">
            Task created and ready.
          </p>
          <TaskDetails task={createdTask.data} />
        </div>
      ) : null}
    </Panel>
  );
}
