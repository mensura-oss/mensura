from uuid import UUID

from fastapi import APIRouter

from mensura_core.api.dependencies import CoreServiceDependency
from mensura_core.api.problems import (
    EXECUTION_CONFLICT_RESPONSE,
    NOT_FOUND_RESPONSE,
    PROVIDER_CONFIGURATION_RESPONSE,
    PROVIDER_EXECUTION_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.models import Run, RunExecute

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get(
    "/{run_id}",
    response_model=Run,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a run",
)
async def get_run(run_id: UUID, service: CoreServiceDependency) -> Run:
    return service.get_run(run_id)


@router.post(
    "/{run_id}/execute",
    response_model=Run,
    responses={
        **NOT_FOUND_RESPONSE,
        **EXECUTION_CONFLICT_RESPONSE,
        **PROVIDER_EXECUTION_RESPONSE,
        **PROVIDER_CONFIGURATION_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Manually execute a queued run",
)
def execute_run(run_id: UUID, payload: RunExecute, service: CoreServiceDependency) -> Run:
    return service.execute_run(run_id, payload)
