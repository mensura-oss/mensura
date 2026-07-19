from uuid import UUID

from fastapi import APIRouter, status

from mensura_core.api.dependencies import GuardServiceDependency
from mensura_core.api.problems import (
    CONFLICT_RESPONSE,
    GUARD_EXECUTION_RESPONSE,
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.guard_models import GuardRunCreate, GuardRunResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/guard/runs",
    tags=["guard"],
)


@router.post(
    "",
    response_model=GuardRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
        **VALIDATION_RESPONSE,
        **GUARD_EXECUTION_RESPONSE,
    },
    summary="Run configured workspace Guard checks",
)
def create_guard_run(
    workspace_id: UUID,
    payload: GuardRunCreate,
    service: GuardServiceDependency,
) -> GuardRunResponse:
    return service.create_run(workspace_id, payload)


@router.get(
    "/latest",
    response_model=GuardRunResponse,
    responses=NOT_FOUND_RESPONSE,
    summary="Get the latest completed workspace Guard run",
)
async def get_latest_guard_run(
    workspace_id: UUID,
    service: GuardServiceDependency,
) -> GuardRunResponse:
    return service.get_latest(workspace_id)
