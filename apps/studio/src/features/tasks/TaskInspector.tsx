import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import {
  formatTimestamp,
  ResourceDetails,
} from "../../components/ResourceDetails";

export function TaskInspector() {
  const client = useCoreClient();
  const [input, setInput] = useState("");
  const [taskId, setTaskId] = useState("");
  const task = useQuery({
    queryKey: queryKeys.task(taskId),
    queryFn: () => client.getTask(taskId),
    enabled: taskId.length > 0,
    retry: false,
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextTaskId = input.trim();
    if (nextTaskId === taskId && nextTaskId) {
      void task.refetch();
      return;
    }
    setTaskId(nextTaskId);
  }

  return (
    <Panel eyebrow="Resource lookup" title="Task inspector">
      <form className="inspector-form" onSubmit={handleSubmit}>
        <label>
          <span>Task ID</span>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="UUID"
            required
          />
        </label>
        <button className="button button--secondary" type="submit">
          Inspect
        </button>
      </form>

      {!taskId ? <EmptyState>Enter a task ID to inspect Core state.</EmptyState> : null}
      {task.isPending && taskId ? <LoadingState>Loading task…</LoadingState> : null}
      {task.isError ? <ProblemDetailsView error={task.error} /> : null}
      {task.isSuccess ? (
        <ResourceDetails
          items={[
            { label: "ID", value: <code>{task.data.id}</code> },
            { label: "Workspace", value: <code>{task.data.workspaceId}</code> },
            { label: "Title", value: task.data.title },
            { label: "Description", value: task.data.description || "—" },
            { label: "Status", value: <span className="badge">{task.data.status}</span> },
            { label: "Assigned role", value: task.data.assignedRole ?? "—" },
            { label: "Created", value: formatTimestamp(task.data.createdAt) },
            { label: "Updated", value: formatTimestamp(task.data.updatedAt) },
          ]}
        />
      ) : null}
    </Panel>
  );
}
