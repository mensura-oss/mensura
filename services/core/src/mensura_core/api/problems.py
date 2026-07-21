import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from mensura_core.exceptions import (
    ApplicationAlreadyExistsError,
    ApplicationContentIncompleteError,
    ApplicationEmptyProposalError,
    ApplicationInProgressError,
    ApplicationLiveDriftError,
    ApplicationNotFoundError,
    ApplicationProposalNotApprovedError,
    ApplicationUnsafePathError,
    ApplicationVerificationMismatchError,
    ApplicationVerificationNotFoundError,
    ApplicationVerificationNotPassedError,
    ApplicationWriteError,
    BackupIntegrityError,
    BackupNotCompletedError,
    BackupNotFoundError,
    BackupRestoreError,
    BackupWriteError,
    ChangeProposalContentTooLargeError,
    ChangeProposalInvalidStateError,
    ChangeProposalNotFoundError,
    ChangeProposalOutputInvalidError,
    ChangeProposalRunNotEligibleError,
    ContextPackFileChangedError,
    ContextPackInvalidSelectionError,
    ContextPackNotFoundError,
    ContextPackTooLargeError,
    ContextPackWorkspaceMismatchError,
    GuardConfigurationInvalidError,
    GuardConfigurationNotFoundError,
    GuardExecutionError,
    GuardRunInProgressError,
    GuardRunNotFoundError,
    JobNotFoundError,
    NotGitRepositoryError,
    ProposalVerificationContentIncompleteError,
    ProposalVerificationInProgressError,
    ProposalVerificationNotAllowedError,
    ProposalVerificationNotFoundError,
    ProviderConfigurationMissingError,
    ProviderConfigurationUnavailableError,
    ProviderCredentialsInvalidError,
    ProviderExecutionFailedError,
    ProviderUpstreamFailedError,
    RepositoryPathNotFoundError,
    ResourceConflictError,
    ResourceNotFoundError,
    RunContextInconsistentError,
    RunContextPackMissingError,
    RunInvalidStateError,
    StructuredResultInvalidError,
    UndoAlreadyExistsError,
    UndoLiveDriftError,
    UndoMetadataIncompleteError,
    UndoNotEligibleError,
    UndoNotFoundError,
    UndoUnsafePathError,
    UndoWriteError,
    UnsupportedProviderError,
    UnsupportedRepositoryStateError,
    UnsupportedWorkspaceStateError,
    VaultBinaryPreviewError,
    VaultFileExcludedError,
    VaultFileNotFoundError,
    VaultInventoryNotBuiltError,
    VaultPathInvalidError,
    VaultRootInvalidError,
    VerificationSandboxError,
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
CONTEXT_PACK_INVALID_SELECTION_TYPE = "urn:mensura:problem:context-pack-invalid-selection"
CONTEXT_PACK_TOO_LARGE_TYPE = "urn:mensura:problem:context-pack-too-large"
CONTEXT_PACK_FILE_CHANGED_TYPE = "urn:mensura:problem:context-pack-file-changed"
CONTEXT_PACK_NOT_FOUND_TYPE = "urn:mensura:problem:context-pack-not-found"
CONTEXT_PACK_WORKSPACE_MISMATCH_TYPE = "urn:mensura:problem:context-pack-workspace-mismatch"
RUN_INVALID_STATE_TYPE = "urn:mensura:problem:run-invalid-state"
RUN_CONTEXT_PACK_MISSING_TYPE = "urn:mensura:problem:run-context-pack-missing"
RUN_CONTEXT_INCONSISTENT_TYPE = "urn:mensura:problem:run-context-inconsistent"
PROVIDER_EXECUTION_FAILED_TYPE = "urn:mensura:problem:provider-execution-failed"
UNSUPPORTED_PROVIDER_TYPE = "urn:mensura:problem:unsupported-provider"
PROVIDER_CONFIGURATION_MISSING_TYPE = "urn:mensura:problem:provider-configuration-missing"
PROVIDER_CONFIGURATION_UNAVAILABLE_TYPE = "urn:mensura:problem:provider-configuration-unavailable"
PROVIDER_CREDENTIALS_INVALID_TYPE = "urn:mensura:problem:provider-credentials-invalid"
PROVIDER_UPSTREAM_FAILED_TYPE = "urn:mensura:problem:provider-upstream-failed"
STRUCTURED_RESULT_INVALID_TYPE = "urn:mensura:problem:structured-result-invalid"
CHANGE_PROPOSAL_NOT_FOUND_TYPE = "urn:mensura:problem:change-proposal-not-found"
CHANGE_PROPOSAL_RUN_NOT_ELIGIBLE_TYPE = "urn:mensura:problem:change-proposal-run-not-eligible"
CHANGE_PROPOSAL_OUTPUT_INVALID_TYPE = "urn:mensura:problem:change-proposal-output-invalid"
CHANGE_PROPOSAL_CONTENT_TOO_LARGE_TYPE = "urn:mensura:problem:change-proposal-content-too-large"
CHANGE_PROPOSAL_INVALID_STATE_TYPE = "urn:mensura:problem:change-proposal-invalid-state"
VERIFICATION_NOT_FOUND_TYPE = "urn:mensura:problem:verification-not-found"
VERIFICATION_PROPOSAL_NOT_APPROVED_TYPE = "urn:mensura:problem:verification-proposal-not-approved"
VERIFICATION_CONTENT_INCOMPLETE_TYPE = "urn:mensura:problem:verification-content-incomplete"
VERIFICATION_IN_PROGRESS_TYPE = "urn:mensura:problem:verification-in-progress"
VERIFICATION_SANDBOX_FAILED_TYPE = "urn:mensura:problem:verification-sandbox-failed"
APPLICATION_NOT_FOUND_TYPE = "urn:mensura:problem:application-not-found"
APPLICATION_PROPOSAL_NOT_APPROVED_TYPE = "urn:mensura:problem:application-proposal-not-approved"
APPLICATION_CONTENT_INCOMPLETE_TYPE = "urn:mensura:problem:application-content-incomplete"
APPLICATION_EMPTY_PROPOSAL_TYPE = "urn:mensura:problem:application-empty-proposal"
APPLICATION_VERIFICATION_NOT_FOUND_TYPE = "urn:mensura:problem:application-verification-not-found"
APPLICATION_VERIFICATION_MISMATCH_TYPE = "urn:mensura:problem:application-verification-mismatch"
APPLICATION_VERIFICATION_NOT_PASSED_TYPE = "urn:mensura:problem:application-verification-not-passed"
APPLICATION_ALREADY_EXISTS_TYPE = "urn:mensura:problem:application-already-exists"
APPLICATION_IN_PROGRESS_TYPE = "urn:mensura:problem:application-in-progress"
APPLICATION_LIVE_DRIFT_TYPE = "urn:mensura:problem:application-live-drift"
APPLICATION_UNSAFE_PATH_TYPE = "urn:mensura:problem:application-unsafe-path"
APPLICATION_WRITE_FAILED_TYPE = "urn:mensura:problem:application-write-failed"
UNDO_NOT_FOUND_TYPE = "urn:mensura:problem:undo-not-found"
UNDO_NOT_ELIGIBLE_TYPE = "urn:mensura:problem:undo-not-eligible"
UNDO_ALREADY_EXISTS_TYPE = "urn:mensura:problem:undo-already-exists"
UNDO_METADATA_INCOMPLETE_TYPE = "urn:mensura:problem:undo-metadata-incomplete"
UNDO_LIVE_DRIFT_TYPE = "urn:mensura:problem:undo-live-drift"
UNDO_UNSAFE_PATH_TYPE = "urn:mensura:problem:undo-unsafe-path"
UNDO_WRITE_FAILED_TYPE = "urn:mensura:problem:undo-write-failed"
JOB_NOT_FOUND_TYPE = "urn:mensura:problem:job-not-found"
BACKUP_NOT_FOUND_TYPE = "urn:mensura:problem:backup-not-found"
BACKUP_NOT_COMPLETED_TYPE = "urn:mensura:problem:backup-not-completed"
BACKUP_INTEGRITY_ERROR_TYPE = "urn:mensura:problem:backup-integrity-error"
BACKUP_RESTORE_FAILED_TYPE = "urn:mensura:problem:backup-restore-failed"
BACKUP_WRITE_FAILED_TYPE = "urn:mensura:problem:backup-write-failed"


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

    @app.exception_handler(ContextPackInvalidSelectionError)
    async def context_pack_invalid_selection_handler(
        request: Request, error: ContextPackInvalidSelectionError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=CONTEXT_PACK_INVALID_SELECTION_TYPE,
            title="Invalid context-pack selection",
            detail=error.detail,
        )

    @app.exception_handler(ContextPackTooLargeError)
    async def context_pack_too_large_handler(
        request: Request, error: ContextPackTooLargeError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=413,
            problem_type=CONTEXT_PACK_TOO_LARGE_TYPE,
            title="Context pack is too large",
            detail=error.detail,
        )

    @app.exception_handler(ContextPackFileChangedError)
    async def context_pack_file_changed_handler(
        request: Request, error: ContextPackFileChangedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=CONTEXT_PACK_FILE_CHANGED_TYPE,
            title="Context-pack file changed",
            detail=error.detail,
        )

    @app.exception_handler(ContextPackNotFoundError)
    async def context_pack_not_found_handler(
        request: Request, error: ContextPackNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=CONTEXT_PACK_NOT_FOUND_TYPE,
            title="Context pack not found",
            detail=error.detail,
        )

    @app.exception_handler(ContextPackWorkspaceMismatchError)
    async def context_pack_workspace_mismatch_handler(
        request: Request, error: ContextPackWorkspaceMismatchError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=CONTEXT_PACK_WORKSPACE_MISMATCH_TYPE,
            title="Context pack workspace mismatch",
            detail=error.detail,
        )

    @app.exception_handler(RunInvalidStateError)
    async def run_invalid_state_handler(
        request: Request, error: RunInvalidStateError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=RUN_INVALID_STATE_TYPE,
            title="Run cannot execute from its current state",
            detail=error.detail,
        )

    @app.exception_handler(RunContextPackMissingError)
    async def run_context_pack_missing_handler(
        request: Request, error: RunContextPackMissingError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=RUN_CONTEXT_PACK_MISSING_TYPE,
            title="Bound context pack is unavailable",
            detail=error.detail,
        )

    @app.exception_handler(RunContextInconsistentError)
    async def run_context_inconsistent_handler(
        request: Request, error: RunContextInconsistentError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=RUN_CONTEXT_INCONSISTENT_TYPE,
            title="Run context binding is inconsistent",
            detail=error.detail,
        )

    @app.exception_handler(ProviderExecutionFailedError)
    async def provider_execution_failed_handler(
        request: Request, error: ProviderExecutionFailedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=502,
            problem_type=PROVIDER_EXECUTION_FAILED_TYPE,
            title="Provider execution failed",
            detail=error.detail,
        )

    @app.exception_handler(UnsupportedProviderError)
    async def unsupported_provider_handler(
        request: Request, error: UnsupportedProviderError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=UNSUPPORTED_PROVIDER_TYPE,
            title="Unsupported provider",
            detail=error.detail,
        )

    @app.exception_handler(ProviderConfigurationMissingError)
    async def provider_configuration_missing_handler(
        request: Request, error: ProviderConfigurationMissingError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=PROVIDER_CONFIGURATION_MISSING_TYPE,
            title="Provider configuration missing",
            detail=error.detail,
        )

    @app.exception_handler(ProviderConfigurationUnavailableError)
    async def provider_configuration_unavailable_handler(
        request: Request, error: ProviderConfigurationUnavailableError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=503,
            problem_type=PROVIDER_CONFIGURATION_UNAVAILABLE_TYPE,
            title="Provider configuration unavailable",
            detail=error.detail,
        )

    @app.exception_handler(ProviderCredentialsInvalidError)
    async def provider_credentials_invalid_handler(
        request: Request, error: ProviderCredentialsInvalidError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=PROVIDER_CREDENTIALS_INVALID_TYPE,
            title="Provider credentials invalid",
            detail=error.detail,
        )

    @app.exception_handler(ProviderUpstreamFailedError)
    async def provider_upstream_failed_handler(
        request: Request, error: ProviderUpstreamFailedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=502,
            problem_type=PROVIDER_UPSTREAM_FAILED_TYPE,
            title="Upstream provider failed",
            detail=error.detail,
        )

    @app.exception_handler(StructuredResultInvalidError)
    async def structured_result_invalid_handler(
        request: Request, error: StructuredResultInvalidError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=502,
            problem_type=STRUCTURED_RESULT_INVALID_TYPE,
            title="Provider result is invalid",
            detail=error.detail,
        )

    @app.exception_handler(ChangeProposalNotFoundError)
    async def change_proposal_not_found_handler(
        request: Request, error: ChangeProposalNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=CHANGE_PROPOSAL_NOT_FOUND_TYPE,
            title="Change proposal not found",
            detail=error.detail,
        )

    @app.exception_handler(ChangeProposalRunNotEligibleError)
    async def change_proposal_run_not_eligible_handler(
        request: Request, error: ChangeProposalRunNotEligibleError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=CHANGE_PROPOSAL_RUN_NOT_ELIGIBLE_TYPE,
            title="Run is not eligible for a change proposal",
            detail=error.detail,
        )

    @app.exception_handler(ChangeProposalOutputInvalidError)
    async def change_proposal_output_invalid_handler(
        request: Request, error: ChangeProposalOutputInvalidError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=CHANGE_PROPOSAL_OUTPUT_INVALID_TYPE,
            title="Change proposal output is invalid",
            detail=error.detail,
        )

    @app.exception_handler(ChangeProposalContentTooLargeError)
    async def change_proposal_content_too_large_handler(
        request: Request, error: ChangeProposalContentTooLargeError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=413,
            problem_type=CHANGE_PROPOSAL_CONTENT_TOO_LARGE_TYPE,
            title="Change proposal content is too large",
            detail=error.detail,
        )

    @app.exception_handler(ChangeProposalInvalidStateError)
    async def change_proposal_invalid_state_handler(
        request: Request, error: ChangeProposalInvalidStateError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=CHANGE_PROPOSAL_INVALID_STATE_TYPE,
            title="Change proposal is already reviewed",
            detail=error.detail,
        )

    @app.exception_handler(ProposalVerificationNotFoundError)
    async def proposal_verification_not_found_handler(
        request: Request, error: ProposalVerificationNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=VERIFICATION_NOT_FOUND_TYPE,
            title="Proposal verification not found",
            detail=error.detail,
        )

    @app.exception_handler(ProposalVerificationNotAllowedError)
    async def proposal_verification_not_allowed_handler(
        request: Request, error: ProposalVerificationNotAllowedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=VERIFICATION_PROPOSAL_NOT_APPROVED_TYPE,
            title="Proposal is not approved for verification",
            detail=error.detail,
        )

    @app.exception_handler(ProposalVerificationContentIncompleteError)
    async def proposal_verification_content_incomplete_handler(
        request: Request, error: ProposalVerificationContentIncompleteError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=VERIFICATION_CONTENT_INCOMPLETE_TYPE,
            title="Proposal content is incomplete for verification",
            detail=error.detail,
        )

    @app.exception_handler(ProposalVerificationInProgressError)
    async def proposal_verification_in_progress_handler(
        request: Request, error: ProposalVerificationInProgressError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=VERIFICATION_IN_PROGRESS_TYPE,
            title="Proposal verification already in progress",
            detail=error.detail,
        )

    @app.exception_handler(VerificationSandboxError)
    async def verification_sandbox_failed_handler(
        request: Request, error: VerificationSandboxError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=500,
            problem_type=VERIFICATION_SANDBOX_FAILED_TYPE,
            title="Verification sandbox could not be created",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationNotFoundError)
    async def application_not_found_handler(
        request: Request, error: ApplicationNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=APPLICATION_NOT_FOUND_TYPE,
            title="Application not found",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationProposalNotApprovedError)
    async def application_proposal_not_approved_handler(
        request: Request, error: ApplicationProposalNotApprovedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=APPLICATION_PROPOSAL_NOT_APPROVED_TYPE,
            title="Proposal is not approved for application",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationContentIncompleteError)
    async def application_content_incomplete_handler(
        request: Request, error: ApplicationContentIncompleteError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=APPLICATION_CONTENT_INCOMPLETE_TYPE,
            title="Proposal content is incomplete for application",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationEmptyProposalError)
    async def application_empty_proposal_handler(
        request: Request, error: ApplicationEmptyProposalError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=APPLICATION_EMPTY_PROPOSAL_TYPE,
            title="Proposal has no changes to apply",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationVerificationNotFoundError)
    async def application_verification_not_found_handler(
        request: Request, error: ApplicationVerificationNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=APPLICATION_VERIFICATION_NOT_FOUND_TYPE,
            title="Verification not found for application",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationVerificationMismatchError)
    async def application_verification_mismatch_handler(
        request: Request, error: ApplicationVerificationMismatchError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=APPLICATION_VERIFICATION_MISMATCH_TYPE,
            title="Verification does not match the proposal",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationVerificationNotPassedError)
    async def application_verification_not_passed_handler(
        request: Request, error: ApplicationVerificationNotPassedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=APPLICATION_VERIFICATION_NOT_PASSED_TYPE,
            title="Verification did not pass",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationAlreadyExistsError)
    async def application_already_exists_handler(
        request: Request, error: ApplicationAlreadyExistsError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=APPLICATION_ALREADY_EXISTS_TYPE,
            title="Proposal already applied",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationInProgressError)
    async def application_in_progress_handler(
        request: Request, error: ApplicationInProgressError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=APPLICATION_IN_PROGRESS_TYPE,
            title="Application already in progress",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationLiveDriftError)
    async def application_live_drift_handler(
        request: Request, error: ApplicationLiveDriftError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=APPLICATION_LIVE_DRIFT_TYPE,
            title="Live working tree drifted from the verified basis",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationUnsafePathError)
    async def application_unsafe_path_handler(
        request: Request, error: ApplicationUnsafePathError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=APPLICATION_UNSAFE_PATH_TYPE,
            title="Proposed path is unsafe",
            detail=error.detail,
        )

    @app.exception_handler(ApplicationWriteError)
    async def application_write_failed_handler(
        request: Request, error: ApplicationWriteError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=500,
            problem_type=APPLICATION_WRITE_FAILED_TYPE,
            title="Live working tree could not be written",
            detail=error.detail,
        )

    @app.exception_handler(UndoNotFoundError)
    async def undo_not_found_handler(
        request: Request, error: UndoNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=UNDO_NOT_FOUND_TYPE,
            title="Undo artifact not found",
            detail=error.detail,
        )

    @app.exception_handler(UndoNotEligibleError)
    async def undo_not_eligible_handler(
        request: Request, error: UndoNotEligibleError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=UNDO_NOT_ELIGIBLE_TYPE,
            title="Application is not eligible for undo",
            detail=error.detail,
        )

    @app.exception_handler(UndoAlreadyExistsError)
    async def undo_already_exists_handler(
        request: Request, error: UndoAlreadyExistsError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=UNDO_ALREADY_EXISTS_TYPE,
            title="Application already undone",
            detail=error.detail,
        )

    @app.exception_handler(UndoMetadataIncompleteError)
    async def undo_metadata_incomplete_handler(
        request: Request, error: UndoMetadataIncompleteError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=UNDO_METADATA_INCOMPLETE_TYPE,
            title="Undo metadata is incomplete",
            detail=error.detail,
        )

    @app.exception_handler(UndoLiveDriftError)
    async def undo_live_drift_handler(
        request: Request, error: UndoLiveDriftError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=UNDO_LIVE_DRIFT_TYPE,
            title="Live working tree drifted from the applied digest",
            detail=error.detail,
        )

    @app.exception_handler(UndoUnsafePathError)
    async def undo_unsafe_path_handler(
        request: Request, error: UndoUnsafePathError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=UNDO_UNSAFE_PATH_TYPE,
            title="Undo target path is unsafe",
            detail=error.detail,
        )

    @app.exception_handler(UndoWriteError)
    async def undo_write_failed_handler(
        request: Request, error: UndoWriteError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=500,
            problem_type=UNDO_WRITE_FAILED_TYPE,
            title="Live working tree could not be restored by undo",
            detail=error.detail,
        )

    @app.exception_handler(JobNotFoundError)
    async def job_not_found_handler(
        request: Request, error: JobNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=JOB_NOT_FOUND_TYPE,
            title="Job not found",
            detail=error.detail,
        )

    @app.exception_handler(BackupNotFoundError)
    async def backup_not_found_handler(
        request: Request, error: BackupNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=BACKUP_NOT_FOUND_TYPE,
            title="Backup not found",
            detail=error.detail,
        )

    @app.exception_handler(BackupNotCompletedError)
    async def backup_not_completed_handler(
        request: Request, error: BackupNotCompletedError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=BACKUP_NOT_COMPLETED_TYPE,
            title="Backup cannot be restored",
            detail=error.detail,
        )

    @app.exception_handler(BackupIntegrityError)
    async def backup_integrity_handler(
        request: Request, error: BackupIntegrityError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=422,
            problem_type=BACKUP_INTEGRITY_ERROR_TYPE,
            title="Backup integrity check failed",
            detail=error.detail,
        )

    @app.exception_handler(BackupRestoreError)
    async def backup_restore_failed_handler(
        request: Request, error: BackupRestoreError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=500,
            problem_type=BACKUP_RESTORE_FAILED_TYPE,
            title="Database restore failed",
            detail=error.detail,
        )

    @app.exception_handler(BackupWriteError)
    async def backup_write_failed_handler(
        request: Request, error: BackupWriteError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=500,
            problem_type=BACKUP_WRITE_FAILED_TYPE,
            title="Database backup failed",
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
PAYLOAD_TOO_LARGE_RESPONSE = problem_response(413, "The context-pack selection exceeds a limit.")
CHANGE_PROPOSAL_TOO_LARGE_RESPONSE = problem_response(
    413, "The stored proposal draft exceeds the bounded source-content limit."
)
CHANGE_PROPOSAL_CONFLICT_RESPONSE = problem_response(
    409, "The run or proposal state does not allow this action."
)
CHANGE_PROPOSAL_INVALID_RESPONSE = problem_response(
    422, "The stored provider proposal output is not safe to materialize."
)
VERIFICATION_CONFLICT_RESPONSE = problem_response(
    409, "The proposal or workspace state does not allow isolated verification."
)
VERIFICATION_UNSUPPORTED_RESPONSE = problem_response(
    422, "The proposal content or workspace repository cannot be verified."
)
VERIFICATION_SANDBOX_RESPONSE = problem_response(
    500, "The temporary isolated sandbox or a Guard command could not be started."
)
APPLICATION_CONFLICT_RESPONSE = problem_response(
    409, "The proposal, verification, or live working tree does not allow application."
)
APPLICATION_UNSUPPORTED_RESPONSE = problem_response(
    422, "The proposal content, referenced verification, or a proposed path cannot be applied."
)
APPLICATION_WRITE_RESPONSE = problem_response(
    500, "The live working tree could not be staged for application."
)
UNDO_CONFLICT_RESPONSE = problem_response(
    409, "The application, live working tree, or undo state does not allow undo."
)
UNDO_UNSUPPORTED_RESPONSE = problem_response(
    422, "The undo metadata or a target path cannot be processed."
)
UNDO_WRITE_RESPONSE = problem_response(
    500, "The live working tree could not be restored by undo."
)
EXECUTION_CONFLICT_RESPONSE = problem_response(409, "The run cannot execute from current state.")
PROVIDER_EXECUTION_RESPONSE = problem_response(502, "The provider execution did not succeed.")
PROVIDER_CONFIGURATION_RESPONSE = problem_response(
    503, "Local provider settings or credential storage is unavailable."
)
BACKUP_CONFLICT_RESPONSE = problem_response(
    409, "The backup cannot be restored from its current status."
)
BACKUP_INTEGRITY_RESPONSE = problem_response(
    422, "The backup file failed integrity verification."
)
BACKUP_RESTORE_RESPONSE = problem_response(
    500, "The database could not be restored from the backup."
)
BACKUP_WRITE_RESPONSE = problem_response(
    500, "The database backup could not be created."
)
