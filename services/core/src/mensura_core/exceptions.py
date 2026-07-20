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
