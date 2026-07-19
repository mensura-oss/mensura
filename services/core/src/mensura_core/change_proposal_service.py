from collections.abc import Callable, Sequence
from datetime import datetime
from hashlib import sha256
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from mensura_core.change_proposal_models import (
    CHANGE_PROPOSAL_MAX_SOURCE_TEXT_BYTES,
    CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_PER_FILE,
    CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_TOTAL,
    ChangeProposal,
    ChangeProposalCollection,
    ChangeProposalFileChange,
    ChangeProposalStatus,
    CreateChangeProposalResponse,
)
from mensura_core.change_proposal_repositories import ChangeProposalRepository
from mensura_core.context_pack_models import ContextPackFileEntry, ContextPackManifest
from mensura_core.context_pack_repositories import ContextPackRepository
from mensura_core.exceptions import (
    ChangeProposalContentTooLargeError,
    ChangeProposalInvalidStateError,
    ChangeProposalNotFoundError,
    ChangeProposalOutputInvalidError,
    ChangeProposalRunNotEligibleError,
    ResourceNotFoundError,
)
from mensura_core.models import (
    ChangeProposalChangeType,
    ChangeProposalDraftFileChange,
    Run,
    RunStatus,
    Task,
    ensure_utc_timestamp,
)
from mensura_core.repositories import CoreRepository
from mensura_core.service import utc_now
from mensura_core.vault_models import VaultFileKind

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


class ChangeProposalService:
    """Materializes and reviews bounded artifacts without repository capabilities."""

    def __init__(
        self,
        core_repository: CoreRepository,
        context_pack_repository: ContextPackRepository,
        proposal_repository: ChangeProposalRepository,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
    ) -> None:
        self._core_repository = core_repository
        self._context_pack_repository = context_pack_repository
        self._proposal_repository = proposal_repository
        self._id_factory = id_factory
        self._clock = clock

    def create(self, run_id: UUID) -> CreateChangeProposalResponse:
        existing = self._proposal_repository.get_for_run(run_id)
        if existing is not None:
            return CreateChangeProposalResponse(proposal=existing, created=False)

        run = self._require_run(run_id)
        if (
            run.status is not RunStatus.SUCCEEDED
            or run.execution is None
            or run.execution.result is None
        ):
            raise ChangeProposalRunNotEligibleError(run.id, run.status)
        task = self._require_task(run.task_id)
        manifest = self._require_consistent_manifest(run, task)
        draft = run.execution.result.proposal_draft
        source_text_bytes = sum(
            len(change.proposed_text.encode("utf-8"))
            for change in draft.file_changes
            if change.proposed_text is not None
        )
        if source_text_bytes > CHANGE_PROPOSAL_MAX_SOURCE_TEXT_BYTES:
            raise ChangeProposalContentTooLargeError(
                run.id,
                source_text_bytes,
                CHANGE_PROPOSAL_MAX_SOURCE_TEXT_BYTES,
            )

        changes = self._materialize_changes(run, manifest, draft.file_changes)
        created_at = ensure_utc_timestamp(self._clock())
        proposal = ChangeProposal(
            id=self._id_factory(),
            run_id=run.id,
            task_id=task.id,
            workspace_id=task.workspace_id,
            context_pack_id=manifest.id,
            provider_id=run.execution.provider.provider_id,
            prompt_version=run.execution.provider.prompt_version,
            status=ChangeProposalStatus.PROPOSED,
            created_at=created_at,
            summary=draft.summary,
            rationale=draft.rationale,
            file_changes=changes,
        )
        created = self._proposal_repository.save_if_absent_for_run(proposal)
        if not created:
            stored = self._proposal_repository.get_for_run(run.id)
            if stored is None:
                raise RuntimeError("Proposal storage lost an idempotent source-run binding.")
            proposal = stored
        return CreateChangeProposalResponse(proposal=proposal, created=created)

    def get(self, proposal_id: UUID) -> ChangeProposal:
        proposal = self._proposal_repository.get(proposal_id)
        if proposal is None:
            raise ChangeProposalNotFoundError(proposal_id)
        return proposal

    def list_for_workspace(self, workspace_id: UUID) -> ChangeProposalCollection:
        if self._core_repository.get_workspace(workspace_id) is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        items = tuple(self._proposal_repository.list_for_workspace(workspace_id))
        return ChangeProposalCollection(items=items, total=len(items))

    def approve(self, proposal_id: UUID) -> ChangeProposal:
        return self._review(proposal_id, ChangeProposalStatus.APPROVED)

    def reject(self, proposal_id: UUID) -> ChangeProposal:
        return self._review(proposal_id, ChangeProposalStatus.REJECTED)

    def _review(self, proposal_id: UUID, status: ChangeProposalStatus) -> ChangeProposal:
        proposal = self.get(proposal_id)
        if proposal.status is not ChangeProposalStatus.PROPOSED:
            raise ChangeProposalInvalidStateError(proposal.id, proposal.status)
        reviewed_at = max(proposal.created_at, ensure_utc_timestamp(self._clock()))
        reviewed = ChangeProposal.model_validate(
            {
                **proposal.model_dump(by_alias=False),
                "status": status,
                "reviewed_at": reviewed_at,
            }
        )
        if not self._proposal_repository.replace_if_status(
            reviewed,
            ChangeProposalStatus.PROPOSED,
        ):
            current = self.get(proposal.id)
            raise ChangeProposalInvalidStateError(current.id, current.status)
        return reviewed

    def _materialize_changes(
        self,
        run: Run,
        manifest: ContextPackManifest,
        drafts: Sequence[ChangeProposalDraftFileChange],
    ) -> tuple[ChangeProposalFileChange, ...]:
        entries = {entry.path: entry for entry in manifest.files}
        seen_paths: set[str] = set()
        stored_budget = CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_TOTAL
        changes: list[ChangeProposalFileChange] = []
        for draft in sorted(drafts, key=lambda item: (item.path, item.change_type.value)):
            path = self._validate_path(run.id, draft.path)
            if path in seen_paths:
                raise ChangeProposalOutputInvalidError(
                    run.id,
                    f"Path '{path}' appears more than once.",
                )
            seen_paths.add(path)
            entry = entries.get(path)
            self._validate_change(run.id, draft, entry)
            original = draft.proposed_text
            original_bytes = original.encode("utf-8") if original is not None else b""
            per_file_budget = min(
                stored_budget,
                CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_PER_FILE,
            )
            stored_text = (
                self._truncate_utf8(original_bytes, per_file_budget)
                if original is not None
                else None
            )
            stored_bytes = len(stored_text.encode("utf-8")) if stored_text is not None else 0
            stored_budget -= stored_bytes
            changes.append(
                ChangeProposalFileChange(
                    path=path,
                    change_type=draft.change_type,
                    language=entry.language if entry is not None else draft.language,
                    before_digest=(entry.content_digest if entry is not None else None),
                    after_digest=(
                        self._digest(original_bytes)
                        if draft.change_type is not ChangeProposalChangeType.DELETE
                        else None
                    ),
                    proposed_text=stored_text,
                    proposed_text_bytes=stored_bytes,
                    original_text_bytes=len(original_bytes),
                    truncated=stored_bytes < len(original_bytes),
                )
            )
        return tuple(changes)

    @staticmethod
    def _validate_path(run_id: UUID, path: str) -> str:
        parts = path.split("/")
        if (
            "\\" in path
            or "\x00" in path
            or path.startswith("/")
            or any(part in {"", ".", ".."} for part in parts)
            or PurePosixPath(path).as_posix() != path
        ):
            raise ChangeProposalOutputInvalidError(
                run_id,
                f"Path '{path}' is not a normalized relative repository path.",
            )
        return path

    @staticmethod
    def _validate_change(
        run_id: UUID,
        draft: ChangeProposalDraftFileChange,
        entry: ContextPackFileEntry | None,
    ) -> None:
        if draft.change_type is ChangeProposalChangeType.CREATE:
            if entry is not None:
                raise ChangeProposalOutputInvalidError(
                    run_id,
                    f"Create path '{draft.path}' already exists in the immutable context.",
                )
            if draft.proposed_text is None:
                raise ChangeProposalOutputInvalidError(
                    run_id,
                    f"Create path '{draft.path}' has no proposed text.",
                )
            return
        if entry is None:
            raise ChangeProposalOutputInvalidError(
                run_id,
                f"{draft.change_type.value.title()} path '{draft.path}' is absent from the "
                "immutable context.",
            )
        if draft.change_type is ChangeProposalChangeType.DELETE:
            if draft.proposed_text is not None:
                raise ChangeProposalOutputInvalidError(
                    run_id,
                    f"Delete path '{draft.path}' must not include proposed text.",
                )
            return
        if draft.proposed_text is None:
            raise ChangeProposalOutputInvalidError(
                run_id,
                f"Modify path '{draft.path}' has no proposed text.",
            )
        if entry.kind is VaultFileKind.BINARY:
            raise ChangeProposalOutputInvalidError(
                run_id,
                f"Binary path '{draft.path}' cannot include a proposed text body.",
            )

    def _require_consistent_manifest(self, run: Run, task: Task) -> ContextPackManifest:
        manifest = self._context_pack_repository.get(task.workspace_id, run.context_pack_id)
        if manifest is None:
            raise ChangeProposalRunNotEligibleError(
                run.id,
                run.status,
                "Its bound immutable context pack is no longer retrievable.",
            )
        reference = run.context_pack
        summary = manifest.summary
        consistent = (
            task.workspace_id == reference.workspace_id == manifest.workspace_id
            and run.context_pack_id == reference.id == manifest.id
            and reference.inventory_id == manifest.inventory_id
            and reference.schema_version == manifest.schema_version
            and reference.file_count == summary.file_count
            and reference.total_file_bytes == summary.total_file_bytes
            and reference.total_preview_bytes == summary.total_preview_bytes
        )
        if not consistent:
            raise ChangeProposalOutputInvalidError(
                run.id,
                "Source task, run, and immutable context lineage are inconsistent.",
            )
        return manifest

    def _require_run(self, run_id: UUID) -> Run:
        run = self._core_repository.get_run(run_id)
        if run is None:
            raise ResourceNotFoundError("Run", run_id)
        return run

    def _require_task(self, task_id: UUID) -> Task:
        task = self._core_repository.get_task(task_id)
        if task is None:
            raise ResourceNotFoundError("Task", task_id)
        return task

    @staticmethod
    def _truncate_utf8(raw: bytes, maximum_bytes: int) -> str:
        return raw[:maximum_bytes].decode("utf-8", errors="ignore")

    @staticmethod
    def _digest(raw: bytes) -> str:
        return f"sha256:{sha256(raw).hexdigest()}"
