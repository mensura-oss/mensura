from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from mensura_core.application_models import (
    APPLICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS,
    ApplicationArtifact,
    ApplicationCollection,
    ApplicationGuardCheck,
    ApplicationGuardResult,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationTargetKind,
    ApplicationTargetMetadata,
    ApplicationUndoMetadata,
    ApplicationUndoStrategy,
    AppliedFileResult,
)
from mensura_core.application_repositories import ApplicationRepository
from mensura_core.application_writer import apply_proposal_changes
from mensura_core.change_proposal_models import ChangeProposal, ChangeProposalStatus
from mensura_core.change_proposal_repositories import ChangeProposalRepository
from mensura_core.event_publisher import EventPublisher, MensuraEvent
from mensura_core.exceptions import (
    ApplicationAlreadyExistsError,
    ApplicationContentIncompleteError,
    ApplicationEmptyProposalError,
    ApplicationNotFoundError,
    ApplicationProposalNotApprovedError,
    ApplicationVerificationMismatchError,
    ApplicationVerificationNotFoundError,
    ApplicationVerificationNotPassedError,
    ChangeProposalNotFoundError,
    GuardError,
    ResourceNotFoundError,
)
from mensura_core.git_workspace import resolve_live_head
from mensura_core.guard_config import GuardConfigurationLoader
from mensura_core.guard_execution import execute_guard_checks
from mensura_core.guard_models import GuardCheckKind, GuardCheckResult, GuardRunStatus
from mensura_core.guard_runner import GuardCommandRunner
from mensura_core.models import ChangeProposalChangeType, Workspace, ensure_utc_timestamp
from mensura_core.repositories import CoreRepository
from mensura_core.service import utc_now
from mensura_core.verification_models import ProposalVerification, ProposalVerificationStatus
from mensura_core.verification_repositories import ProposalVerificationRepository
from mensura_core.workspace_reservation import WorkspaceWriteReservation

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]
Monotonic = Callable[[], float]
HeadResolver = Callable[[str], str]

UNDO_NOTE = (
    "Undo is not executed automatically yet. Restore each prior digest/content and "
    "re-delete created files to revert this application later."
)


class ChangeApplicationService:
    """Apply an approved, verified proposal to the live working tree only when eligible."""

    def __init__(
        self,
        core_repository: CoreRepository,
        proposal_repository: ChangeProposalRepository,
        verification_repository: ProposalVerificationRepository,
        application_repository: ApplicationRepository,
        guard_configuration_loader: GuardConfigurationLoader,
        guard_command_runner: GuardCommandRunner,
        write_reservation: WorkspaceWriteReservation,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
        monotonic: Monotonic = perf_counter,
        head_resolver: HeadResolver = resolve_live_head,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._core_repository = core_repository
        self._proposal_repository = proposal_repository
        self._verification_repository = verification_repository
        self._application_repository = application_repository
        self._guard_configuration_loader = guard_configuration_loader
        self._guard_command_runner = guard_command_runner
        self._write_reservation = write_reservation
        self._id_factory = id_factory
        self._clock = clock
        self._monotonic = monotonic
        self._head_resolver = head_resolver
        self._event_publisher = event_publisher

    def apply(self, proposal_id: UUID, verification_id: UUID) -> ApplicationArtifact:
        proposal = self._require_proposal(proposal_id)
        if proposal.status is not ChangeProposalStatus.APPROVED:
            raise ApplicationProposalNotApprovedError(proposal.id, proposal.status)
        if any(change.truncated for change in proposal.file_changes):
            raise ApplicationContentIncompleteError(proposal.id)
        if not proposal.file_changes:
            raise ApplicationEmptyProposalError(proposal.id)
        verification = self._require_passing_verification(verification_id, proposal)
        if self._application_repository.get_for_proposal(proposal.id) is not None:
            raise ApplicationAlreadyExistsError(proposal.id)
        workspace = self._require_workspace(proposal.workspace_id)

        with self._write_reservation.reserve(
            workspace.id,
            holder_kind="application_apply",
            target_entity_type="change_proposal",
            target_entity_id=proposal.id,
        ):
            return self._apply_to_live(workspace, proposal, verification)

    def get(self, application_id: UUID) -> ApplicationArtifact:
        application = self._application_repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        return application

    def list_for_workspace(self, workspace_id: UUID) -> ApplicationCollection:
        self._require_workspace(workspace_id)
        items = tuple(self._application_repository.list_for_workspace(workspace_id))
        return ApplicationCollection(items=items, total=len(items))

    def _publish_application_event(self, application: ApplicationArtifact) -> None:
        if self._event_publisher is None:
            return
        summary = (
            f"Application {application.status.value}. "
            f"Applied: {application.summary.applied_count} files."
        )
        self._event_publisher.publish(
            MensuraEvent(
                event_type="application.created",
                workspace_id=application.workspace_id,
                entity_type="application",
                entity_id=application.id,
                status=application.status.value,
                summary=summary,
            )
        )

    def _apply_to_live(
        self,
        workspace: Workspace,
        proposal: ChangeProposal,
        verification: ProposalVerification,
    ) -> ApplicationArtifact:
        created_at = ensure_utc_timestamp(self._clock())
        started = self._monotonic()
        root = Path(workspace.root_path)

        # Validate the live repository and confirm Guard can load before any write.
        live_commit = self._head_resolver(workspace.root_path)
        self._guard_configuration_loader.load(workspace.root_path)

        # From here a write may occur, so an artifact is always persisted.
        write = apply_proposal_changes(root, proposal.file_changes)
        if write.partial:
            guard: ApplicationGuardResult | None = None
            guard_unavailable_reason: str | None = None
            status = ApplicationStatus.APPLICATION_FAILED
        else:
            guard, guard_unavailable_reason, status = self._run_live_guard(workspace.root_path)

        finished_at = ensure_utc_timestamp(self._clock())
        application = ApplicationArtifact(
            id=self._id_factory(),
            proposal_id=proposal.id,
            verification_id=verification.id,
            run_id=proposal.run_id,
            task_id=proposal.task_id,
            workspace_id=proposal.workspace_id,
            context_pack_id=proposal.context_pack_id,
            status=status,
            target=ApplicationTargetMetadata(
                kind=ApplicationTargetKind.LIVE_WORKING_TREE,
                live_commit_id=live_commit,
                verification_commit_id=verification.sandbox.commit_id,
                head_moved_since_verification=(live_commit != verification.sandbox.commit_id),
            ),
            guard=guard,
            guard_unavailable_reason=guard_unavailable_reason,
            file_results=write.file_results,
            summary=self._summary(write.file_results),
            undo=ApplicationUndoMetadata(
                strategy=ApplicationUndoStrategy.RESTORE_PRIOR_CONTENT,
                note=UNDO_NOTE,
                captured_at=created_at,
                files=write.undo_files,
            ),
            created_at=created_at,
            finished_at=max(created_at, finished_at),
            duration_ms=max(0, round((self._monotonic() - started) * 1000)),
        )
        self._application_repository.save_if_absent_for_proposal(application)
        self._publish_application_event(application)
        return application

    def _run_live_guard(
        self, root: str
    ) -> tuple[ApplicationGuardResult | None, str | None, ApplicationStatus]:
        try:
            execution = execute_guard_checks(
                root,
                [GuardCheckKind.LINT, GuardCheckKind.TEST],
                configuration_loader=self._guard_configuration_loader,
                command_runner=self._guard_command_runner,
                clock=self._clock,
                monotonic=self._monotonic,
            )
        except GuardError as error:
            reason = (
                f"Guard could not run against the live working tree after apply. {error.detail}"
            )
            return None, reason[:500], ApplicationStatus.APPLIED_GUARD_UNAVAILABLE

        guard = ApplicationGuardResult(
            status=execution.status,
            blocking=execution.summary.is_blocking,
            summary=execution.summary,
            checks=[self._compact_check(check) for check in execution.checks],
        )
        status = (
            ApplicationStatus.APPLIED_GUARD_PASSED
            if execution.status is GuardRunStatus.PASSED
            else ApplicationStatus.APPLIED_GUARD_FAILED
        )
        return guard, None, status

    @staticmethod
    def _compact_check(check: GuardCheckResult) -> ApplicationGuardCheck:
        combined = "\n".join(part for part in (check.stdout.strip(), check.stderr.strip()) if part)
        excerpt = combined[-APPLICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS:]
        return ApplicationGuardCheck(
            kind=check.kind,
            status=check.status,
            blocking=check.blocking,
            summary=check.summary,
            exit_code=check.exit_code,
            duration_ms=check.duration_ms,
            output_excerpt=excerpt,
            output_truncated=check.output_truncated or len(excerpt) < len(combined),
        )

    @staticmethod
    def _summary(file_results: tuple[AppliedFileResult, ...]) -> ApplicationSummary:
        applied = sum(result.applied for result in file_results)
        return ApplicationSummary(
            files_total=len(file_results),
            created_count=sum(
                result.change_type is ChangeProposalChangeType.CREATE for result in file_results
            ),
            modified_count=sum(
                result.change_type is ChangeProposalChangeType.MODIFY for result in file_results
            ),
            deleted_count=sum(
                result.change_type is ChangeProposalChangeType.DELETE for result in file_results
            ),
            applied_count=applied,
            failed_count=len(file_results) - applied,
        )

    def _require_passing_verification(
        self, verification_id: UUID, proposal: ChangeProposal
    ) -> ProposalVerification:
        verification = self._verification_repository.get(verification_id)
        if verification is None:
            raise ApplicationVerificationNotFoundError(verification_id)
        if verification.proposal_id != proposal.id:
            raise ApplicationVerificationMismatchError(verification_id, proposal.id)
        if verification.status is not ProposalVerificationStatus.PASSED:
            raise ApplicationVerificationNotPassedError(verification_id, verification.status)
        return verification

    def _require_proposal(self, proposal_id: UUID) -> ChangeProposal:
        proposal = self._proposal_repository.get(proposal_id)
        if proposal is None:
            raise ChangeProposalNotFoundError(proposal_id)
        return proposal

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._core_repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace
