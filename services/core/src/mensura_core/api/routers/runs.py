from uuid import UUID

from fastapi import APIRouter

from mensura_core.api.dependencies import CoreServiceDependency
from mensura_core.api.problems import NOT_FOUND_RESPONSE, VALIDATION_RESPONSE
from mensura_core.models import Run

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get(
    "/{run_id}",
    response_model=Run,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a run",
)
async def get_run(run_id: UUID, service: CoreServiceDependency) -> Run:
    return service.get_run(run_id)
