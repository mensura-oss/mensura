import type {
  ApplicationArtifact,
  ApplicationCollection,
  ApplicationGuardResult,
  ApplicationStatus,
  AppliedFileReason,
  ChangeProposal,
  ProposalVerification,
  UndoArtifact,
  UndoCollection,
  UndoFileAction,
} from "@mensura/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";

const STATUS_COPY: Record<ApplicationStatus, string> = {
  applied_guard_passed:
    "The verified content was written to the live working tree and Guard passed there.",
  applied_guard_failed:
    "The verified content was written to the live working tree, but Guard failed against it. Nothing was reverted.",
  applied_guard_unavailable:
    "The verified content was written to the live working tree, but Guard could not run there, so its result is unknown.",
  application_failed:
    "The application only partially wrote the live working tree. Review the per-file results before doing anything else.",
};

const FILE_REASON_COPY: Record<AppliedFileReason, string> = {
  applied: "Applied to live tree",
  write_failed: "Write failed",
  not_attempted: "Not attempted",
};

function statusTone(status: ApplicationStatus): "passed" | "failed" | "warning" {
  if (status === "applied_guard_passed") return "passed";
  if (status === "applied_guard_unavailable") return "warning";
  return "failed";
}

function shortDigest(digest: string | null, fallback: string): string {
  if (digest === null) return fallback;
  return digest.replace(/^sha256:/, "").slice(0, 12);
}

export function ProposalApplicationSection({
  proposal,
}: {
  proposal: ChangeProposal;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const workspaceId = proposal.workspaceId;

  const verifications = useQuery({
    queryKey: queryKeys.changeProposalVerifications(proposal.id),
    queryFn: () => client.listChangeProposalVerifications(proposal.id),
    retry: false,
  });
  const applications = useQuery({
    queryKey: queryKeys.workspaceApplications(workspaceId),
    queryFn: () => client.listWorkspaceApplications(workspaceId),
    retry: false,
  });
  const undos = useQuery({
    queryKey: queryKeys.workspaceUndos(workspaceId),
    queryFn: () => client.listWorkspaceUndos(workspaceId),
    retry: false,
    enabled: workspaceId !== null,
  });

  const apply = useMutation({
    mutationFn: (verificationId: string) =>
      client.applyChangeProposal(proposal.id, { verificationId }),
    onSuccess: (application) => {
      queryClient.setQueryData(
        queryKeys.application(application.id),
        application,
      );
      queryClient.setQueryData<ApplicationCollection>(
        queryKeys.workspaceApplications(workspaceId),
        (current) => {
          const items = [
            ...(current?.items ?? []).filter(
              (item) => item.id !== application.id,
            ),
            application,
          ];
          return { items, total: items.length };
        },
      );
    },
  });

  const undo = useMutation({
    mutationFn: (applicationId: string) =>
      client.undoApplication(applicationId),
    onSuccess: (undoArtifact) => {
      queryClient.setQueryData(
        queryKeys.undo(undoArtifact.id),
        undoArtifact,
      );
      queryClient.setQueryData<UndoCollection>(
        queryKeys.workspaceUndos(workspaceId),
        (current) => {
          const items = [
            ...(current?.items ?? []).filter(
              (item) => item.id !== undoArtifact.id,
            ),
            undoArtifact,
          ];
          return { items, total: items.length };
        },
      );
    },
  });

  if (proposal.status !== "approved") return null;

  const verificationItems = verifications.data?.items ?? [];
  const passingVerification = [...verificationItems]
    .reverse()
    .find((item) => item.status === "passed");
  const existing = applications.data?.items.find(
    (item) => item.proposalId === proposal.id,
  );
  const application = apply.data ?? existing;
  const existingUndo = application
    ? undos.data?.items.find(
        (item) => item.applicationId === application.id,
      )
    : undefined;
  const undoArtifact = undo.data ?? existingUndo;

  return (
    <section
      className="proposal-application"
      aria-labelledby={`application-${proposal.id}`}
    >
      <div className="change-proposal__heading">
        <div>
          <span className="section-label">Live application</span>
          <h4 id={`application-${proposal.id}`}>Apply to live working tree</h4>
        </div>
        {application ? (
          <span className={`badge badge--${statusTone(application.status)}`}>
            {application.status}
          </span>
        ) : null}
      </div>

      <p className="proposal-application__boundary">
        This is a high-trust action. It writes the <strong>verified</strong>{" "}
        content to your <strong>live working tree</strong>. It still does not
        commit, stage, or push, and no model provider is involved. Git history is
        untouched; the changes simply appear in your working files.
      </p>

      {verifications.isPending || applications.isPending ? (
        <LoadingState>Checking application preconditions…</LoadingState>
      ) : null}
      {applications.isError ? (
        <ProblemDetailsView error={applications.error} />
      ) : null}

      {application ? (
        <ApplicationResult
          application={application}
          undoArtifact={undoArtifact}
          isUndoing={undo.isPending}
          onUndo={() => undo.mutate(application.id)}
          undoError={undo.error}
        />
      ) : (
        <ApplyGate
          hasVerification={verificationItems.length > 0}
          passingVerification={passingVerification}
          pending={apply.isPending}
          onApply={(verificationId) => apply.mutate(verificationId)}
        />
      )}
      {apply.isError ? <ProblemDetailsView error={apply.error} /> : null}
    </section>
  );
}

function ApplyGate({
  hasVerification,
  passingVerification,
  pending,
  onApply,
}: {
  hasVerification: boolean;
  passingVerification: ProposalVerification | undefined;
  pending: boolean;
  onApply: (verificationId: string) => void;
}) {
  const gates: { label: string; met: boolean }[] = [
    { label: "Proposal approved", met: true },
    { label: "Verified in isolated sandbox", met: hasVerification },
    { label: "Verification passed", met: Boolean(passingVerification) },
    { label: "Not yet applied", met: true },
  ];

  return (
    <div className="proposal-application__gate">
      <ul className="application-gate" aria-label="Application preconditions">
        {gates.map((gate) => (
          <li key={gate.label}>
            <span
              className={`badge badge--${gate.met ? "passed" : "failed"}`}
              aria-hidden="true"
            >
              {gate.met ? "✓" : "✗"}
            </span>
            <span>{gate.label}</span>
          </li>
        ))}
      </ul>

      {passingVerification ? (
        <div className="proposal-application__actions">
          <button
            className="button button--primary"
            type="button"
            onClick={() => onApply(passingVerification.id)}
            disabled={pending}
          >
            {pending ? "Applying to live working tree…" : "Apply to live working tree"}
          </button>
          <span className="proposal-application__uses">
            Uses passing verification{" "}
            <code>{passingVerification.id.slice(0, 8)}</code>
          </span>
        </div>
      ) : (
        <p className="proposal-application__blocked" role="status">
          Applying is unavailable until this approved proposal has a passing
          verification. Run verification above first.
        </p>
      )}
    </div>
  );
}

const UNDO_STATUS_COPY: Record<string, string> = {
  undone_guard_passed:
    "Content was restored to the live working tree and Guard passed.",
  undone_guard_failed:
    "Content was restored to the live working tree, but Guard failed. Nothing was reverted.",
  undo_refused:
    "Undo was refused before writing. The live working tree is unchanged.",
  undo_failed:
    "Undo partially restored the live working tree. Review the per-file outcomes before doing anything else.",
};

const UNDO_ACTION_COPY: Record<string, string> = {
  restored: "Prior content restored",
  deleted: "Created file removed",
  refused: "Refused",
  failed: "Write failed",
};

function undoStatusTone(
  status: string,
): "passed" | "failed" | "warning" | "running" {
  if (status === "undone_guard_passed") return "passed";
  if (status === "undo_refused") return "warning";
  return "failed";
}

const APPLIED_OUTCOMES: readonly string[] = [
  "applied_guard_passed",
  "applied_guard_failed",
  "applied_guard_unavailable",
];

function UndoSection({
  application,
  undoArtifact,
  isUndoing,
  onUndo,
  undoError,
}: {
  application: ApplicationArtifact;
  undoArtifact: UndoArtifact | undefined;
  isUndoing: boolean;
  onUndo: () => void;
  undoError: unknown;
}) {
  const isEligible =
    APPLIED_OUTCOMES.includes(application.status) && !undoArtifact;
  const hasTruncated = application.undo.files.some(
    (file) =>
      file.changeType !== "create" && file.priorTruncated,
  );

  if (undoArtifact) {
    return <UndoResult undo={undoArtifact} />;
  }

  if (!isEligible) return null;

  return (
    <div className="proposal-application__undo-action">
      <div className="proposal-review__files-heading">
        <strong>Undo application</strong>
      </div>
      <p>
        Restore prior content and remove created files. The live working tree must
        still match the recorded applied digests. If files have changed since
        application, undo will be refused before any write.
      </p>
      {hasTruncated ? (
        <p className="proposal-application__blocked" role="status">
          Undo metadata is incomplete — some files have truncated prior content
          and require external recovery.
        </p>
      ) : (
        <button
          className="button button--primary"
          type="button"
          onClick={onUndo}
          disabled={isUndoing}
        >
          {isUndoing ? "Undoing…" : "Undo application"}
        </button>
      )}
      {undoError ? <ProblemDetailsView error={undoError} /> : null}
    </div>
  );
}

function UndoResult({ undo }: { undo: UndoArtifact }) {
  return (
    <div className="proposal-application__undo-result" aria-live="polite">
      <div className="proposal-review__files-heading">
        <strong>Undo result</strong>
        <span className={`badge badge--${undoStatusTone(undo.status)}`}>
          {undo.status}
        </span>
      </div>
      <p className="proposal-application__outcome">
        {UNDO_STATUS_COPY[undo.status] ?? undo.status}
      </p>
      <dl className="proposal-review__lineage">
        <div>
          <dt>Undo</dt>
          <dd>
            <code>{undo.id}</code>
          </dd>
        </div>
        <div>
          <dt>Application</dt>
          <dd>
            <code>{undo.applicationId}</code>
          </dd>
        </div>
        <div>
          <dt>Finished</dt>
          <dd>
            {formatTimestamp(undo.finishedAt)} · {undo.durationMs} ms
          </dd>
        </div>
      </dl>

      {undo.fileOutcomes.length > 0 ? (
        <div className="proposal-review__files">
          <div className="proposal-review__files-heading">
            <strong>File outcomes</strong>
            <span>{undo.fileOutcomes.length}</span>
          </div>
          {undo.fileOutcomes.map((outcome) => (
            <div
              key={`${outcome.changeType}:${outcome.path}`}
              className="proposal-application__file"
            >
              <code>{outcome.path}</code>
              <span className={`badge badge--${outcome.changeType}`}>
                {outcome.changeType}
              </span>
              <span
                className={`badge badge--${outcome.undone ? "passed" : "failed"}`}
              >
                {UNDO_ACTION_COPY[outcome.action] ?? outcome.action}
              </span>
              <span className="proposal-application__digest">
                {shortDigest(outcome.observedLiveDigest, "—")} →{" "}
                {shortDigest(outcome.priorDigestRestored, "—")}
              </span>
            </div>
          ))}
        </div>
      ) : null}

      {undo.guard ? (
        <div className="proposal-application__guard">
          <div className="proposal-review__files-heading">
            <strong>Guard after undo</strong>
            <span className={`badge badge--${undo.guard.status}`}>
              {undo.guard.status}
              {undo.guard.blocking ? " · blocking" : ""}
            </span>
          </div>
          <p className="proposal-application__guard-summary">
            {undo.guard.summary.passedCount} passed ·{" "}
            {undo.guard.summary.failedCount} failed ·{" "}
            {undo.guard.summary.errorCount} errored
          </p>
          {undo.guard.checks.map((check) => (
            <details key={check.kind} className="proposal-file-change">
              <summary>
                <code>{check.kind}</code>
                <span className={`badge badge--${check.status}`}>
                  {check.status}
                </span>
              </summary>
              <dl>
                <div>
                  <dt>Summary</dt>
                  <dd>{check.summary}</dd>
                </div>
                <div>
                  <dt>Exit / duration</dt>
                  <dd>
                    {check.exitCode ?? "—"} · {check.durationMs} ms
                  </dd>
                </div>
              </dl>
              {check.outputExcerpt ? (
                <pre className="proposal-file-change__content">
                  <code>{check.outputExcerpt}</code>
                </pre>
              ) : null}
            </details>
          ))}
        </div>
      ) : undo.guardUnavailableReason ? (
        <p className="proposal-application__no-guard" role="status">
          {undo.guardUnavailableReason}
        </p>
      ) : null}
    </div>
  );
}

function ApplicationResult({
  application,
  undoArtifact,
  isUndoing,
  onUndo,
  undoError,
}: {
  application: ApplicationArtifact;
  undoArtifact: UndoArtifact | undefined;
  isUndoing: boolean;
  onUndo: () => void;
  undoError: unknown;
}) {
  const restorable = application.undo.files.filter(
    (file) => !file.priorTruncated,
  ).length;

  return (
    <div className="proposal-application__result" aria-live="polite">
      <p className="proposal-application__outcome">
        {STATUS_COPY[application.status]}
      </p>

      <dl className="proposal-review__lineage">
        <div>
          <dt>Application</dt>
          <dd>
            <code>{application.id}</code>
          </dd>
        </div>
        <div>
          <dt>Verification used</dt>
          <dd>
            <code>{application.verificationId}</code>
          </dd>
        </div>
        <div>
          <dt>Live target</dt>
          <dd>
            Working tree at commit{" "}
            <code>{application.target.liveCommitId.slice(0, 12)}</code>
            {application.target.headMovedSinceVerification ? (
              <span className="badge badge--warning">
                HEAD moved since verification
              </span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Finished</dt>
          <dd>
            {formatTimestamp(application.finishedAt)} · {application.durationMs}{" "}
            ms
          </dd>
        </div>
        <div>
          <dt>Summary</dt>
          <dd>
            {application.summary.appliedCount}/{application.summary.filesTotal}{" "}
            applied · {application.summary.createdCount} create ·{" "}
            {application.summary.modifiedCount} modify ·{" "}
            {application.summary.deletedCount} delete
            {application.summary.failedCount > 0
              ? ` · ${application.summary.failedCount} failed`
              : ""}
          </dd>
        </div>
      </dl>

      <div className="proposal-review__files">
        <div className="proposal-review__files-heading">
          <strong>Digest-checked file writes</strong>
          <span>{application.fileResults.length}</span>
        </div>
        {application.fileResults.map((result) => (
          <div
            key={`${result.changeType}:${result.path}`}
            className="proposal-application__file"
          >
            <code>{result.path}</code>
            <span className={`badge badge--${result.changeType}`}>
              {result.changeType}
            </span>
            <span
              className={`badge badge--${result.applied ? "passed" : "failed"}`}
            >
              {FILE_REASON_COPY[result.reason]}
            </span>
            <span className="proposal-application__digest">
              {shortDigest(result.liveBeforeDigest, "new")} →{" "}
              {shortDigest(result.appliedDigest, "removed")}
            </span>
          </div>
        ))}
      </div>

      {application.guard ? (
        <ApplicationGuardOutcome guard={application.guard} />
      ) : application.guardUnavailableReason ? (
        <p className="proposal-application__no-guard" role="status">
          {application.guardUnavailableReason}
        </p>
      ) : (
        <p className="proposal-application__no-guard" role="status">
          Guard did not run because the application did not complete.
        </p>
      )}

      <div className="proposal-application__undo">
        <div className="proposal-review__files-heading">
          <strong>Undo basis</strong>
          <span>{application.undo.files.length}</span>
        </div>
        <p>
          Restoration data captured for {application.undo.files.length}{" "}
          {application.undo.files.length === 1 ? "file" : "files"} (
          {restorable} fully restorable). {application.undo.note}
        </p>
        {application.undo.files.map((file) => (
          <div
            key={`${file.changeType}:${file.path}`}
            className="proposal-application__undo-file"
          >
            <code>{file.path}</code>
            <span>
              {file.priorExisted
                ? `prior ${shortDigest(file.priorDigest, "—")}`
                : "did not exist"}
            </span>
            {file.priorTruncated ? (
              <span className="badge badge--warning">
                needs external recovery
              </span>
            ) : null}
          </div>
        ))}
      </div>

      <UndoSection
        application={application}
        undoArtifact={undoArtifact}
        isUndoing={isUndoing}
        onUndo={onUndo}
        undoError={undoError}
      />

      <p className="proposal-review__decision" role="status">
        Applied to the live working tree only. No commit, stage, or push was
        performed, and Mensura did not contact any model provider.
      </p>
    </div>
  );
}

function ApplicationGuardOutcome({ guard }: { guard: ApplicationGuardResult }) {
  return (
    <div className="proposal-application__guard">
      <div className="proposal-review__files-heading">
        <strong>Guard on live tree</strong>
        <span className={`badge badge--${guard.status}`}>
          {guard.status}
          {guard.blocking ? " · blocking" : ""}
        </span>
      </div>
      <p className="proposal-application__guard-summary">
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
