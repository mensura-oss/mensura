import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { RunDetails } from "./RunDetails";

export function StartRunAction({ taskId }: { taskId: string }) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [createdRunId, setCreatedRunId] = useState("");
  const createdRun = useQuery({
    queryKey: queryKeys.run(createdRunId),
    queryFn: () => client.getRun(createdRunId),
    enabled: createdRunId.length > 0,
    retry: false,
  });
  const createRun = useMutation({
    mutationFn: () => client.createRun(taskId),
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.run(run.id), run);
      setCreatedRunId(run.id);
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.task(taskId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.run(run.id) }),
      ]);
    },
  });

  return (
    <div className="run-action">
      <div className="run-action__controls">
        <div>
          <strong>Queued execution</strong>
          <span>Creates a run record only; no worker executes it yet.</span>
        </div>
        <button
          className="button button--secondary"
          type="button"
          onClick={() => createRun.mutate()}
          disabled={createRun.isPending}
        >
          {createRun.isPending ? "Starting run…" : "Start run"}
        </button>
      </div>

      {createRun.isError ? <ProblemDetailsView error={createRun.error} /> : null}
      {createdRun.isPending && createdRunId ? (
        <LoadingState>Refreshing queued run…</LoadingState>
      ) : null}
      {createdRun.isError ? (
        <ProblemDetailsView error={createdRun.error} />
      ) : null}
      {createdRun.isSuccess ? (
        <div className="result-stack" aria-live="polite">
          <p className="success-message" role="status">
            Run created and queued.
          </p>
          <RunDetails run={createdRun.data} />
        </div>
      ) : null}
    </div>
  );
}
