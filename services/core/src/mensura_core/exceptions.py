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
