import type {
  ChangeProposal,
  FileVerificationResult,
  ProposalVerification,
  ProposalVerificationCollection,
  ProposalVerificationOutcome,
  VerificationGuardResult,
} from "@mensura/shared-types";
import type { Job } from "@mensura/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";

const OUTCOME_COPY: Record<ProposalVerificationOutcome, string> = {
  sandbox_verified:
    "The proposal materialized cleanly in the temporary sandbox and Guard passed there.",
  guard_failed:
    "The proposal materialized in the temporary sandbox, but Guard failed against it.",
  materialization_failed:
    "The proposal could not be materialized against the sandbox HEAD, so Guard did not run.",
};

const FILE_REASON_COPY: Record<FileVerificationResult["reason"], string> = {
  applied: "Applied in sandbox",
  create_target_exists: "Create target already exists",
  target_missing: "Target file is missing",
  target_not_a_file: "Target is not a regular file",
  before_content_mismatch: "Content drifted from the captured evidence",
  unsafe_path: "Unsafe path refused",
};

export function ProposalVerificationSection({
  proposal,
}: {
  proposal: ChangeProposal;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [verifyJobId, setVerifyJobId] = useState<string | null>(null);
  const verifications = useQuery({
    queryKey: queryKeys.changeProposalVerifications(proposal.id),
    queryFn: () => client.listChangeProposalVerifications(proposal.id),
    retry: false,
  });
  const verify = useMutation({
    mutationFn: () => client.verifyChangeProposal(proposal.id),
    onSuccess: (verification) => {
      queryClient.setQueryData(
        queryKeys.verification(verification.id),
        verification,
      );
      queryClient.setQueryData<ProposalVerificationCollection>(
        queryKeys.changeProposalVerifications(proposal.id),
        (current) => {
          const items = [
            ...(current?.items ?? []).filter(
              (item) => item.id !== verification.id,
            ),
            verification,
          ];
          return { items, total: items.length };
        },
      );
    },
  });

  const verifyJob = useMutation({
    mutationFn: () =>
      client.enqueueJob({
        jobType: "proposal_verification",
        proposalId: proposal.id,
      }),
    onSuccess: (job) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs });
      setVerifyJobId(job.id);
    },
  });

  const jobStatus = useQuery<Job | null>({
    queryKey: verifyJobId ? queryKeys.job(verifyJobId) : ["core", "jobs", "noop"],
    queryFn: () => (verifyJobId ? client.getJob(verifyJobId) : Promise.resolve(null)),
    enabled: Boolean(verifyJobId),
    refetchInterval: (query) =>
      query.state.data?.status === "queued" || query.state.data?.status === "running"
        ? 1_000
        : false,
    retry: false,
  });

  if (proposal.status !== "approved") return null;

  const items = verifications.data?.items ?? [];
  const verifyLatest = verify.data ?? items[items.length - 1];

  const jobSucceeded = jobStatus.data?.status === "succeeded" && jobStatus.data?.resultEntityId;
  const previousCount = Math.max(0, items.length - (verifyLatest ? 1 : 0));

  return (
    <section
      className="proposal-verification"
      aria-labelledby={`verification-${proposal.id}`}
    >
      <div className="change-proposal__heading">
        <div>
          <span className="section-label">Temporary isolated sandbox</span>
          <h4 id={`verification-${proposal.id}`}>Proposal verification</h4>
        </div>
        {verifyLatest ? (
          <span className={`badge badge--${verifyLatest.status}`}>{verifyLatest.status}</span>
        ) : null}
      </div>

      <p className="change-proposal__boundary">
        Verification materializes this approved proposal only inside a temporary
        detached Git worktree and runs Guard there. Your live branch, working
        tree, and repository files are never written.
      </p>

      {verifications.isPending ? (
        <LoadingState>Checking for existing verifications…</LoadingState>
      ) : null}
      {verifications.isError ? (
        <ProblemDetailsView error={verifications.error} />
      ) : null}

      <div className="proposal-verification__actions">
        <button
          className="button button--secondary"
          type="button"
          onClick={() => verify.mutate()}
          disabled={verify.isPending}
        >
          {verify.isPending
            ? "Verifying in isolated sandbox…"
            : verifyLatest
              ? "Verify again (direct)"
              : "Verify (direct)"}
        </button>
        <button
          className="button button--primary"
          type="button"
          onClick={() => verifyJob.mutate()}
          disabled={verifyJob.isPending || verify.isPending}
        >
          {verifyJob.isPending
            ? "Enqueuing verification job…"
            : "Verify as background job"}
        </button>
        {verify.isPending ? (
          <span role="status" className="proposal-verification__pending">
            Running Guard inside a temporary worktree…
          </span>
        ) : null}
        {verifyJob.isError ? <ProblemDetailsView error={verifyJob.error} /> : null}
      </div>

      {jobStatus.data ? (
        <div className="proposal-verification__job-status" role="status">
          <span className={`badge badge--${jobStatus.data.status}`}>
            Job: {jobStatus.data.status}
          </span>
          {jobStatus.data.status === "running" ? (
            <span>Verification is running in a background worker…</span>
          ) : null}
          {jobStatus.data.status === "succeeded" && jobStatus.data.resultEntityId ? (
            <span>
              Completed —{" "}
              <code>{jobStatus.data.resultEntityId.slice(0, 8)}</code>
            </span>
          ) : null}
          {jobStatus.data.status === "failed" ? (
            <span className="job-item__error">
              Failed: {jobStatus.data.lastError ?? "Unknown error"}
            </span>
          ) : null}
        </div>
      ) : null}
      {verify.isError ? <ProblemDetailsView error={verify.error} /> : null}

      {verifyLatest ? (
        <VerificationResult verification={verifyLatest} previousCount={previousCount} />
      ) : null}
    </section>
  );
}

function VerificationResult({
  verification,
  previousCount,
}: {
  verification: ProposalVerification;
  previousCount: number;
}) {
  return (
    <div className="proposal-verification__result" aria-live="polite">
      <p className="proposal-verification__outcome">
        {OUTCOME_COPY[verification.outcome]}
      </p>

      <dl className="proposal-review__lineage">
        <div>
          <dt>Verification</dt>
          <dd>
            <code>{verification.id}</code>
          </dd>
        </div>
        <div>
          <dt>Sandbox</dt>
          <dd>
            Temporary Git worktree of commit{" "}
            <code>{verification.sandbox.commitId.slice(0, 12)}</code>
            {verification.sandbox.cleanupCompleted ? (
              " · removed after verification"
            ) : (
              <span className="badge badge--warning">cleanup incomplete</span>
            )}
          </dd>
        </div>
        <div>
          <dt>Finished</dt>
          <dd>
            {formatTimestamp(verification.finishedAt)} ·{" "}
            {verification.durationMs} ms
          </dd>
        </div>
        <div>
          <dt>Safe diff</dt>
          <dd>
            {verification.safeDiff.appliedCount}/{verification.safeDiff.filesTotal}{" "}
            applied · {verification.safeDiff.createdCount} create ·{" "}
            {verification.safeDiff.modifiedCount} modify ·{" "}
            {verification.safeDiff.deletedCount} delete
          </dd>
        </div>
      </dl>

      <div className="proposal-review__files">
        <div className="proposal-review__files-heading">
          <strong>File checks in sandbox</strong>
          <span>{verification.fileResults.length}</span>
        </div>
        {verification.fileResults.map((result) => (
          <div
            key={`${result.changeType}:${result.path}`}
            className="proposal-verification__file"
          >
            <code>{result.path}</code>
            <span className={`badge badge--${result.changeType}`}>
              {result.changeType}
            </span>
            <span
              className={`badge badge--${result.appliedInSandbox ? "passed" : "failed"}`}
            >
              {FILE_REASON_COPY[result.reason]}
            </span>
          </div>
        ))}
      </div>

      {verification.guard ? (
        <GuardOutcome guard={verification.guard} />
      ) : (
        <p className="proposal-verification__no-guard">
          Guard was not executed because the proposal did not materialize
          completely in the sandbox.
        </p>
      )}

      <p className="proposal-review__decision" role="status">
        This result was produced in a temporary isolated sandbox
        {previousCount > 0
          ? ` (${previousCount} earlier ${previousCount === 1 ? "attempt" : "attempts"} recorded)`
          : ""}
        . The live repository remains untouched.
      </p>
    </div>
  );
}

function GuardOutcome({ guard }: { guard: VerificationGuardResult }) {
  return (
    <div className="proposal-verification__guard">
      <div className="proposal-review__files-heading">
        <strong>Guard in sandbox</strong>
        <span className={`badge badge--${guard.status}`}>
          {guard.status}
          {guard.blocking ? " · blocking" : ""}
        </span>
      </div>
      <p className="proposal-verification__guard-summary">
        {guard.summary.passedCount} passed · {guard.summary.failedCount} failed ·{" "}
        {guard.summary.errorCount} errored
      </p>
      {guard.checks.map((check) => (
        <details key={check.kind} className="proposal-file-change">
          <summary>
            <code>{check.kind}</code>
            <span className={`badge badge--${check.status}`}>{check.status}</span>
            {check.outputTruncated ? (
              <span className="badge badge--warning">truncated</span>
            ) : null}
          </summary>
          <dl>
            <div>
              <dt>Summary</dt>
              <dd>{check.summary}</dd>
            </div>
            <div>
              <dt>Exit code / duration</dt>
              <dd>
                {check.exitCode ?? "timed out"} · {check.durationMs} ms
              </dd>
            </div>
          </dl>
          {check.outputExcerpt ? (
            <pre className="proposal-file-change__content">
              <code>{check.outputExcerpt}</code>
            </pre>
          ) : (
            <p className="proposal-file-change__no-content">
              This check produced no output.
            </p>
          )}
        </details>
      ))}
    </div>
  );
}
