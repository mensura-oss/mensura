import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from mensura_core.exceptions import (
    GuardConfigurationInvalidError,
    GuardConfigurationNotFoundError,
    GuardExecutionError,
    GuardRunInProgressError,
    GuardRunNotFoundError,
    NotGitRepositoryError,
    RepositoryPathNotFoundError,
    ResourceConflictError,
    ResourceNotFoundError,
    UnsupportedRepositoryStateError,
    UnsupportedWorkspaceStateError,
    VaultBinaryPreviewError,
    VaultFileExcludedError,
    VaultFileNotFoundError,
    VaultInventoryNotBuiltError,
    VaultPathInvalidError,
    VaultRootInvalidError,
)

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
NOT_FOUND_TYPE = "urn:mensura:problem:resource-not-found"
CONFLICT_TYPE = "urn:mensura:problem:resource-conflict"
VALIDATION_TYPE = "urn:mensura:problem:validation-error"
REPOSITORY_PATH_NOT_FOUND_TYPE = "urn:mensura:problem:repository-path-not-found"
NOT_GIT_REPOSITORY_TYPE = "urn:mensura:problem:not-a-git-repository"
UNSUPPORTED_REPOSITORY_STATE_TYPE = "urn:mensura:problem:unsupported-repository-state"
GUARD_CONFIGURATION_NOT_FOUND_TYPE = "urn:mensura:problem:guard-configuration-not-found"
INVALID_GUARD_CONFIGURATION_TYPE = "urn:mensura:problem:invalid-guard-configuration"
UNSUPPORTED_WORKSPACE_STATE_TYPE = "urn:mensura:problem:unsupported-workspace-state"
GUARD_EXECUTION_FAILED_TYPE = "urn:mensura:problem:guard-execution-failed"
GUARD_RUN_IN_PROGRESS_TYPE = "urn:mensura:problem:guard-run-in-progress"
GUARD_RUN_NOT_FOUND_TYPE = "urn:mensura:problem:guard-run-not-found"
VAULT_ROOT_INVALID_TYPE = "urn:mensura:problem:vault-root-invalid"
VAULT_INVENTORY_NOT_BUILT_TYPE = "urn:mensura:problem:vault-inventory-not-built"
VAULT_PATH_INVALID_TYPE = "urn:mensura:problem:vault-path-invalid"
VAULT_FILE_EXCLUDED_TYPE = "urn:mensura:problem:vault-file-excluded"
VAULT_BINARY_PREVIEW_TYPE = "urn:mensura:problem:vault-binary-preview-refused"
VAULT_FILE_NOT_FOUND_TYPE = "urn:mensura:problem:vault-file-not-found"


class InvalidParameter(BaseModel):
    detail: str
    pointer: str


class ProblemDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: list[InvalidParameter] | None = None


def _problem_response(
    request: Request,
    *,
    status: int,
    problem_type: str,
    title: str,
    detail: str,
    errors: list[InvalidParameter] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        type=problem_type,
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        errors=errors,
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(mode="json", exclude_none=True),
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def _json_pointer(location: tuple[Any, ...]) -> str:
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in location]
    return "#/" + "/".join(escaped)


def _status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, error: ResourceNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=NOT_FOUND_TYPE,
            title="Resource not found",
            detail=str(error),
        )

    @app.exception_handler(ResourceConflictError)
    async def resource_conflict_handler(
        request: Request, error: ResourceConflictError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=CONFLICT_TYPE,
            title="Resource conflict",
            detail=error.detail,
        )

    @app.exception_handler(RepositoryPathNotFoundError)
    async def repository_path_not_found_handler(
        request: Request, error: RepositoryPathNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=REPOSITORY_PATH_NOT_FOUND_TYPE,
            title="Repository path not found",
            detail=error.detail,
        )

    @app.exception_handler(NotGitRepositoryError)
    async def not_git_repository_handler(
        request: Request, error: NotGitRepositoryError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=NOT_GIT_REPOSITORY_TYPE,
            title="Not a Git repository",
            detail=error.detail,
        )

    @app.exception_handler(UnsupportedRepositoryStateError)
    async def unsupported_repository_state_handler(
        request: Request, error: UnsupportedRepositoryStateError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=UNSUPPORTED_REPOSITORY_STATE_TYPE,
            title="Unsupported repository state",
            detail=error.detail,
        )

    @app.exception_handler(GuardConfigurationNotFoundError)
    async def guard_configuration_not_found_handler(
        request: Request, error: GuardConfigurationNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=GUARD_CONFIGURATION_NOT_FOUND_TYPE,
            title="Guard configuration not found",
            detail=error.detail,
        )

    @app.exception_handler(GuardConfigurationInvalidError)
    async def invalid_guard_configuration_handler(
        request: Request, error: GuardConfigurationInvalidError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=INVALID_GUARD_CONFIGURATION_TYPE,
            title="Invalid Guard configuration",
            detail=error.detail,
        )

    @app.exception_handler(UnsupportedWorkspaceStateError)
    async def unsupported_workspace_state_handler(
        request: Request, error: UnsupportedWorkspaceStateError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=UNSUPPORTED_WORKSPACE_STATE_TYPE,
            title="Unsupported workspace state",
            detail=error.detail,
        )

    @app.exception_handler(GuardRunInProgressError)
    async def guard_run_in_progress_handler(
        request: Request, error: GuardRunInProgressError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=GUARD_RUN_IN_PROGRESS_TYPE,
            title="Guard run already in progress",
            detail=error.detail,
        )

    @app.exception_handler(GuardRunNotFoundError)
    async def guard_run_not_found_handler(
        request: Request, error: GuardRunNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=GUARD_RUN_NOT_FOUND_TYPE,
            title="Guard run not found",
            detail=error.detail,
        )

    @app.exception_handler(GuardExecutionError)
    async def guard_execution_handler(request: Request, error: GuardExecutionError) -> JSONResponse:
        return _problem_response(
            request,
            status=500,
            problem_type=GUARD_EXECUTION_FAILED_TYPE,
            title="Guard execution failed",
            detail=error.detail,
        )

    @app.exception_handler(VaultRootInvalidError)
    async def vault_root_invalid_handler(
        request: Request, error: VaultRootInvalidError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=VAULT_ROOT_INVALID_TYPE,
            title="Invalid Vault root",
            detail=error.detail,
        )

    @app.exception_handler(VaultInventoryNotBuiltError)
    async def vault_inventory_not_built_handler(
        request: Request, error: VaultInventoryNotBuiltError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=VAULT_INVENTORY_NOT_BUILT_TYPE,
            title="Vault inventory not built",
            detail=error.detail,
        )

    @app.exception_handler(VaultPathInvalidError)
    async def vault_path_invalid_handler(
        request: Request, error: VaultPathInvalidError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=VAULT_PATH_INVALID_TYPE,
            title="Invalid Vault file path",
            detail=error.detail,
        )

    @app.exception_handler(VaultFileExcludedError)
    async def vault_file_excluded_handler(
        request: Request, error: VaultFileExcludedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=403,
            problem_type=VAULT_FILE_EXCLUDED_TYPE,
            title="Vault file access excluded",
            detail=error.detail,
        )

    @app.exception_handler(VaultBinaryPreviewError)
    async def vault_binary_preview_handler(
        request: Request, error: VaultBinaryPreviewError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=415,
            problem_type=VAULT_BINARY_PREVIEW_TYPE,
            title="Binary preview refused",
            detail=error.detail,
        )

    @app.exception_handler(VaultFileNotFoundError)
    async def vault_file_not_found_handler(
        request: Request, error: VaultFileNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=VAULT_FILE_NOT_FOUND_TYPE,
            title="Vault file not found",
            detail=error.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        invalid_parameters = [
            InvalidParameter(detail=item["msg"], pointer=_json_pointer(tuple(item["loc"])))
            for item in error.errors()
        ]
        return _problem_response(
            request,
            status=422,
            problem_type=VALIDATION_TYPE,
            title="Request validation failed",
            detail="One or more request values are invalid.",
            errors=invalid_parameters,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        status = error.status_code
        title = _status_title(status)
        detail = error.detail if isinstance(error.detail, str) else title
        return _problem_response(
            request,
            status=status,
            problem_type="about:blank",
            title=title,
            detail=detail,
            headers=error.headers,
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled Core API error", exc_info=error)
        return _problem_response(
            request,
            status=500,
            problem_type="about:blank",
            title="Internal Server Error",
            detail="The server could not complete the request.",
        )


def problem_response(status: int, description: str) -> dict[int, dict[str, Any]]:
    return {
        status: {
            "description": description,
            "content": {
                PROBLEM_MEDIA_TYPE: {
                    "schema": ProblemDetails.model_json_schema(mode="serialization")
                }
            },
        }
    }


NOT_FOUND_RESPONSE = problem_response(404, "The requested resource does not exist.")
CONFLICT_RESPONSE = problem_response(409, "The resource conflicts with existing state.")
VALIDATION_RESPONSE = problem_response(422, "The request does not satisfy the v1 contract.")
REPOSITORY_INVALID_RESPONSE = problem_response(422, "The workspace root is not a Git repository.")
GUARD_EXECUTION_RESPONSE = problem_response(500, "A configured Guard command could not start.")
FORBIDDEN_RESPONSE = problem_response(403, "The requested path is excluded from Vault access.")
UNSUPPORTED_MEDIA_RESPONSE = problem_response(415, "The requested file is not previewable text.")
