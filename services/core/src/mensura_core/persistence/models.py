from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.types import Uuid

from mensura_core.application_models import (
    ApplicationArtifact,
    ApplicationGuardResult,
    ApplicationSummary,
    ApplicationTargetMetadata,
    ApplicationUndoMetadata,
    AppliedFileResult,
)
from mensura_core.backup_models import BackupArtifact
from mensura_core.change_proposal_models import (
    ChangeProposal,
    ChangeProposalFileChange,
)
from mensura_core.context_pack_models import (
    ContextPackFileEntry,
    ContextPackFileSummary,
    ContextPackLimits,
    ContextPackManifest,
)
from mensura_core.guard_models import (
    GuardCheckResult,
    GuardRunResponse,
    GuardSummary,
)
from mensura_core.job_models import Job, JobPayload
from mensura_core.models import (
    Run,
    RunContextPackReference,
    RunExecution,
    Task,
    Workspace,
)
from mensura_core.undo_models import (
    UndoArtifact,
    UndoFileOutcome,
    UndoGuardResult,
)
from mensura_core.vault_models import (
    VaultFileInventoryItem,
    VaultInventorySnapshot,
    VaultInventorySummary,
)
from mensura_core.vault_repositories import VaultInventoryRecord
from mensura_core.verification_models import (
    FileVerificationResult,
    ProposalVerification,
    SafeDiffMetadata,
    VerificationGuardResult,
    VerificationSandboxMetadata,
)


class Base(DeclarativeBase):
    pass


def _ensure_tz(dt: datetime) -> datetime:
    """Normalize a datetime to UTC-aware for Pydantic domain models."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


_checks_adapter = TypeAdapter(list[GuardCheckResult])
_file_changes_adapter = TypeAdapter(tuple[ChangeProposalFileChange, ...])
_verification_file_results_adapter = TypeAdapter(tuple[FileVerificationResult, ...])
_applied_file_results_adapter = TypeAdapter(tuple[AppliedFileResult, ...])
_context_pack_files_adapter = TypeAdapter(tuple[ContextPackFileEntry, ...])


_workspace_adapter = TypeAdapter(Workspace)
_task_adapter = TypeAdapter(Task)
_run_adapter = TypeAdapter(Run)
_context_pack_reference_adapter = TypeAdapter(RunContextPackReference)
_run_execution_adapter = TypeAdapter(RunExecution)
_guard_run_response_adapter = TypeAdapter(GuardRunResponse)
_guard_summary_adapter = TypeAdapter(GuardSummary)
_vault_inventory_snapshot_adapter = TypeAdapter(VaultInventorySnapshot)
_vault_inventory_summary_adapter = TypeAdapter(VaultInventorySummary)
_vault_file_item_adapter = TypeAdapter(VaultFileInventoryItem)
_context_pack_limits_adapter = TypeAdapter(ContextPackLimits)
_context_pack_summary_adapter = TypeAdapter(ContextPackFileSummary)
_context_pack_manifest_adapter = TypeAdapter(ContextPackManifest)
_change_proposal_adapter = TypeAdapter(ChangeProposal)
_sandbox_metadata_adapter = TypeAdapter(VerificationSandboxMetadata)
_verification_guard_result_adapter = TypeAdapter(VerificationGuardResult)
_safe_diff_adapter = TypeAdapter(SafeDiffMetadata)
_proposal_verification_adapter = TypeAdapter(ProposalVerification)
_target_metadata_adapter = TypeAdapter(ApplicationTargetMetadata)
_application_guard_result_adapter = TypeAdapter(ApplicationGuardResult)
_application_summary_adapter = TypeAdapter(ApplicationSummary)
_undo_metadata_adapter = TypeAdapter(ApplicationUndoMetadata)
_undo_file_outcomes_adapter = TypeAdapter(tuple[UndoFileOutcome, ...])
_undo_guard_result_adapter = TypeAdapter(UndoGuardResult)
_undo_artifact_adapter = TypeAdapter(UndoArtifact)
_application_artifact_adapter = TypeAdapter(ApplicationArtifact)
_job_payload_adapter = TypeAdapter(JobPayload)


class WorkspaceRow(Base):
    __tablename__ = "workspaces"

    id = Column(Uuid, primary_key=True)
    name = Column(String(120), nullable=False)
    root_path = Column(String(4096), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    tasks = relationship("TaskRow", back_populates="workspace", cascade="all, delete-orphan")
    runs = relationship("RunRow", back_populates="workspace", cascade="all, delete-orphan")
    guard_runs = relationship(
        "GuardRunRow", back_populates="workspace", cascade="all, delete-orphan"
    )
    vault_snapshots = relationship(
        "VaultInventorySnapshotRow", back_populates="workspace", cascade="all, delete-orphan"
    )
    context_packs = relationship(
        "ContextPackRow", back_populates="workspace", cascade="all, delete-orphan"
    )
    change_proposals = relationship(
        "ChangeProposalRow", back_populates="workspace", cascade="all, delete-orphan"
    )
    verifications = relationship(
        "ProposalVerificationRow", back_populates="workspace", cascade="all, delete-orphan"
    )
    applications = relationship(
        "ApplicationRow", back_populates="workspace", cascade="all, delete-orphan"
    )

    def to_domain(self) -> Workspace:
        return Workspace(
            id=self.id,
            name=self.name,
            root_path=self.root_path,
            created_at=_ensure_tz(self.created_at),
            updated_at=_ensure_tz(self.updated_at),
        )

    @classmethod
    def from_domain(cls, workspace: Workspace) -> "WorkspaceRow":
        return cls(
            id=workspace.id,
            name=workspace.name,
            root_path=workspace.root_path,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )


class TaskRow(Base):
    __tablename__ = "tasks"

    id = Column(Uuid, primary_key=True)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String(240), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False)
    assigned_role = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    workspace = relationship("WorkspaceRow", back_populates="tasks")
    runs = relationship("RunRow", back_populates="task", cascade="all, delete-orphan")

    def to_domain(self) -> Task:
        return Task(
            id=self.id,
            workspace_id=self.workspace_id,
            title=self.title,
            description=self.description,
            status=self.status,
            assigned_role=self.assigned_role,
            created_at=_ensure_tz(self.created_at),
            updated_at=_ensure_tz(self.updated_at),
        )

    @classmethod
    def from_domain(cls, task: Task) -> "TaskRow":
        return cls(
            id=task.id,
            workspace_id=task.workspace_id,
            title=task.title,
            description=task.description,
            status=task.status,
            assigned_role=task.assigned_role,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class RunRow(Base):
    __tablename__ = "runs"

    id = Column(Uuid, primary_key=True)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False, index=True)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    context_pack_id = Column(String(72), nullable=False)
    _context_pack = Column("context_pack", JSON, nullable=False)
    status = Column(String(20), nullable=False)
    _execution = Column("execution", JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    workspace = relationship("WorkspaceRow", back_populates="runs")
    task = relationship("TaskRow", back_populates="runs")

    def to_domain(self) -> Run:
        return Run(
            id=self.id,
            task_id=self.task_id,
            context_pack_id=self.context_pack_id,
            context_pack=_context_pack_reference_adapter.validate_python(self._context_pack),
            status=self.status,
            execution=_run_execution_adapter.validate_python(self._execution)
            if self._execution is not None
            else None,
            started_at=_ensure_tz(self.started_at) if self.started_at is not None else None,
            finished_at=_ensure_tz(self.finished_at) if self.finished_at is not None else None,
            created_at=_ensure_tz(self.created_at),
            updated_at=_ensure_tz(self.updated_at),
        )

    @classmethod
    def from_domain(cls, run: Run) -> "RunRow":
        return cls(
            id=run.id,
            task_id=run.task_id,
            workspace_id=run.context_pack.workspace_id,
            context_pack_id=run.context_pack_id,
            _context_pack=run.context_pack.model_dump(by_alias=False, mode="json"),
            status=run.status,
            _execution=run.execution.model_dump(by_alias=False, mode="json")
            if run.execution is not None
            else None,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )


class GuardRunRow(Base):
    __tablename__ = "guard_runs"

    id = Column(Uuid, primary_key=True)
    workspace_id = Column(
        Uuid, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True
    )
    status = Column(String(20), nullable=False)
    blocking = Column(Boolean, nullable=False)
    _summary = Column("summary", JSON, nullable=False)
    _checks = Column("checks", JSON, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)

    workspace = relationship("WorkspaceRow", back_populates="guard_runs")

    def to_domain(self) -> GuardRunResponse:
        return GuardRunResponse(
            id=self.id,
            workspace_id=self.workspace_id,
            status=self.status,
            blocking=self.blocking,
            summary=_guard_summary_adapter.validate_python(self._summary),
            checks=_checks_adapter.validate_python(self._checks),
            started_at=_ensure_tz(self.started_at),
            completed_at=_ensure_tz(self.completed_at),
            duration_ms=self.duration_ms,
        )

    @classmethod
    def from_domain(cls, guard_run: GuardRunResponse) -> "GuardRunRow":
        return cls(
            id=guard_run.id,
            workspace_id=guard_run.workspace_id,
            status=guard_run.status,
            blocking=guard_run.blocking,
            _summary=guard_run.summary.model_dump(by_alias=False, mode="json"),
            _checks=[check.model_dump(by_alias=False, mode="json") for check in guard_run.checks],
            started_at=guard_run.started_at,
            completed_at=guard_run.completed_at,
            duration_ms=guard_run.duration_ms,
        )


class VaultInventorySnapshotRow(Base):
    __tablename__ = "vault_inventory_snapshots"

    id = Column(Uuid, primary_key=True)
    workspace_id = Column(
        Uuid, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True
    )
    status = Column(String(20), nullable=False)
    built_at = Column(DateTime(timezone=True), nullable=False)
    _summary = Column("summary", JSON, nullable=False)
    item_count = Column(Integer, nullable=False)

    workspace = relationship("WorkspaceRow", back_populates="vault_snapshots")
    items = relationship(
        "VaultInventoryItemRow", back_populates="snapshot", cascade="all, delete-orphan"
    )

    def to_snapshot(self) -> VaultInventorySnapshot:
        return VaultInventorySnapshot(
            id=self.id,
            workspace_id=self.workspace_id,
            status=self.status,
            built_at=_ensure_tz(self.built_at),
            summary=_vault_inventory_summary_adapter.validate_python(self._summary),
        )

    @classmethod
    def from_record(
        cls, record: VaultInventoryRecord
    ) -> tuple["VaultInventorySnapshotRow", list["VaultInventoryItemRow"]]:
        snapshot = cls(
            id=record.snapshot.id,
            workspace_id=record.snapshot.workspace_id,
            status=record.snapshot.status,
            built_at=record.snapshot.built_at,
            _summary=record.snapshot.summary.model_dump(by_alias=False, mode="json"),
            item_count=len(record.items),
        )
        items = [
            VaultInventoryItemRow(
                inventory_id=record.snapshot.id,
                path=item.path,
                name=item.name,
                extension=item.extension,
                language=item.language,
                kind=item.kind,
                size_bytes=item.size_bytes,
            )
            for item in record.items
        ]
        return snapshot, items


class VaultInventoryItemRow(Base):
    __tablename__ = "vault_inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_id = Column(
        Uuid, ForeignKey("vault_inventory_snapshots.id"), nullable=False, index=True
    )
    path = Column(String(4096), nullable=False)
    name = Column(String(1024), nullable=False)
    extension = Column(String(80), nullable=True)
    language = Column(String(80), nullable=True)
    kind = Column(String(10), nullable=False)
    size_bytes = Column(Integer, nullable=False)

    snapshot = relationship("VaultInventorySnapshotRow", back_populates="items")

    def to_domain(self) -> VaultFileInventoryItem:
        return VaultFileInventoryItem(
            path=self.path,
            name=self.name,
            extension=self.extension,
            language=self.language,
            kind=self.kind,
            size_bytes=self.size_bytes,
        )


class ContextPackRow(Base):
    __tablename__ = "context_packs"

    id = Column(String(72), primary_key=True)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    inventory_id = Column(Uuid, nullable=False)
    schema_version = Column(String(10), nullable=False)
    _limits = Column("limits", JSON, nullable=False)
    _summary = Column("summary", JSON, nullable=False)
    _files = Column("files", JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("workspace_id", "id", name="uq_context_pack_workspace"),)

    workspace = relationship("WorkspaceRow", back_populates="context_packs")

    def to_domain(self) -> ContextPackManifest:
        return ContextPackManifest(
            id=self.id,
            digest=self.id,
            workspace_id=self.workspace_id,
            inventory_id=self.inventory_id,
            schema_version=self.schema_version,
            limits=_context_pack_limits_adapter.validate_python(self._limits),
            summary=_context_pack_summary_adapter.validate_python(self._summary),
            files=_context_pack_files_adapter.validate_python(self._files),
        )

    @classmethod
    def from_domain(cls, manifest: ContextPackManifest) -> "ContextPackRow":
        return cls(
            id=manifest.id,
            workspace_id=manifest.workspace_id,
            inventory_id=manifest.inventory_id,
            schema_version=manifest.schema_version,
            _limits=manifest.limits.model_dump(by_alias=False, mode="json"),
            _summary=manifest.summary.model_dump(by_alias=False, mode="json"),
            _files=[f.model_dump(by_alias=False, mode="json") for f in manifest.files],
            created_at=datetime.now().astimezone(),
        )


class ChangeProposalRow(Base):
    __tablename__ = "change_proposals"

    id = Column(Uuid, primary_key=True)
    schema_version = Column(String(10), nullable=False)
    run_id = Column(Uuid, ForeignKey("runs.id"), nullable=False, unique=True, index=True)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    context_pack_id = Column(String(72), nullable=False)
    provider_id = Column(String(40), nullable=False)
    prompt_version = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    summary = Column(String(1000), nullable=False)
    rationale = Column(String(2000), nullable=False)
    _file_changes = Column("file_changes", JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("WorkspaceRow", back_populates="change_proposals")

    def to_domain(self) -> ChangeProposal:
        return ChangeProposal(
            id=self.id,
            schema_version=self.schema_version,
            run_id=self.run_id,
            task_id=self.task_id,
            workspace_id=self.workspace_id,
            context_pack_id=self.context_pack_id,
            provider_id=self.provider_id,
            prompt_version=self.prompt_version,
            status=self.status,
            created_at=_ensure_tz(self.created_at),
            reviewed_at=_ensure_tz(self.reviewed_at) if self.reviewed_at is not None else None,
            summary=self.summary,
            rationale=self.rationale,
            file_changes=_file_changes_adapter.validate_python(self._file_changes),
        )

    @classmethod
    def from_domain(cls, proposal: ChangeProposal) -> "ChangeProposalRow":
        return cls(
            id=proposal.id,
            schema_version=proposal.schema_version,
            run_id=proposal.run_id,
            task_id=proposal.task_id,
            workspace_id=proposal.workspace_id,
            context_pack_id=proposal.context_pack_id,
            provider_id=proposal.provider_id,
            prompt_version=proposal.prompt_version,
            status=proposal.status,
            summary=proposal.summary,
            rationale=proposal.rationale,
            _file_changes=[
                fc.model_dump(by_alias=False, mode="json") for fc in proposal.file_changes
            ],
            created_at=proposal.created_at,
            reviewed_at=proposal.reviewed_at,
        )


class ProposalVerificationRow(Base):
    __tablename__ = "proposal_verifications"

    id = Column(Uuid, primary_key=True)
    proposal_id = Column(Uuid, ForeignKey("change_proposals.id"), nullable=False, index=True)
    run_id = Column(Uuid, ForeignKey("runs.id"), nullable=False)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    context_pack_id = Column(String(72), nullable=False)
    status = Column(String(20), nullable=False)
    outcome = Column(String(40), nullable=False)
    _sandbox = Column("sandbox", JSON, nullable=False)
    _guard = Column("guard", JSON, nullable=True)
    _file_results = Column("file_results", JSON, nullable=False)
    _safe_diff = Column("safe_diff", JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)

    workspace = relationship("WorkspaceRow", back_populates="verifications")

    def to_domain(self) -> ProposalVerification:
        return ProposalVerification(
            id=self.id,
            proposal_id=self.proposal_id,
            run_id=self.run_id,
            task_id=self.task_id,
            workspace_id=self.workspace_id,
            context_pack_id=self.context_pack_id,
            status=self.status,
            outcome=self.outcome,
            sandbox=_sandbox_metadata_adapter.validate_python(self._sandbox),
            guard=_verification_guard_result_adapter.validate_python(self._guard)
            if self._guard is not None
            else None,
            file_results=_verification_file_results_adapter.validate_python(self._file_results),
            safe_diff=_safe_diff_adapter.validate_python(self._safe_diff),
            created_at=_ensure_tz(self.created_at),
            finished_at=_ensure_tz(self.finished_at),
            duration_ms=self.duration_ms,
        )

    @classmethod
    def from_domain(cls, verification: ProposalVerification) -> "ProposalVerificationRow":
        return cls(
            id=verification.id,
            proposal_id=verification.proposal_id,
            run_id=verification.run_id,
            task_id=verification.task_id,
            workspace_id=verification.workspace_id,
            context_pack_id=verification.context_pack_id,
            status=verification.status,
            outcome=verification.outcome,
            _sandbox=verification.sandbox.model_dump(by_alias=False, mode="json"),
            _guard=verification.guard.model_dump(by_alias=False, mode="json")
            if verification.guard is not None
            else None,
            _file_results=[
                fr.model_dump(by_alias=False, mode="json") for fr in verification.file_results
            ],
            _safe_diff=verification.safe_diff.model_dump(by_alias=False, mode="json"),
            created_at=verification.created_at,
            finished_at=verification.finished_at,
            duration_ms=verification.duration_ms,
        )


class ApplicationRow(Base):
    __tablename__ = "applications"

    id = Column(Uuid, primary_key=True)
    proposal_id = Column(
        Uuid, ForeignKey("change_proposals.id"), nullable=False, unique=True, index=True
    )
    verification_id = Column(Uuid, ForeignKey("proposal_verifications.id"), nullable=False)
    run_id = Column(Uuid, ForeignKey("runs.id"), nullable=False)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    context_pack_id = Column(String(72), nullable=False)
    status = Column(String(40), nullable=False)
    _target = Column("target", JSON, nullable=False)
    _guard = Column("guard", JSON, nullable=True)
    guard_unavailable_reason = Column(Text, nullable=True)
    _file_results = Column("file_results", JSON, nullable=False)
    _summary = Column("summary", JSON, nullable=False)
    _undo = Column("undo", JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)

    workspace = relationship("WorkspaceRow", back_populates="applications")

    def to_domain(self) -> ApplicationArtifact:
        return ApplicationArtifact(
            id=self.id,
            proposal_id=self.proposal_id,
            verification_id=self.verification_id,
            run_id=self.run_id,
            task_id=self.task_id,
            workspace_id=self.workspace_id,
            context_pack_id=self.context_pack_id,
            status=self.status,
            target=_target_metadata_adapter.validate_python(self._target),
            guard=_application_guard_result_adapter.validate_python(self._guard)
            if self._guard is not None
            else None,
            guard_unavailable_reason=self.guard_unavailable_reason,
            file_results=_applied_file_results_adapter.validate_python(self._file_results),
            summary=_application_summary_adapter.validate_python(self._summary),
            undo=_undo_metadata_adapter.validate_python(self._undo),
            created_at=_ensure_tz(self.created_at),
            finished_at=_ensure_tz(self.finished_at),
            duration_ms=self.duration_ms,
        )

    @classmethod
    def from_domain(cls, application: ApplicationArtifact) -> "ApplicationRow":
        return cls(
            id=application.id,
            proposal_id=application.proposal_id,
            verification_id=application.verification_id,
            run_id=application.run_id,
            task_id=application.task_id,
            workspace_id=application.workspace_id,
            context_pack_id=application.context_pack_id,
            status=application.status,
            _target=application.target.model_dump(by_alias=False, mode="json"),
            _guard=application.guard.model_dump(by_alias=False, mode="json")
            if application.guard is not None
            else None,
            guard_unavailable_reason=application.guard_unavailable_reason,
            _file_results=[
                fr.model_dump(by_alias=False, mode="json") for fr in application.file_results
            ],
            _summary=application.summary.model_dump(by_alias=False, mode="json"),
            _undo=application.undo.model_dump(by_alias=False, mode="json"),
            created_at=application.created_at,
            finished_at=application.finished_at,
            duration_ms=application.duration_ms,
        )


class UndoRow(Base):
    __tablename__ = "undos"

    id = Column(Uuid, primary_key=True)
    application_id = Column(
        Uuid,
        ForeignKey("applications.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    proposal_id = Column(Uuid, nullable=False)
    workspace_id = Column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False)
    _file_outcomes = Column("file_outcomes", JSON, nullable=False)
    _guard = Column("guard", JSON, nullable=True)
    guard_unavailable_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)

    workspace = relationship("WorkspaceRow")

    def to_domain(self) -> UndoArtifact:
        return UndoArtifact(
            id=self.id,
            application_id=self.application_id,
            proposal_id=self.proposal_id,
            workspace_id=self.workspace_id,
            status=self.status,
            file_outcomes=_undo_file_outcomes_adapter.validate_python(self._file_outcomes),
            guard=_undo_guard_result_adapter.validate_python(self._guard)
            if self._guard is not None
            else None,
            guard_unavailable_reason=self.guard_unavailable_reason,
            created_at=_ensure_tz(self.created_at),
            finished_at=_ensure_tz(self.finished_at),
            duration_ms=self.duration_ms,
        )

    @classmethod
    def from_domain(cls, undo: UndoArtifact) -> "UndoRow":
        return cls(
            id=undo.id,
            application_id=undo.application_id,
            proposal_id=undo.proposal_id,
            workspace_id=undo.workspace_id,
            status=undo.status,
            _file_outcomes=[
                fo.model_dump(by_alias=False, mode="json") for fo in undo.file_outcomes
            ],
            _guard=undo.guard.model_dump(by_alias=False, mode="json")
            if undo.guard is not None
            else None,
            guard_unavailable_reason=undo.guard_unavailable_reason,
            created_at=undo.created_at,
            finished_at=undo.finished_at,
            duration_ms=undo.duration_ms,
        )


class BackupRow(Base):
    __tablename__ = "backups"

    id = Column(Uuid, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    db_version = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=False)
    sha256_hex = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False, unique=True)
    status = Column(Text, nullable=False)
    label = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    def to_domain(self) -> "BackupArtifact":
        from mensura_core.backup_models import BackupArtifact

        return BackupArtifact(
            id=self.id,
            created_at=_ensure_tz(self.created_at),
            db_version=self.db_version,
            file_size_bytes=self.file_size_bytes,
            sha256_hex=self.sha256_hex,
            storage_path=self.storage_path,
            status=self.status,
            label=self.label,
            error_message=self.error_message,
        )

    @classmethod
    def from_domain(cls, backup: "BackupArtifact") -> "BackupRow":
        return cls(
            id=backup.id,
            created_at=backup.created_at,
            db_version=backup.db_version,
            file_size_bytes=backup.file_size_bytes,
            sha256_hex=backup.sha256_hex,
            storage_path=backup.storage_path,
            status=backup.status,
            label=backup.label,
            error_message=backup.error_message,
        )


class JobRow(Base):
    """Durable orchestration record. Loosely coupled: target_entity_id is polymorphic
    (proposal, application, or none) and workspace_id is a plain indexed column, not an FK."""

    __tablename__ = "jobs"

    id = Column(Uuid, primary_key=True)
    job_type = Column(String(40), nullable=False)
    target_entity_type = Column(String(20), nullable=False)
    target_entity_id = Column(Uuid, nullable=True)
    workspace_id = Column(Uuid, nullable=True, index=True)
    status = Column(String(20), nullable=False, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    _payload = Column("payload", JSON, nullable=False)
    result_entity_type = Column(String(40), nullable=True)
    result_entity_id = Column(Uuid, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> Job:
        return Job(
            id=self.id,
            job_type=self.job_type,
            target_entity_type=self.target_entity_type,
            target_entity_id=self.target_entity_id,
            workspace_id=self.workspace_id,
            status=self.status,
            attempt_count=self.attempt_count,
            payload=_job_payload_adapter.validate_python(self._payload),
            result_entity_type=self.result_entity_type,
            result_entity_id=self.result_entity_id,
            last_error=self.last_error,
            created_at=_ensure_tz(self.created_at),
            started_at=_ensure_tz(self.started_at) if self.started_at is not None else None,
            finished_at=_ensure_tz(self.finished_at) if self.finished_at is not None else None,
        )

    @classmethod
    def from_domain(cls, job: Job) -> "JobRow":
        return cls(
            id=job.id,
            job_type=job.job_type,
            target_entity_type=job.target_entity_type,
            target_entity_id=job.target_entity_id,
            workspace_id=job.workspace_id,
            status=job.status,
            attempt_count=job.attempt_count,
            _payload=job.payload.model_dump(by_alias=False, mode="json"),
            result_entity_type=job.result_entity_type,
            result_entity_id=job.result_entity_id,
            last_error=job.last_error,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
