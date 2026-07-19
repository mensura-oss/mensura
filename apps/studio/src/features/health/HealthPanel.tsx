import { useQuery } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";

export function HealthPanel() {
  const client = useCoreClient();
  const query = useQuery({
    queryKey: queryKeys.health,
    queryFn: () => client.getHealth(),
    refetchInterval: 15_000,
  });

  return (
    <Panel
      eyebrow="Connectivity"
      title="Core status"
      toolbar={
        <button
          className="button button--quiet"
          type="button"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          Refresh
        </button>
      }
    >
      {query.isPending ? <LoadingState>Checking Core…</LoadingState> : null}
      {query.isError ? (
        <div className="status-stack">
          <div className="status-line">
            <span className="status-dot status-dot--error" />
            <strong>Unhealthy</strong>
          </div>
          <ProblemDetailsView error={query.error} />
        </div>
      ) : null}
      {query.isSuccess ? (
        <div className="health-summary">
          <div className="status-line">
            <span className="status-dot status-dot--ok" />
            <strong>Healthy</strong>
          </div>
          <dl className="inline-details">
            <div>
              <dt>Service</dt>
              <dd>{query.data.service}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{query.data.version}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </Panel>
  );
}
