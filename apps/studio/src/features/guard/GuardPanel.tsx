import type { GuardCheckResult, GuardRunResponse } from "@mensura/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { CoreApiError } from "../../api/coreClient";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";

const NO_GUARD_RUN_TYPE = "urn:mensura:problem:guard-run-not-found";

export function GuardPanel({
  activeWorkspaceId,
}: {
  activeWorkspaceId: string | null;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const latest = useQuery({
    queryKey: queryKeys.guardLatest(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before loading Guard results.");
      }
      return client.getLatestGuardRun(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });
  const runChecks = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before running Guard checks.");
      }
      return client.createGuardRun(activeWorkspaceId, {});
    },
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.guardLatest(run.workspaceId), run);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.guardLatest(run.workspaceId),
      });
    },
  });
  const noLatestRun = latest.isError && isNoGuardRun(latest.error);

  return (
    <Panel
      eyebrow="Quality gate"
      title="Guard"
      toolbar={
        activeWorkspaceId ? (
          <button
            className="button button--primary"
            type="button"
            onClick={() => runChecks.mutate()}
            disabled={runChecks.isPending}
          >
            {runChecks.isPending ? "Running checks…" : "Run checks"}
          </button>
        ) : undefined
      }
    >
      {!activeWorkspaceId ? (
        <EmptyState>Select an active workspace to run Guard checks.</EmptyState>
      ) : null}
      {activeWorkspaceId && latest.isPending ? (
        <LoadingState>Loading latest Guard result…</LoadingState>
      ) : null}
      {noLatestRun ? (
        <EmptyState>No Guard run yet. Run the configured lint and test checks.</EmptyState>
      ) : null}
      {latest.isError && !noLatestRun ? (
        <ProblemDetailsView error={latest.error} />
      ) : null}
      {runChecks.isPending ? (
        <div className="guard-running" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Core is running configured lint and test commands…</span>
        </div>
      ) : null}
      {runChecks.isError ? <ProblemDetailsView error={runChecks.error} /> : null}
      {latest.isSuccess ? <GuardRunDetails run={latest.data} /> : null}
    </Panel>
  );
}

function isNoGuardRun(error: unknown) {
  return error instanceof CoreApiError && error.problem.type === NO_GUARD_RUN_TYPE;
}

function GuardRunDetails({ run }: { run: GuardRunResponse }) {
  return (
    <div className="guard-result" aria-live="polite">
      <div className="guard-result__heading">
        <div>
          <span>Latest result</span>
          <strong>{run.status === "passed" ? "Passed" : "Failed"}</strong>
        </div>
        <span className={`badge ${run.blocking ? "badge--error" : "badge--clean"}`}>
          {run.blocking ? "Blocking" : "Non-blocking"}
        </span>
      </div>

      <dl className="guard-counts">
        <div>
          <dt>Passed</dt>
          <dd>{run.summary.passedCount}</dd>
        </div>
        <div>
          <dt>Failed</dt>
          <dd>{run.summary.failedCount}</dd>
        </div>
        <div>
          <dt>Errors</dt>
          <dd>{run.summary.errorCount}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{formatDuration(run.durationMs)}</dd>
        </div>
      </dl>

      <div className="guard-checks">
        {run.checks.map((check) => (
          <GuardCheckCard key={check.kind} check={check} />
        ))}
      </div>
    </div>
  );
}

function GuardCheckCard({ check }: { check: GuardCheckResult }) {
  const hasOutput = Boolean(check.stdout || check.stderr);

  return (
    <article className="guard-check">
      <div className="guard-check__heading">
        <strong>{check.kind === "lint" ? "Lint" : "Tests"}</strong>
        <span
          className={`badge ${check.status === "passed" ? "badge--clean" : "badge--error"}`}
        >
          {check.status}
        </span>
      </div>
      <p>{check.summary}</p>
      <div className="guard-check__meta">
        <span>{check.blocking ? "blocking" : "non-blocking"}</span>
        <span>exit {check.exitCode ?? "—"}</span>
        <span>{formatDuration(check.durationMs)}</span>
        {check.outputTruncated ? <span>output truncated</span> : null}
      </div>
      <code className="guard-check__command">{check.command.join(" ")}</code>
      {hasOutput ? (
        <details className="guard-output">
          <summary>Captured output</summary>
          {check.stdout ? (
            <div>
              <span>stdout</span>
              <pre>{check.stdout}</pre>
            </div>
          ) : null}
          {check.stderr ? (
            <div>
              <span>stderr</span>
              <pre>{check.stderr}</pre>
            </div>
          ) : null}
        </details>
      ) : null}
    </article>
  );
}

function formatDuration(durationMs: number) {
  return durationMs < 1000
    ? `${durationMs} ms`
    : `${(durationMs / 1000).toFixed(1)} s`;
}
