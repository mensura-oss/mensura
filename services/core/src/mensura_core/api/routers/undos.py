from uuid import UUID

from fastapi import APIRouter, Response, status

from mensura_core.api.dependencies import UndoServiceDependency
from mensura_core.api.problems import (
    NOT_FOUND_RESPONSE,
    UNDO_CONFLICT_RESPONSE,
    UNDO_UNSUPPORTED_RESPONSE,
    UNDO_WRITE_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.undo_models import UndoArtifact, UndoCollection

router = APIRouter(tags=["undos"])


@router.post(
    "/applications/{application_id}/undo",
    response_model=UndoArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **UNDO_CONFLICT_RESPONSE,
        **UNDO_UNSUPPORTED_RESPONSE,
        **UNDO_WRITE_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Explicitly undo a previously applied text-file application",
)
def undo_application(
    application_id: UUID,
    response: Response,
    service: UndoServiceDependency,
) -> UndoArtifact:
    undo = service.undo(application_id)
    response.headers["Location"] = f"/api/v1/undos/{undo.id}"
    return undo


@router.get(
    "/undos/{undo_id}",
    response_model=UndoArtifact,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get an undo artifact",
)
async def get_undo(
    undo_id: UUID,
    service: UndoServiceDependency,
) -> UndoArtifact:
    return service.get(undo_id)


@router.get(
    "/workspaces/{workspace_id}/undos",
    response_model=UndoCollection,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="List undo artifacts for a workspace",
)
async def list_workspace_undos(
    workspace_id: UUID,
    service: UndoServiceDependency,
) -> UndoCollection:
    return service.list_for_workspace(workspace_id)
