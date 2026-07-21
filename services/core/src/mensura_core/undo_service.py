from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from mensura_core.application_models import (
    ApplicationArtifact,
    ApplicationStatus,
)
from mensura_core.application_repositories import ApplicationRepository
from mensura_core.event_publisher import EventPublisher, MensuraEvent
from mensura_core.exceptions import (
    ApplicationNotFoundError,
    GuardError,
    ResourceNotFoundError,
    UndoAlreadyExistsError,
    UndoMetadataIncompleteError,
    UndoNotEligibleError,
)
from mensura_core.guard_config import GuardConfigurationLoader
from mensura_core.guard_execution import execute_guard_checks
from mensura_core.guard_models import GuardCheckKind, GuardCheckResult, GuardRunStatus
from mensura_core.guard_runner import GuardCommandRunner
from mensura_core.models import ChangeProposalChangeType, Workspace, ensure_utc_timestamp
from mensura_core.repositories import CoreRepository
from mensura_core.service import utc_now
from mensura_core.undo_models import (
    UNDO_GUARD_OUTPUT_EXCERPT_MAX_CHARS,
    UndoArtifact,
    UndoCollection,
    UndoGuardCheck,
    UndoGuardResult,
    UndoStatus,
)
from mensura_core.undo_repositories import UndoRepository
from mensura_core.undo_writer import execute_undo

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]
Monotonic = Callable[[], float]


class UndoService:
    """Explicitly undo a text-file application using only recorded undo metadata."""

    def __init__(
        self,
        core_repository: CoreRepository,
        application_repository: ApplicationRepository,
        undo_repository: UndoRepository,
        guard_configuration_loader: GuardConfigurationLoader,
        guard_command_runner: GuardCommandRunner,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
        monotonic: Monotonic = perf_counter,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._core_repository = core_repository
        self._application_repository = application_repository
        self._undo_repository = undo_repository
        self._guard_configuration_loader = guard_configuration_loader
        self._guard_command_runner = guard_command_runner
        self._id_factory = id_factory
        self._clock = clock
        self._monotonic = monotonic
        self._event_publisher = event_publisher

    def undo(self, application_id: UUID) -> UndoArtifact:
        application = self._application_repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        self._assert_eligible(application)
        if self._undo_repository.get_for_application(application.id) is not None:
            raise UndoAlreadyExistsError(application.id)
        workspace = self._require_workspace(application.workspace_id)
        return self._execute_undo(workspace, application)

    def get(self, undo_id: UUID) -> UndoArtifact:
        undo = self._undo_repository.get(undo_id)
        if undo is None:
            from mensura_core.exceptions import UndoNotFoundError
            raise UndoNotFoundError(undo_id)
        return undo

    def list_for_workspace(self, workspace_id: UUID) -> UndoCollection:
        self._require_workspace(workspace_id)
        items = tuple(self._undo_repository.list_for_workspace(workspace_id))
        return UndoCollection(items=items, total=len(items))

    def _assert_eligible(self, application: ApplicationArtifact) -> None:
        if application.status is ApplicationStatus.APPLICATION_FAILED:
            raise UndoNotEligibleError(
                application.id,
                "The application did not complete successfully and cannot be undone.",
            )
        if not application.undo.files:
            raise UndoNotEligibleError(
                application.id, "The application has no undo metadata."
            )
        for entry in application.undo.files:
            if entry.change_type in (
                ChangeProposalChangeType.MODIFY,
                ChangeProposalChangeType.DELETE,
            ) and entry.prior_truncated:
                raise UndoMetadataIncompleteError(entry.path)

    def _execute_undo(
        self, workspace: Workspace, application: ApplicationArtifact
    ) -> UndoArtifact:
        created_at = ensure_utc_timestamp(self._clock())
        started = self._monotonic()
        root = Path(workspace.root_path)

        try:
            write = execute_undo(root, application.undo.files)
        except Exception as error:
            return self._refusal_artifact(
                application, created_at, started, str(error)
            )

        guard: UndoGuardResult | None = None
        guard_unavailable_reason: str | None = None
        if write.partial:
            status = UndoStatus.UNDO_FAILED
        else:
            guard, guard_unavailable_reason, status = self._run_post_undo_guard(
                workspace.root_path
            )

        finished_at = ensure_utc_timestamp(self._clock())
        undo_artifact = UndoArtifact(
            id=self._id_factory(),
            application_id=application.id,
            proposal_id=application.proposal_id,
            workspace_id=application.workspace_id,
            status=status,
            file_outcomes=write.outcomes,
            guard=guard,
            guard_unavailable_reason=guard_unavailable_reason,
            created_at=created_at,
            finished_at=max(created_at, finished_at),
            duration_ms=max(0, round((self._monotonic() - started) * 1000)),
        )
        self._undo_repository.save_if_absent_for_application(undo_artifact)
        self._publish_undo_event(undo_artifact)
        return undo_artifact

    def _refusal_artifact(
        self,
        application: ApplicationArtifact,
        created_at: datetime,
        started: float,
        reason: str,
    ) -> UndoArtifact:
        finished_at = ensure_utc_timestamp(self._clock())
        undo_artifact = UndoArtifact(
            id=self._id_factory(),
            application_id=application.id,
            proposal_id=application.proposal_id,
            workspace_id=application.workspace_id,
            status=UndoStatus.UNDO_REFUSED,
            file_outcomes=(),
            guard=None,
            guard_unavailable_reason=reason,
            created_at=created_at,
            finished_at=max(created_at, finished_at),
            duration_ms=max(0, round((self._monotonic() - started) * 1000)),
        )
        self._undo_repository.save_if_absent_for_application(undo_artifact)
        self._publish_undo_event(undo_artifact)
        return undo_artifact

    def _publish_undo_event(self, undo: UndoArtifact) -> None:
        if self._event_publisher is None:
            return
        summary = f"Undo {undo.status.value}."
        self._event_publisher.publish(
            MensuraEvent(
                event_type="undo.created",
                workspace_id=undo.workspace_id,
                entity_type="undo",
                entity_id=undo.id,
                status=undo.status.value,
                summary=summary,
            )
        )

    def _run_post_undo_guard(
        self, root: str
    ) -> tuple[UndoGuardResult | None, str | None, UndoStatus]:
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
                f"Guard could not run against the live working tree after undo. {error.detail}"
            )
            return None, reason[:500], UndoStatus.UNDONE_GUARD_FAILED

        guard = UndoGuardResult(
            status=execution.status,
            blocking=execution.summary.is_blocking,
            summary=execution.summary,
            checks=[self._compact_undo_check(check) for check in execution.checks],
        )
        status = (
            UndoStatus.UNDONE_GUARD_PASSED
            if execution.status is GuardRunStatus.PASSED
            else UndoStatus.UNDONE_GUARD_FAILED
        )
        return guard, None, status

    @staticmethod
    def _compact_undo_check(check: GuardCheckResult) -> UndoGuardCheck:
        combined = "\n".join(
            part for part in (check.stdout.strip(), check.stderr.strip()) if part
        )
        excerpt = combined[-UNDO_GUARD_OUTPUT_EXCERPT_MAX_CHARS:]
        return UndoGuardCheck(
            kind=check.kind,
            status=check.status,
            blocking=check.blocking,
            summary=check.summary,
            exit_code=check.exit_code,
            duration_ms=check.duration_ms,
            output_excerpt=excerpt,
            output_truncated=check.output_truncated or len(excerpt) < len(combined),
        )

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._core_repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace
