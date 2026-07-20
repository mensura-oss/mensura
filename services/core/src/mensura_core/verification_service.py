from collections.abc import Callable
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import perf_counter
from uuid import UUID, uuid4

from mensura_core.change_proposal_models import (
    ChangeProposal,
    ChangeProposalFileChange,
    ChangeProposalStatus,
)
from mensura_core.change_proposal_repositories import ChangeProposalRepository
from mensura_core.exceptions import (
    ChangeProposalNotFoundError,
    ProposalVerificationContentIncompleteError,
    ProposalVerificationInProgressError,
    ProposalVerificationNotAllowedError,
    ProposalVerificationNotFoundError,
    ResourceNotFoundError,
)
from mensura_core.guard_config import GuardConfigurationLoader
from mensura_core.guard_execution import execute_guard_checks
from mensura_core.guard_models import GuardCheckKind, GuardCheckResult, GuardRunStatus
from mensura_core.guard_runner import GuardCommandRunner
from mensura_core.models import ChangeProposalChangeType, Workspace, ensure_utc_timestamp
from mensura_core.repositories import CoreRepository
from mensura_core.service import utc_now
from mensura_core.verification_models import (
    VERIFICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS,
    FileVerificationReason,
    FileVerificationResult,
    ProposalVerification,
    ProposalVerificationCollection,
    ProposalVerificationOutcome,
    ProposalVerificationStatus,
    SafeDiffMetadata,
    VerificationGuardCheck,
    VerificationGuardResult,
    VerificationSandboxKind,
    VerificationSandboxMetadata,
)
from mensura_core.verification_repositories import ProposalVerificationRepository
from mensura_core.verification_sandbox import VerificationSandbox, VerificationSandboxFactory

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]
Monotonic = Callable[[], float]


class ProposalVerificationService:
    """Verify approved proposals inside a temporary isolated sandbox only."""

    def __init__(
        self,
        core_repository: CoreRepository,
        proposal_repository: ChangeProposalRepository,
        verification_repository: ProposalVerificationRepository,
        sandbox_factory: VerificationSandboxFactory,
        guard_configuration_loader: GuardConfigurationLoader,
        guard_command_runner: GuardCommandRunner,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
        monotonic: Monotonic = perf_counter,
    ) -> None:
        self._core_repository = core_repository
        self._proposal_repository = proposal_repository
        self._verification_repository = verification_repository
        self._sandbox_factory = sandbox_factory
        self._guard_configuration_loader = guard_configuration_loader
        self._guard_command_runner = guard_command_runner
        self._id_factory = id_factory
        self._clock = clock
        self._monotonic = monotonic
        self._active_workspaces: set[UUID] = set()
        self._active_lock = Lock()

    def verify(self, proposal_id: UUID) -> ProposalVerification:
        proposal = self._require_proposal(proposal_id)
        if proposal.status is not ChangeProposalStatus.APPROVED:
            raise ProposalVerificationNotAllowedError(proposal.id, proposal.status)
        if any(change.truncated for change in proposal.file_changes):
            raise ProposalVerificationContentIncompleteError(proposal.id)
        workspace = self._require_workspace(proposal.workspace_id)

        self._reserve(workspace.id)
        try:
            return self._verify_in_sandbox(workspace, proposal)
        finally:
            self._release(workspace.id)

    def get(self, verification_id: UUID) -> ProposalVerification:
        verification = self._verification_repository.get(verification_id)
        if verification is None:
            raise ProposalVerificationNotFoundError(verification_id)
        return verification

    def list_for_proposal(self, proposal_id: UUID) -> ProposalVerificationCollection:
        self._require_proposal(proposal_id)
        items = tuple(self._verification_repository.list_for_proposal(proposal_id))
        return ProposalVerificationCollection(items=items, total=len(items))

    def _verify_in_sandbox(
        self, workspace: Workspace, proposal: ChangeProposal
    ) -> ProposalVerification:
        created_at = ensure_utc_timestamp(self._clock())
        started = self._monotonic()
        sandbox = self._sandbox_factory.create(workspace.root_path)
        try:
            file_results = tuple(
                self._materialize(sandbox.path, change) for change in proposal.file_changes
            )
            guard = self._run_guard(sandbox) if self._all_applied(file_results) else None
        finally:
            cleanup_completed = sandbox.cleanup()

        if guard is None:
            outcome = ProposalVerificationOutcome.MATERIALIZATION_FAILED
        elif guard.status is GuardRunStatus.PASSED:
            outcome = ProposalVerificationOutcome.SANDBOX_VERIFIED
        else:
            outcome = ProposalVerificationOutcome.GUARD_FAILED
        finished_at = ensure_utc_timestamp(self._clock())
        verification = ProposalVerification(
            id=self._id_factory(),
            proposal_id=proposal.id,
            run_id=proposal.run_id,
            task_id=proposal.task_id,
            workspace_id=proposal.workspace_id,
            context_pack_id=proposal.context_pack_id,
            status=(
                ProposalVerificationStatus.PASSED
                if outcome is ProposalVerificationOutcome.SANDBOX_VERIFIED
                else ProposalVerificationStatus.FAILED
            ),
            outcome=outcome,
            sandbox=VerificationSandboxMetadata(
                kind=VerificationSandboxKind.GIT_WORKTREE,
                commit_id=sandbox.commit_id,
                cleanup_completed=cleanup_completed,
            ),
            guard=guard,
            file_results=file_results,
            safe_diff=self._safe_diff(proposal, file_results),
            created_at=created_at,
            finished_at=max(created_at, finished_at),
            duration_ms=max(0, round((self._monotonic() - started) * 1000)),
        )
        self._verification_repository.save(verification)
        return verification

    def _materialize(
        self, sandbox_root: Path, change: ChangeProposalFileChange
    ) -> FileVerificationResult:
        target = self._safe_target(sandbox_root, change.path)
        if target is None:
            return self._file_result(change, None, FileVerificationReason.UNSAFE_PATH)

        if change.change_type is ChangeProposalChangeType.CREATE:
            if target.exists():
                observed = self._file_digest(target) if target.is_file() else None
                return self._file_result(
                    change, observed, FileVerificationReason.CREATE_TARGET_EXISTS
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((change.proposed_text or "").encode("utf-8"))
            return self._file_result(change, None, FileVerificationReason.APPLIED)

        if not target.exists():
            return self._file_result(change, None, FileVerificationReason.TARGET_MISSING)
        if not target.is_file():
            return self._file_result(change, None, FileVerificationReason.TARGET_NOT_A_FILE)
        observed = self._file_digest(target)
        if observed != change.before_digest:
            return self._file_result(
                change, observed, FileVerificationReason.BEFORE_CONTENT_MISMATCH
            )

        if change.change_type is ChangeProposalChangeType.DELETE:
            target.unlink()
        else:
            target.write_bytes((change.proposed_text or "").encode("utf-8"))
        return self._file_result(change, observed, FileVerificationReason.APPLIED)

    def _run_guard(self, sandbox: VerificationSandbox) -> VerificationGuardResult:
        execution = execute_guard_checks(
            str(sandbox.path),
            [GuardCheckKind.LINT, GuardCheckKind.TEST],
            configuration_loader=self._guard_configuration_loader,
            command_runner=self._guard_command_runner,
            clock=self._clock,
            monotonic=self._monotonic,
        )
        return VerificationGuardResult(
            status=execution.status,
            blocking=execution.summary.is_blocking,
            summary=execution.summary,
            checks=[self._compact_check(check) for check in execution.checks],
        )

    @staticmethod
    def _compact_check(check: GuardCheckResult) -> VerificationGuardCheck:
        combined = "\n".join(part for part in (check.stdout.strip(), check.stderr.strip()) if part)
        excerpt = combined[-VERIFICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS:]
        return VerificationGuardCheck(
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
    def _safe_target(sandbox_root: Path, relative_path: str) -> Path | None:
        """Refuse symlinked components so writes can never escape the sandbox."""
        target = sandbox_root / relative_path
        current = sandbox_root
        for part in Path(relative_path).parts[:-1]:
            current = current / part
            if current.is_symlink() or (current.exists() and not current.is_dir()):
                return None
        if target.is_symlink():
            return None
        return target

    @staticmethod
    def _file_result(
        change: ChangeProposalFileChange,
        sandbox_digest: str | None,
        reason: FileVerificationReason,
    ) -> FileVerificationResult:
        return FileVerificationResult(
            path=change.path,
            change_type=change.change_type,
            before_digest=change.before_digest,
            after_digest=change.after_digest,
            sandbox_digest=sandbox_digest,
            applied_in_sandbox=reason is FileVerificationReason.APPLIED,
            reason=reason,
        )

    @staticmethod
    def _all_applied(file_results: tuple[FileVerificationResult, ...]) -> bool:
        return all(result.applied_in_sandbox for result in file_results)

    @staticmethod
    def _safe_diff(
        proposal: ChangeProposal, file_results: tuple[FileVerificationResult, ...]
    ) -> SafeDiffMetadata:
        applied = sum(result.applied_in_sandbox for result in file_results)
        return SafeDiffMetadata(
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
            unapplied_count=len(file_results) - applied,
            proposed_bytes_total=sum(
                change.original_text_bytes for change in proposal.file_changes
            ),
        )

    @staticmethod
    def _file_digest(target: Path) -> str:
        return f"sha256:{sha256(target.read_bytes()).hexdigest()}"

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

    def _reserve(self, workspace_id: UUID) -> None:
        with self._active_lock:
            if workspace_id in self._active_workspaces:
                raise ProposalVerificationInProgressError(workspace_id)
            self._active_workspaces.add(workspace_id)

    def _release(self, workspace_id: UUID) -> None:
        with self._active_lock:
            self._active_workspaces.discard(workspace_id)
