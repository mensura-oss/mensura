import type {
  ChangeProposal,
  ChangeProposalCollection,
  ChangeProposalFileChange,
  Run,
} from "@mensura/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";
import { ProposalVerificationSection } from "./ProposalVerificationSection";

export function ChangeProposalPanel({ run }: { run: Run }) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const workspaceId = run.contextPack.workspaceId;
  const proposals = useQuery({
    queryKey: queryKeys.changeProposals(workspaceId),
    queryFn: () => client.listChangeProposals(workspaceId),
    retry: false,
  });
  const create = useMutation({
    mutationFn: () => client.createChangeProposal(run.id),
    onSuccess: (result) => updateProposalCache(queryClient, result.proposal),
  });
  const review = useMutation<
    ChangeProposal,
    Error,
    { proposalId: string; decision: "approve" | "reject" }
  >({
    mutationFn: ({ proposalId, decision }) =>
      decision === "approve"
        ? client.approveChangeProposal(proposalId)
        : client.rejectChangeProposal(proposalId),
    onSuccess: (reviewed) => updateProposalCache(queryClient, reviewed),
  });
  const proposal =
    review.data ??
    create.data?.proposal ??
    proposals.data?.items.find((item) => item.runId === run.id);

  if (run.status !== "succeeded") return null;

  return (
    <section className="change-proposal" aria-labelledby={`proposal-${run.id}`}>
      <div className="change-proposal__heading">
        <div>
          <span className="section-label">Write-isolated artifact</span>
          <h4 id={`proposal-${run.id}`}>Change proposal</h4>
        </div>
        {proposal ? (
          <span className={`badge badge--${proposal.status}`}>{proposal.status}</span>
        ) : null}
      </div>

      <p className="change-proposal__boundary">
        Review decisions are recorded on this artifact only. Mensura will not apply,
        stage, commit, or otherwise write these suggestions to the repository.
      </p>

      {proposals.isPending && !proposal ? (
        <LoadingState>Checking for an existing proposal…</LoadingState>
      ) : null}
      {proposals.isError && !proposal ? (
        <ProblemDetailsView error={proposals.error} />
      ) : null}

      {!proposal && !proposals.isPending ? (
        <div className="change-proposal__create">
          <p>
            Materialize the successful run&apos;s validated proposal draft as a separate,
            reviewable artifact.
          </p>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => create.mutate()}
            disabled={create.isPending}
          >
            {create.isPending ? "Creating proposal…" : "Create proposal"}
          </button>
        </div>
      ) : null}
      {create.isError ? <ProblemDetailsView error={create.error} /> : null}

      {proposal ? (
        <ProposalReview
          proposal={proposal}
          reviewing={review.isPending}
          onReview={(decision) =>
            review.mutate({ proposalId: proposal.id, decision })
          }
        />
      ) : null}
      {review.isError ? <ProblemDetailsView error={review.error} /> : null}
      {proposal ? <ProposalVerificationSection proposal={proposal} /> : null}
    </section>
  );
}

function ProposalReview({
  proposal,
  reviewing,
  onReview,
}: {
  proposal: ChangeProposal;
  reviewing: boolean;
  onReview: (decision: "approve" | "reject") => void;
}) {
  return (
    <div className="proposal-review" aria-live="polite">
      <dl className="proposal-review__lineage">
        <div>
          <dt>Proposal</dt>
          <dd>
            <code>{proposal.id}</code>
          </dd>
        </div>
        <div>
          <dt>Source run</dt>
          <dd>
            <code>{proposal.runId}</code>
          </dd>
        </div>
        <div>
          <dt>Immutable context</dt>
          <dd>
            <code>{proposal.contextPackId}</code>
          </dd>
        </div>
        <div>
          <dt>Provider / prompt</dt>
          <dd>
            {proposal.providerId} · {proposal.promptVersion}
          </dd>
        </div>
      </dl>

      <div className="proposal-review__copy">
        <div>
          <span>Summary</span>
          <p>{proposal.summary}</p>
        </div>
        <div>
          <span>Rationale</span>
          <p>{proposal.rationale}</p>
        </div>
      </div>

      <div className="proposal-review__files">
        <div className="proposal-review__files-heading">
          <strong>Proposed file changes</strong>
          <span>{proposal.fileChanges.length}</span>
        </div>
        {proposal.fileChanges.length ? (
          proposal.fileChanges.map((change) => (
            <ProposalFileChange key={`${change.changeType}:${change.path}`} change={change} />
          ))
        ) : (
          <p className="proposal-review__empty">
            This provider did not propose file changes from the available evidence.
          </p>
        )}
      </div>

      {proposal.status === "proposed" ? (
        <div className="proposal-review__actions">
          <button
            className="button button--secondary"
            type="button"
            onClick={() => onReview("approve")}
            disabled={reviewing}
          >
            {reviewing ? "Recording decision…" : "Approve proposal"}
          </button>
          <button
            className="button button--danger"
            type="button"
            onClick={() => onReview("reject")}
            disabled={reviewing}
          >
            Reject proposal
          </button>
        </div>
      ) : (
        <p className="proposal-review__decision" role="status">
          Review recorded as <strong>{proposal.status}</strong> at{" "}
          {formatTimestamp(proposal.reviewedAt)}. No repository changes were applied.
        </p>
      )}
    </div>
  );
}

function ProposalFileChange({ change }: { change: ChangeProposalFileChange }) {
  return (
    <details className="proposal-file-change">
      <summary>
        <code>{change.path}</code>
        <span className={`badge badge--${change.changeType}`}>{change.changeType}</span>
        {change.truncated ? <span className="badge badge--warning">truncated</span> : null}
      </summary>
      <dl>
        <div>
          <dt>Language</dt>
          <dd>{change.language ?? "Not detected"}</dd>
        </div>
        <div>
          <dt>Before digest</dt>
          <dd>
            <code>{change.beforeDigest ?? "New file"}</code>
          </dd>
        </div>
        <div>
          <dt>After digest</dt>
          <dd>
            <code>{change.afterDigest ?? "Deleted file"}</code>
          </dd>
        </div>
        <div>
          <dt>Stored / original</dt>
          <dd>
            {formatBytes(change.proposedTextBytes)} / {formatBytes(change.originalTextBytes)}
          </dd>
        </div>
      </dl>
      {change.proposedText !== null ? (
        <pre className="proposal-file-change__content">
          <code>{change.proposedText}</code>
        </pre>
      ) : (
        <p className="proposal-file-change__no-content">
          No content body is stored for this {change.changeType} proposal.
        </p>
      )}
    </details>
  );
}

function updateProposalCache(
  queryClient: ReturnType<typeof useQueryClient>,
  proposal: ChangeProposal,
) {
  queryClient.setQueryData(queryKeys.changeProposal(proposal.id), proposal);
  queryClient.setQueryData<ChangeProposalCollection>(
    queryKeys.changeProposals(proposal.workspaceId),
    (current) => {
      const items = current?.items ?? [];
      const next = items.some((item) => item.id === proposal.id)
        ? items.map((item) => (item.id === proposal.id ? proposal : item))
        : [...items, proposal];
      return { items: next, total: next.length };
    },
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KiB`;
}
