from fastapi import APIRouter, status

from mensura_core.api.dependencies import CoreServiceDependency
from mensura_core.api.problems import CONFLICT_RESPONSE, VALIDATION_RESPONSE
from mensura_core.models import Workspace, WorkspaceCollection, WorkspaceCreate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=WorkspaceCollection, summary="List workspaces")
async def list_workspaces(service: CoreServiceDependency) -> WorkspaceCollection:
    workspaces = list(service.list_workspaces())
    return WorkspaceCollection(items=workspaces, total=len(workspaces))


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
