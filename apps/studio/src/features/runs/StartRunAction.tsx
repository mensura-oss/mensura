import type { ContextPackSummary } from "@mensura/shared-types";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { RunDetails } from "./RunDetails";

export function StartRunAction({
  taskId,
  workspaceId,
}: {
  taskId: string;
  workspaceId: string;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [createdRunId, setCreatedRunId] = useState("");
  const [selectedContextPackId, setSelectedContextPackId] = useState("");
  const contextPacks = useQuery({
    queryKey: queryKeys.contextPacks(workspaceId),
    queryFn: () => client.listContextPacks(workspaceId),
    retry: false,
  });
  const selectedContextPack = contextPacks.data?.items.find(
    (pack) => pack.id === selectedContextPackId,
  );
  const createdRun = useQuery({
    queryKey: queryKeys.run(createdRunId),
    queryFn: () => client.getRun(createdRunId),
    enabled: createdRunId.length > 0,
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 1_000 : false,
  });
  const createRun = useMutation({
    mutationFn: () => {
      if (!selectedContextPack) {
        throw new Error("Select an immutable context pack first.");
      }
      return client.createRun(taskId, { contextPackId: selectedContextPack.id });
    },
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
          <span>Creates a run first; provider execution is a separate manual action.</span>
        </div>
      </div>

      {contextPacks.isPending ? (
        <LoadingState>Loading immutable context packs…</LoadingState>
      ) : null}
      {contextPacks.isError ? (
        <ProblemDetailsView error={contextPacks.error} />
      ) : null}
      {contextPacks.isSuccess && contextPacks.data.items.length === 0 ? (
        <div className="run-context-empty">
          Create and review an immutable context pack for this task workspace before
          starting a run.
        </div>
      ) : null}
      {contextPacks.isSuccess && contextPacks.data.items.length > 0 ? (
        <div className="run-context-picker">
          <label className="form-field">
            <span>Immutable context pack</span>
            <select
              value={selectedContextPackId}
              onChange={(event) => {
                setSelectedContextPackId(event.target.value);
                createRun.reset();
              }}
              aria-describedby="run-context-help"
              required
            >
              <option value="">Select a reviewed pack</option>
              {contextPacks.data.items.map((pack) => (
                <option key={pack.id} value={pack.id}>
                  {formatPackOption(pack)}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => createRun.mutate()}
            disabled={!selectedContextPack || createRun.isPending}
          >
            {createRun.isPending ? "Starting run…" : "Start run"}
          </button>
        </div>
      ) : null}

      <p className="run-context-help" id="run-context-help">
        Core will queue only the exact immutable evidence selected here.
      </p>
      {selectedContextPack ? (
        <div className="run-context-selection" aria-live="polite">
          <span>Selected execution context</span>
          <code>{selectedContextPack.id}</code>
          <small>
            {selectedContextPack.summary.fileCount} files ·{" "}
            {formatBytes(selectedContextPack.summary.totalFileBytes)} file data ·{" "}
            {formatBytes(selectedContextPack.summary.totalPreviewBytes)} captured preview
          </small>
        </div>
      ) : null}

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
            Run created and queued with immutable context.
          </p>
          <RunDetails run={createdRun.data} />
        </div>
      ) : null}
    </div>
  );
}

function formatPackOption(pack: ContextPackSummary) {
  return `${pack.id} · ${pack.summary.fileCount} files`;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
