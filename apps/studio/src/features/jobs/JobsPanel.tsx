import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Job, JobStatus } from "@mensura/shared-types";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";

const STATUS_BADGE: Record<JobStatus, string> = {
  queued: "badge",
  running: "badge--running",
  succeeded: "badge--succeeded",
  failed: "badge--failed",
};

const JOB_TYPE_LABEL: Record<string, string> = {
  proposal_verification: "Verify proposal",
  application_apply: "Apply proposal",
  application_undo: "Undo application",
  backup_create: "Create backup",
};

function shortId(id: string): string {
  return id.slice(0, 8);
}

export function JobsPanel() {
  const client = useCoreClient();
  const queryClient = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: queryKeys.jobs,
    queryFn: () => client.listJobs(),
    // SSE keeps this fresh; poll as a fallback in case the stream drops.
    refetchInterval: 10_000,
  });

  const queueBackup = useMutation({
    mutationFn: () => client.enqueueJob({ jobType: "backup_create" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs });
    },
  });

  const retryJob = useMutation({
    mutationFn: (jobId: string) => client.retryJob(jobId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs });
    },
  });

  return (
    <Panel
      eyebrow="System"
      title="Background jobs"
      toolbar={
        <button
          className="button button--primary"
          type="button"
          onClick={() => queueBackup.mutate()}
          disabled={queueBackup.isPending}
        >
          {queueBackup.isPending ? "Queuing…" : "Queue backup job"}
        </button>
      }
    >
      <p className="panel-note">
        Durable queued operations run in a background worker inside Core and survive
        process restarts. The database remains the source of truth; this view refreshes
        live over SSE.
      </p>

      {queueBackup.isError ? <ProblemDetailsView error={queueBackup.error} /> : null}

      {jobsQuery.isPending ? <LoadingState>Loading jobs…</LoadingState> : null}
      {jobsQuery.isError ? <ProblemDetailsView error={jobsQuery.error} /> : null}
      {jobsQuery.isSuccess && jobsQuery.data.items.length === 0 ? (
        <EmptyState>No background jobs yet.</EmptyState>
      ) : null}
      {jobsQuery.isSuccess && jobsQuery.data.items.length > 0 ? (
        <div className="job-list">
          {jobsQuery.data.items.map((job) => (
            <div key={job.id} className="job-item">
              <div className="job-item__header">
                <span className={`badge ${STATUS_BADGE[job.status]}`}>
                  {job.status}
                </span>
                <strong>{JOB_TYPE_LABEL[job.jobType] ?? job.jobType}</strong>
                <span className="job-item__target">
                  {job.targetEntityType}
                  {job.targetEntityId ? ` ${shortId(job.targetEntityId)}` : ""}
                </span>
              </div>
              <div className="job-item__meta">
                <span>Queued {formatTimestamp(job.createdAt)}</span>
                {job.startedAt ? (
                  <span>Started {formatTimestamp(job.startedAt)}</span>
                ) : null}
                {job.finishedAt ? (
                  <span>Finished {formatTimestamp(job.finishedAt)}</span>
                ) : null}
              </div>
              {job.retryOfJobId ? (
                <div className="job-item__retry-lineage">
                  Retry of <code>{shortId(job.retryOfJobId)}</code>
                  {job.rootJobId ? <> — root: <code>{shortId(job.rootJobId)}</code></> : null}
                </div>
              ) : null}
              {job.resultEntityId ? (
                <div className="job-item__result">
                  Produced {job.resultEntityType} {shortId(job.resultEntityId)}
                </div>
              ) : null}
              {job.lastError ? (
                <div className="job-item__error">{job.lastError}</div>
              ) : null}
              {job.status === "failed" && job.retryEligible ? (
                <div className="job-item__actions">
                  <button
                    className="button button--secondary"
                    type="button"
                    onClick={() => retryJob.mutate(job.id)}
                    disabled={retryJob.isPending}
                  >
                    {retryJob.isPending ? "Retrying…" : "Retry (single attempt remaining)"}
                  </button>
                </div>
              ) : null}
              {job.status === "failed" && !job.retryEligible && job.retryCount > 0 ? (
                <div className="job-item__retry-exhausted">
                  ℹ No retries remaining
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </Panel>
  );
}
