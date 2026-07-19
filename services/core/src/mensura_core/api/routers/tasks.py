from uuid import UUID

from fastapi import APIRouter, Response, status

from mensura_core.api.dependencies import CoreServiceDependency
from mensura_core.api.problems import NOT_FOUND_RESPONSE, VALIDATION_RESPONSE
from mensura_core.models import Run, Task, TaskCreate

router = APIRouter(tags=["tasks"])


@router.get(
    "/tasks/{task_id}",
    response_model=Task,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a task",
)
async def get_task(task_id: UUID, service: CoreServiceDependency) -> Task:
    return service.get_task(task_id)


@router.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Create a task",
)
async def create_task(
    payload: TaskCreate,
    response: Response,
    service: CoreServiceDependency,
) -> Task:
    task = service.create_task(payload)
    response.headers["Location"] = f"/api/v1/tasks/{task.id}"
    return task


@router.post(
    "/tasks/{task_id}/runs",
    response_model=Run,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Create a queued run",
)
async def create_run(
    task_id: UUID,
    response: Response,
    service: CoreServiceDependency,
) -> Run:
    run = service.create_run(task_id)
    response.headers["Location"] = f"/api/v1/runs/{run.id}"
    return run
