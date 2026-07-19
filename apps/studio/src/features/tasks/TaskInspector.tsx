import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { TaskDetails } from "./TaskDetails";

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
        <TaskDetails task={task.data} />
      ) : null}
    </Panel>
  );
}
