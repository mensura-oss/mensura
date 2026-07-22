import type { ContextPackSummary, TaskSummary } from "@mensura/shared-types";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { startRunEligibility } from "./taskBoard";

/**
 * The board's single write affordance: launch a run for an eligible task card.
 *
 * It reuses the existing run flow rather than inventing a parallel one — the
 * same `listContextPacks` query and `createRun` mutation (`POST /tasks/{id}/runs`)
 * that the Tasks panel's `StartRunAction` uses, and the same query cache keys —
 * so a run launched here is an ordinary queued run bound to an immutable context
 * pack. Only the presentation is compact: an eligible card offers "Start run",
 * which lazily opens a context-pack picker; launching invalidates the board so
 * the task's `latestRun` badge appears. Ineligible cards show a disabled button
 * with a bounded reason. Provider execution stays a separate manual action.
 */
export function StartRunControl({ task }: { task: TaskSummary }) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const eligibility = startRunEligibility(task);
  const [open, setOpen] = useState(false);
  const [selectedContextPackId, setSelectedContextPackId] = useState("");

  const contextPacks = useQuery({
    queryKey: queryKeys.contextPacks(task.workspaceId),
    queryFn: () => client.listContextPacks(task.workspaceId),
    enabled: open,
    retry: false,
  });

  const packs = contextPacks.data?.items ?? [];
  const selectedContextPack = packs.find(
    (pack) => pack.id === selectedContextPackId,
  );

  const createRun = useMutation({
    mutationFn: () => {
      if (!selectedContextPack) {
        throw new Error("Select an immutable context pack first.");
      }
      // Reuse the exact existing launch API — an ordinary queued run bound to
      // the immutable pack — not a board-specific execution path.
      return client.createRun(task.id, {
        contextPackId: selectedContextPack.id,
      });
    },
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.run(run.id), run);
      // Collapse the picker now that the run is queued; the confirmation below
      // takes over, and once the run later advances (see the reset effect) the
      // control returns to a clean collapsed "Start run" rather than re-opening.
      setOpen(false);
      setSelectedContextPackId("");
      void Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.workspaceTasks(task.workspaceId),
        }),
        queryClient.invalidateQueries({ queryKey: queryKeys.task(task.id) }),
      ]);
    },
  });

  // Once live board state — the post-launch refetch, or a later SSE
  // `run.status.changed` event surfaced through the board's `workspaceTasks`
  // query — shows our launched run advancing past `queued`, drop the local
  // "Run queued." confirmation so it can never linger stale. After the reset
  // the control is purely eligibility-driven off the live `task` prop: disabled
  // with "A run is already running…" while running, and re-enabled once the run
  // is terminal. In isolation (a fixed `task` prop whose `latestRun` never
  // advances) this never fires, so the confirmation persists as before.
  const launchedRunId = createRun.data?.id;
  const latestRunId = task.latestRun?.id;
  const latestRunStatus = task.latestRun?.status;
  const resetCreateRun = createRun.reset;
  useEffect(() => {
    if (
      launchedRunId &&
      latestRunId === launchedRunId &&
      latestRunStatus !== undefined &&
      latestRunStatus !== "queued"
    ) {
      resetCreateRun();
    }
  }, [launchedRunId, latestRunId, latestRunStatus, resetCreateRun]);

  // A run launched from this card in this session: show a bounded confirmation.
  // The board refetch will also reflect the new `latestRun` badge on its own.
  if (createRun.isSuccess) {
    return (
      <div className="board-run" aria-live="polite">
        <p className="board-run__success" role="status">
          Run queued.
        </p>
      </div>
    );
  }

  if (!eligibility.eligible) {
    return (
      <div className="board-run">
        <button
          type="button"
          className="button button--secondary board-run__button"
          disabled
          title={eligibility.reason ?? undefined}
        >
          Start run
        </button>
        {eligibility.reason ? (
          <span className="board-run__reason">{eligibility.reason}</span>
        ) : null}
      </div>
    );
  }

  if (!open) {
    return (
      <div className="board-run">
        <button
          type="button"
          className="button button--secondary board-run__button"
          onClick={() => setOpen(true)}
        >
          Start run
        </button>
      </div>
    );
  }

  const canLaunch = Boolean(selectedContextPack) && !createRun.isPending;

  return (
    <div className="board-run board-run--open">
      {contextPacks.isPending ? (
        <LoadingState>Loading context packs…</LoadingState>
      ) : null}
      {contextPacks.isError ? (
        <ProblemDetailsView error={contextPacks.error} />
      ) : null}
      {contextPacks.isSuccess && packs.length === 0 ? (
        <p className="board-run__hint">
          No immutable context pack yet. Create and review one in the Context
          packs panel first.
        </p>
      ) : null}
      {contextPacks.isSuccess && packs.length > 0 ? (
        <label className="form-field board-run__field">
          <span>Immutable context pack</span>
          <select
            value={selectedContextPackId}
            onChange={(event) => {
              setSelectedContextPackId(event.target.value);
              createRun.reset();
            }}
            aria-label="Immutable context pack"
          >
            <option value="">Select a reviewed pack</option>
            {packs.map((pack) => (
              <option key={pack.id} value={pack.id}>
                {formatPackOption(pack)}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {createRun.isError ? <ProblemDetailsView error={createRun.error} /> : null}

      <div className="board-run__actions">
        <button
          type="button"
          className="button button--secondary board-run__button"
          onClick={() => createRun.mutate()}
          disabled={!canLaunch}
        >
          {createRun.isPending ? "Starting…" : "Start run"}
        </button>
        <button
          type="button"
          className="button button--quiet board-run__button"
          onClick={() => {
            setOpen(false);
            setSelectedContextPackId("");
            createRun.reset();
          }}
          disabled={createRun.isPending}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function formatPackOption(pack: ContextPackSummary) {
  return `${pack.summary.fileCount} files · …${pack.id.slice(-12)}`;
}
