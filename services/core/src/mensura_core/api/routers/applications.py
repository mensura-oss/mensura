from uuid import UUID

from fastapi import APIRouter, Response, status

from mensura_core.api.dependencies import ChangeApplicationServiceDependency
from mensura_core.api.problems import (
    APPLICATION_CONFLICT_RESPONSE,
    APPLICATION_UNSUPPORTED_RESPONSE,
    APPLICATION_WRITE_RESPONSE,
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.application_models import (
    ApplicationArtifact,
    ApplicationCollection,
    ApplyChangeProposal,
)

router = APIRouter(tags=["applications"])


@router.post(
    "/change-proposals/{proposal_id}/apply",
    response_model=ApplicationArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **APPLICATION_CONFLICT_RESPONSE,
        **APPLICATION_UNSUPPORTED_RESPONSE,
        **APPLICATION_WRITE_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Explicitly apply an approved, verified proposal to the live working tree",
)
def apply_change_proposal(
    proposal_id: UUID,
    payload: ApplyChangeProposal,
    response: Response,
    service: ChangeApplicationServiceDependency,
) -> ApplicationArtifact:
    application = service.apply(proposal_id, payload.verification_id)
    response.headers["Location"] = f"/api/v1/applications/{application.id}"
    return application


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationArtifact,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a live application artifact",
)
async def get_application(
    application_id: UUID,
    service: ChangeApplicationServiceDependency,
) -> ApplicationArtifact:
    return service.get(application_id)


@router.get(
    "/workspaces/{workspace_id}/applications",
    response_model=ApplicationCollection,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="List live application artifacts for a workspace",
)
async def list_workspace_applications(
    workspace_id: UUID,
    service: ChangeApplicationServiceDependency,
) -> ApplicationCollection:
    return service.list_for_workspace(workspace_id)
