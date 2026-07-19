from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from mensura_core.api.dependencies import VaultServiceDependency
from mensura_core.api.problems import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNSUPPORTED_MEDIA_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.vault_models import (
    VaultFileCollection,
    VaultFilePreview,
    VaultInventorySnapshot,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/vault",
    tags=["vault"],
)


@router.post(
    "/inventory",
    response_model=VaultInventorySnapshot,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
    summary="Build or refresh the workspace Vault inventory",
)
def build_vault_inventory(
    workspace_id: UUID,
    service: VaultServiceDependency,
) -> VaultInventorySnapshot:
    return service.build_inventory(workspace_id)


@router.get(
    "/inventory",
    response_model=VaultInventorySnapshot,
    responses=NOT_FOUND_RESPONSE,
    summary="Get the latest workspace Vault inventory summary",
)
async def get_vault_inventory(
    workspace_id: UUID,
    service: VaultServiceDependency,
) -> VaultInventorySnapshot:
    return service.get_inventory(workspace_id)


@router.get(
    "/files",
    response_model=VaultFileCollection,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="List deterministic file metadata from the latest Vault inventory",
)
async def list_vault_files(
    workspace_id: UUID,
    service: VaultServiceDependency,
    query: Annotated[str | None, Query(max_length=240)] = None,
    extension: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> VaultFileCollection:
    return service.list_files(
        workspace_id,
        query=query,
        extension=extension,
        limit=limit,
    )


@router.get(
    "/files/content",
    response_model=VaultFilePreview,
    responses={
        **NOT_FOUND_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **VALIDATION_RESPONSE,
        **UNSUPPORTED_MEDIA_RESPONSE,
        **CONFLICT_RESPONSE,
    },
    summary="Get a bounded UTF-8 preview for one inventoried file",
)
def get_vault_file_preview(
    workspace_id: UUID,
    service: VaultServiceDependency,
    path: Annotated[str, Query(min_length=1, max_length=4096)],
) -> VaultFilePreview:
    return service.get_file_preview(workspace_id, path)
