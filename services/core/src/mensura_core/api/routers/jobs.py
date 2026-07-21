from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from mensura_core.api.dependencies import JobServiceDependency
from mensura_core.api.problems import (
    JOB_RETRY_CONFLICT_RESPONSE,
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.job_models import EnqueueJobRequest, Job, JobCollection, JobStatus, JobType

router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Enqueue a durable background job",
)
def enqueue_job(
    payload: EnqueueJobRequest,
    response: Response,
    service: JobServiceDependency,
) -> Job:
    job = service.enqueue(payload)
    response.headers["Location"] = f"/api/v1/jobs/{job.id}"
    return job


@router.get(
    "/jobs",
    response_model=JobCollection,
    responses={**VALIDATION_RESPONSE},
    summary="List durable background jobs",
)
async def list_jobs(
    service: JobServiceDependency,
    workspace_id: Annotated[UUID | None, Query(description="Filter by workspace")] = None,
    job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
    job_type: Annotated[JobType | None, Query(alias="jobType")] = None,
) -> JobCollection:
    return service.list_jobs(workspace_id=workspace_id, status=job_status, job_type=job_type)


@router.get(
    "/jobs/{job_id}",
    response_model=Job,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a durable background job",
)
async def get_job(
    job_id: UUID,
    service: JobServiceDependency,
) -> Job:
    return service.get(job_id)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=Job,
    status_code=status.HTTP_200_OK,
    responses={**NOT_FOUND_RESPONSE, **JOB_RETRY_CONFLICT_RESPONSE},
    summary="Explicitly retry a failed background job",
)
def retry_job(
    job_id: UUID,
    response: Response,
    service: JobServiceDependency,
) -> Job:
    retry = service.retry(job_id)
    response.headers["Location"] = f"/api/v1/jobs/{retry.id}"
    return retry
