from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response, status

from mensura_core.api.dependencies import ContextPackServiceDependency
from mensura_core.api.problems import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    PAYLOAD_TOO_LARGE_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.context_pack_models import (
    ContextPackCollection,
    ContextPackManifest,
    CreateContextPackRequest,
    CreateContextPackResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/context-packs",
    tags=["context-packs"],
)

ContextPackId = Annotated[
    str,
    Path(pattern=r"^sha256:[0-9a-f]{64}$"),
]


@router.post(
    "",
    response_model=CreateContextPackResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **VALIDATION_RESPONSE,
        **CONFLICT_RESPONSE,
        **PAYLOAD_TOO_LARGE_RESPONSE,
    },
    summary="Create an immutable context pack from inventoried files",
)
def create_context_pack(
    workspace_id: UUID,
    payload: CreateContextPackRequest,
    response: Response,
    service: ContextPackServiceDependency,
) -> CreateContextPackResponse:
    result = service.create(workspace_id, payload)
    response.headers["Location"] = (
        f"/api/v1/workspaces/{workspace_id}/context-packs/{result.context_pack.id}"
    )
    return result


@router.get(
    "",
    response_model=ContextPackCollection,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="List immutable context packs for a workspace",
)
async def list_context_packs(
    workspace_id: UUID,
    service: ContextPackServiceDependency,
) -> ContextPackCollection:
    return service.list(workspace_id)


@router.get(
    "/{context_pack_id}",
    response_model=ContextPackManifest,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get an immutable context-pack manifest",
)
async def get_context_pack(
    workspace_id: UUID,
    context_pack_id: ContextPackId,
    service: ContextPackServiceDependency,
) -> ContextPackManifest:
    return service.get(workspace_id, context_pack_id)
