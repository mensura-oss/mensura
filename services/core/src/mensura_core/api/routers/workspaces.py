from uuid import UUID

from fastapi import APIRouter, status

from mensura_core.api.dependencies import CoreServiceDependency
from mensura_core.api.problems import (
    CONFLICT_RESPONSE,
    NOT_FOUND_RESPONSE,
    REPOSITORY_INVALID_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.models import Workspace, WorkspaceCollection, WorkspaceCreate
from mensura_core.repository_models import RepositorySummary

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=WorkspaceCollection, summary="List workspaces")
async def list_workspaces(service: CoreServiceDependency) -> WorkspaceCollection:
    workspaces = list(service.list_workspaces())
    return WorkspaceCollection(items=workspaces, total=len(workspaces))


@router.get(
    "/{workspace_id}/repository",
    response_model=RepositorySummary,
    responses={
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
        **REPOSITORY_INVALID_RESPONSE,
    },
    summary="Inspect a workspace Git repository",
)
async def inspect_workspace_repository(
    workspace_id: UUID,
    service: CoreServiceDependency,
) -> RepositorySummary:
    return service.inspect_workspace_repository(workspace_id)


@router.post(
    "",
    response_model=Workspace,
    status_code=status.HTTP_201_CREATED,
    responses={**CONFLICT_RESPONSE, **VALIDATION_RESPONSE},
    summary="Create a workspace",
)
async def create_workspace(
    payload: WorkspaceCreate,
    service: CoreServiceDependency,
) -> Workspace:
    return service.create_workspace(payload)
