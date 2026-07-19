import { useQuery } from "@tanstack/react-query";
import type { RepositorySummary } from "@mensura/shared-types";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";

const MAX_VISIBLE_CHANGES = 8;

export function RepositorySummaryPanel({
  activeWorkspaceId,
}: {
  activeWorkspaceId: string | null;
}) {
  const client = useCoreClient();
  const repository = useQuery({
    queryKey: queryKeys.workspaceRepository(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before inspecting its repository.");
      }
      return client.getWorkspaceRepository(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
  });

  return (
    <Panel
      eyebrow="Read-only Git"
      title="Repository"
      toolbar={
        activeWorkspaceId && !repository.isPending ? (
          <button
            className="button button--quiet"
            type="button"
            onClick={() => void repository.refetch()}
            disabled={repository.isFetching}
          >
            {repository.isFetching
              ? "Refreshing…"
              : repository.isError
                ? "Retry"
                : "Refresh"}
          </button>
        ) : undefined
      }
    >
      {!activeWorkspaceId ? (
        <EmptyState>Select an active workspace to inspect its Git state.</EmptyState>
      ) : null}
      {activeWorkspaceId && repository.isPending ? (
        <LoadingState>Inspecting repository…</LoadingState>
      ) : null}
      {activeWorkspaceId && repository.isError ? (
        <ProblemDetailsView error={repository.error} />
      ) : null}
      {repository.isSuccess ? (
        <RepositorySummaryContent summary={repository.data} />
      ) : null}
    </Panel>
  );
}

function RepositorySummaryContent({
  summary,
}: {
  summary: RepositorySummary;
}) {
  const visibleChanges = summary.diffMetadata.slice(0, MAX_VISIBLE_CHANGES);
  const hiddenCount = summary.diffMetadata.length - visibleChanges.length;

  return (
    <div className="repository-summary">
      <div className="repository-summary__heading">
        <div>
          <span>Branch</span>
          <strong>{summary.branch ?? "Detached HEAD"}</strong>
        </div>
        <span
          className={`badge ${summary.isDirty ? "badge--dirty" : "badge--clean"}`}
        >
          {summary.isDirty ? "Dirty" : "Clean"}
        </span>
      </div>

      <dl className="repository-counts">
        <div>
          <dt>Staged</dt>
          <dd>{summary.stagedCount}</dd>
        </div>
        <div>
          <dt>Unstaged</dt>
          <dd>{summary.unstagedCount}</dd>
        </div>
        <div>
          <dt>Untracked</dt>
          <dd>{summary.untrackedCount}</dd>
        </div>
        <div>
          <dt>Paths</dt>
          <dd>{summary.changedPathsCount}</dd>
        </div>
      </dl>

      {visibleChanges.length === 0 ? (
        <EmptyState>No local repository changes.</EmptyState>
      ) : (
        <div className="repository-changes">
          <span>Changed paths</span>
          <ul>
            {visibleChanges.map((change, index) => (
              <li key={`${change.path}-${change.staged}-${change.changeType}-${index}`}>
                <code>{change.path}</code>
                <span className="repository-change-tags">
                  <span className="badge">{change.changeType}</span>
                  {change.staged ? <span className="badge">staged</span> : null}
                </span>
              </li>
            ))}
          </ul>
          {hiddenCount > 0 ? (
            <p className="repository-changes__more">
              {hiddenCount} more metadata {hiddenCount === 1 ? "entry" : "entries"}
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
