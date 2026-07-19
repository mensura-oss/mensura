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


class ProviderExecutionFailedError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"Provider execution failed for run '{run_id}'.")


class StructuredResultInvalidError(RunExecutionError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"Provider returned an invalid structured result for run '{run_id}'.")
