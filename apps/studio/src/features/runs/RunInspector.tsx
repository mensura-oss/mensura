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

export function RunInspector() {
  const client = useCoreClient();
  const [input, setInput] = useState("");
  const [runId, setRunId] = useState("");
  const run = useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => client.getRun(runId),
    enabled: runId.length > 0,
    retry: false,
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextRunId = input.trim();
    if (nextRunId === runId && nextRunId) {
      void run.refetch();
      return;
    }
    setRunId(nextRunId);
  }

  return (
    <Panel eyebrow="Resource lookup" title="Run inspector">
      <form className="inspector-form" onSubmit={handleSubmit}>
        <label>
          <span>Run ID</span>
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

      {!runId ? <EmptyState>Enter a run ID to inspect Core state.</EmptyState> : null}
      {run.isPending && runId ? <LoadingState>Loading run…</LoadingState> : null}
      {run.isError ? <ProblemDetailsView error={run.error} /> : null}
      {run.isSuccess ? (
        <ResourceDetails
          items={[
            { label: "ID", value: <code>{run.data.id}</code> },
            { label: "Task", value: <code>{run.data.taskId}</code> },
            { label: "Status", value: <span className="badge">{run.data.status}</span> },
            { label: "Started", value: formatTimestamp(run.data.startedAt) },
            { label: "Finished", value: formatTimestamp(run.data.finishedAt) },
            { label: "Created", value: formatTimestamp(run.data.createdAt) },
            { label: "Updated", value: formatTimestamp(run.data.updatedAt) },
          ]}
        />
      ) : null}
    </Panel>
  );
}
