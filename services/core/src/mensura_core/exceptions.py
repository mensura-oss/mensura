from uuid import UUID


class CoreError(Exception):
    """Expected service error that is safe to translate to an HTTP problem."""


class ResourceNotFoundError(CoreError):
    def __init__(self, resource: str, resource_id: UUID) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} '{resource_id}' was not found.")


class ResourceConflictError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class WorkspaceWriteInProgressError(CoreError):
    """A live working-tree write is already reserved for this workspace.

    Raised by any live-tree writer (application apply or undo) when another writer
    already holds the workspace's write reservation. The condition is a transient
    conflict, not a permanent failure: retry once the active operation completes.
    """

    def __init__(self, workspace_id: UUID, holder_kind: str) -> None:
        self.workspace_id = workspace_id
        self.holder_kind = holder_kind
        super().__init__(
            f"A live working-tree write for workspace '{workspace_id}' is already in "
            f"progress (held by '{holder_kind}'). This operation was refused; nothing was "
            "written. Retry once the active operation completes."
        )


class RepositoryInspectionError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class RepositoryPathNotFoundError(RepositoryInspectionError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Workspace root path '{path}' does not exist or is not a directory.")


class NotGitRepositoryError(RepositoryInspectionError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Workspace root path '{path}' is not a Git repository.")


class UnsupportedRepositoryStateError(RepositoryInspectionError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Repository at '{path}' cannot be inspected. {reason}")


class GuardError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class GuardConfigurationNotFoundError(GuardError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Guard configuration '{path}' was not found.")


class GuardConfigurationInvalidError(GuardError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Guard configuration '{path}' is invalid. {reason}")


class UnsupportedWorkspaceStateError(GuardError):
    pass


class GuardExecutionError(GuardError):
    def __init__(self, check_kind: str) -> None:
        super().__init__(f"Guard could not start the configured {check_kind} command.")


class GuardRunInProgressError(GuardError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(f"A Guard run for workspace '{workspace_id}' is already in progress.")


class GuardRunNotFoundError(GuardError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(f"No completed Guard run exists for workspace '{workspace_id}'.")


class VaultError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class VaultRootInvalidError(VaultError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Workspace root path '{path}' does not exist or is not a directory.")


class VaultInventoryNotBuiltError(VaultError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(f"No Vault inventory exists for workspace '{workspace_id}'.")


class VaultPathInvalidError(VaultError):
    def __init__(self) -> None:
        super().__init__("The requested file path must be a normalized relative repository path.")


class VaultFileExcludedError(VaultError):
    def __init__(self, path: str) -> None:
        super().__init__(f"File '{path}' is excluded from Vault inventory or preview access.")


class VaultBinaryPreviewError(VaultError):
    def __init__(self, path: str) -> None:
        super().__init__(f"File '{path}' is binary and cannot be previewed as text.")


class VaultFileNotFoundError(VaultError):
    def __init__(self, path: str) -> None:
        super().__init__(f"File '{path}' does not exist in the latest Vault inventory.")


class VaultIndexNotBuiltError(VaultError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(
            f"No Vault index exists for workspace '{workspace_id}'. Index the workspace first."
        )


class VaultMemoryItemNotFoundError(VaultError):
    def __init__(self, memory_item_id: UUID) -> None:
        super().__init__(f"Vault memory item '{memory_item_id}' was not found.")


class ContextPackError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ContextPackInvalidSelectionError(ContextPackError):
    pass


class ContextPackTooLargeError(ContextPackError):
    pass


class ContextPackFileChangedError(ContextPackError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"File '{path}' changed or became unavailable after the latest Vault inventory. "
            "Refresh the inventory before creating a context pack."
        )


class ContextPackNotFoundError(ContextPackError):
    def __init__(self, context_pack_id: str) -> None:
        super().__init__(f"Context pack '{context_pack_id}' was not found in this workspace.")


class ContextPackWorkspaceMismatchError(ContextPackError):
    def __init__(
        self,
        task_id: UUID,
        task_workspace_id: UUID,
        context_pack_id: str,
        context_pack_workspace_id: UUID,
    ) -> None:
        super().__init__(
            f"Task '{task_id}' belongs to workspace '{task_workspace_id}', but context pack "
            f"'{context_pack_id}' belongs to workspace '{context_pack_workspace_id}'."
        )


class RunExecutionError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class RunInvalidStateError(RunExecutionError):
    def __init__(self, run_id: UUID, status: str) -> None:
        super().__init__(f"Run '{run_id}' cannot execute from status '{status}'.")


class RunContextPackMissingError(RunExecutionError):
    def __init__(self, run_id: UUID, context_pack_id: str) -> None:
        super().__init__(
            f"Run '{run_id}' is bound to context pack '{context_pack_id}', but that immutable "
            "pack is no longer retrievable."
        )


class RunContextInconsistentError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(
            f"Run '{run_id}' has an inconsistent task or immutable context-pack binding."
        )


class UnsupportedProviderError(RunExecutionError):
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"Provider '{provider_id}' is not supported by this Core version.")


class ProviderConfigurationMissingError(RunExecutionError):
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"Provider '{provider_id}' is not configured on this device.")


class ProviderConfigurationUnavailableError(RunExecutionError):
    def __init__(self) -> None:
        super().__init__("Local provider configuration or credential storage is unavailable.")


class ProviderExecutionFailedError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"Provider execution failed for run '{run_id}'.")


class ProviderCredentialsInvalidError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"The configured provider credentials were rejected for run '{run_id}'.")


class ProviderUpstreamFailedError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"The upstream provider could not complete run '{run_id}'.")


class StructuredResultInvalidError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"Provider returned an invalid structured result for run '{run_id}'.")


class ChangeProposalError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ChangeProposalNotFoundError(ChangeProposalError):
    def __init__(self, proposal_id: UUID) -> None:
        super().__init__(f"Change proposal '{proposal_id}' was not found.")


class ChangeProposalRunNotEligibleError(ChangeProposalError):
    def __init__(self, run_id: UUID, status: str, reason: str | None = None) -> None:
        detail = f"Run '{run_id}' cannot produce a change proposal from status '{status}'."
        if reason is not None:
            detail = f"Run '{run_id}' cannot produce a change proposal. {reason}"
        super().__init__(detail)


class ChangeProposalOutputInvalidError(ChangeProposalError):
    def __init__(self, run_id: UUID, reason: str) -> None:
        super().__init__(f"Run '{run_id}' contains malformed change-proposal output. {reason}")


class ChangeProposalContentTooLargeError(ChangeProposalError):
    def __init__(self, run_id: UUID, actual_bytes: int, maximum_bytes: int) -> None:
        super().__init__(
            f"Run '{run_id}' proposes {actual_bytes} bytes of text; the maximum source size is "
            f"{maximum_bytes} bytes."
        )


class ChangeProposalInvalidStateError(ChangeProposalError):
    def __init__(self, proposal_id: UUID, status: str) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' cannot be reviewed from status '{status}'."
        )


class ProposalVerificationError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ProposalVerificationNotFoundError(ProposalVerificationError):
    def __init__(self, verification_id: UUID) -> None:
        super().__init__(f"Proposal verification '{verification_id}' was not found.")


class ProposalVerificationNotAllowedError(ProposalVerificationError):
    def __init__(self, proposal_id: UUID, status: str) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' cannot be verified from status '{status}'. "
            "Only approved proposals are eligible for isolated verification."
        )


class ProposalVerificationContentIncompleteError(ProposalVerificationError):
    def __init__(self, proposal_id: UUID) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' stores truncated file content and cannot be "
            "materialized faithfully in an isolated sandbox."
        )


class ProposalVerificationInProgressError(ProposalVerificationError):
    def __init__(self, workspace_id: UUID) -> None:
        super().__init__(
            f"A proposal verification for workspace '{workspace_id}' is already in progress."
        )


class VerificationSandboxError(ProposalVerificationError):
    """The temporary isolated sandbox could not be created."""


class ChangeApplicationError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ApplicationNotFoundError(ChangeApplicationError):
    def __init__(self, application_id: UUID) -> None:
        super().__init__(f"Application '{application_id}' was not found.")


class ApplicationProposalNotApprovedError(ChangeApplicationError):
    def __init__(self, proposal_id: UUID, status: str) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' cannot be applied from status '{status}'. "
            "Only approved proposals are eligible for application."
        )


class ApplicationContentIncompleteError(ChangeApplicationError):
    def __init__(self, proposal_id: UUID) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' stores truncated file content and cannot be "
            "applied faithfully to the live working tree."
        )


class ApplicationEmptyProposalError(ChangeApplicationError):
    def __init__(self, proposal_id: UUID) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' has no file changes to apply to the live "
            "working tree."
        )


class ApplicationVerificationNotFoundError(ChangeApplicationError):
    def __init__(self, verification_id: UUID) -> None:
        super().__init__(
            f"Proposal verification '{verification_id}' was not found for this application."
        )


class ApplicationVerificationMismatchError(ChangeApplicationError):
    def __init__(self, verification_id: UUID, proposal_id: UUID) -> None:
        super().__init__(
            f"Verification '{verification_id}' does not belong to change proposal "
            f"'{proposal_id}' and cannot authorize its application."
        )


class ApplicationVerificationNotPassedError(ChangeApplicationError):
    def __init__(self, verification_id: UUID, status: str) -> None:
        super().__init__(
            f"Verification '{verification_id}' is '{status}'. Only a passing verification "
            "can authorize applying a proposal to the live working tree."
        )


class ApplicationAlreadyExistsError(ChangeApplicationError):
    def __init__(self, proposal_id: UUID) -> None:
        super().__init__(
            f"Change proposal '{proposal_id}' has already been applied to the live working "
            "tree. Applications are single-use and are not re-applied automatically."
        )


class ApplicationLiveDriftError(ChangeApplicationError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Live file '{path}' has drifted from the verified materialization basis. "
            "Application was refused and nothing was written."
        )


class ApplicationUnsafePathError(ChangeApplicationError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Proposed path '{path}' resolves outside the workspace root or crosses a "
            "symlink. Application was refused and nothing was written."
        )


class ApplicationWriteError(ChangeApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "The live working tree could not be staged for application; nothing was written."
        )


class UndoError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UndoNotFoundError(UndoError):
    def __init__(self, undo_id: UUID) -> None:
        super().__init__(f"Undo artifact '{undo_id}' was not found.")


class UndoNotEligibleError(UndoError):
    def __init__(self, application_id: UUID, reason: str) -> None:
        super().__init__(
            f"Application '{application_id}' is not eligible for undo. {reason}"
        )


class UndoAlreadyExistsError(UndoError):
    def __init__(self, application_id: UUID) -> None:
        super().__init__(
            f"Application '{application_id}' has already been undone."
        )


class UndoMetadataIncompleteError(UndoError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Undo metadata for '{path}' is incomplete (truncated prior content). "
            "This file requires external recovery."
        )


class UndoLiveDriftError(UndoError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Live file '{path}' has drifted from the recorded applied digest. "
            "Undo was refused and nothing was written."
        )


class UndoUnsafePathError(UndoError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Undo target path '{path}' resolves outside the workspace root or crosses a "
            "symlink. Undo was refused and nothing was written."
        )


class UndoWriteError(UndoError):
    def __init__(self) -> None:
        super().__init__(
            "The live working tree could not be staged for undo; nothing was written."
        )


class JobError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class JobNotFoundError(JobError):
    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Job '{job_id}' was not found.")


class JobRetryNotEligibleError(JobError):
    def __init__(self, job_id: UUID, reason: str) -> None:
        super().__init__(f"Job '{job_id}' is not eligible for retry: {reason}")


class BackupError(CoreError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class BackupNotFoundError(BackupError):
    def __init__(self, backup_id: UUID) -> None:
        super().__init__(f"Backup '{backup_id}' was not found.")


class BackupNotCompletedError(BackupError):
    def __init__(self, backup_id: UUID) -> None:
        super().__init__(
            f"Backup '{backup_id}' has status 'failed' and cannot be restored."
        )


class BackupIntegrityError(BackupError):
    def __init__(self, backup_id: UUID, reason: str) -> None:
        super().__init__(
            f"Backup '{backup_id}' failed integrity check. {reason}"
        )


class BackupRestoreError(BackupError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class BackupWriteError(BackupError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
