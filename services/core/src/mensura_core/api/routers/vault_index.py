from uuid import UUID

from fastapi import APIRouter, status

from mensura_core.api.dependencies import VaultIndexServiceDependency
from mensura_core.api.problems import (
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
    VAULT_EMBEDDING_UNAVAILABLE_RESPONSE,
)
from mensura_core.vault_index_models import (
    VaultArchitectureSummary,
    VaultIndexRequest,
    VaultIndexSnapshot,
    VaultMemoryItemDetail,
    VaultSearchRequest,
    VaultSearchResponse,
    VaultSummarizeRequest,
)

router = APIRouter(prefix="/vault", tags=["vault-index"])


@router.post(
    "/index",
    response_model=VaultIndexSnapshot,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **VALIDATION_RESPONSE,
        **VAULT_EMBEDDING_UNAVAILABLE_RESPONSE,
    },
    summary="Index a workspace into Vault memory items and chunks",
)
def index_workspace(
    request: VaultIndexRequest,
    service: VaultIndexServiceDependency,
) -> VaultIndexSnapshot:
    return service.index_workspace(request.workspace_id)


@router.get(
    "/indexes/{workspace_id}",
    response_model=VaultIndexSnapshot,
    responses=NOT_FOUND_RESPONSE,
    summary="Get the latest Vault index status and summary for a workspace",
)
def get_vault_index(
    workspace_id: UUID,
    service: VaultIndexServiceDependency,
) -> VaultIndexSnapshot:
    return service.get_index(workspace_id)


@router.post(
    "/search",
    response_model=VaultSearchResponse,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Search indexed Vault chunks by semantic-lexical relevance",
)
def search_vault(
    request: VaultSearchRequest,
    service: VaultIndexServiceDependency,
) -> VaultSearchResponse:
    return service.search(
        request.workspace_id,
        query=request.query,
        limit=request.limit,
        source_type=request.source_type,
    )


@router.get(
    "/memory/{memory_id}",
    response_model=VaultMemoryItemDetail,
    responses=NOT_FOUND_RESPONSE,
    summary="Get one Vault memory item and its chunks",
)
def get_vault_memory_item(
    memory_id: UUID,
    service: VaultIndexServiceDependency,
) -> VaultMemoryItemDetail:
    return service.get_memory_item(memory_id)


@router.post(
    "/summarize",
    response_model=VaultArchitectureSummary,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Generate a basic architecture summary from indexed Vault material",
)
def summarize_vault(
    request: VaultSummarizeRequest,
    service: VaultIndexServiceDependency,
) -> VaultArchitectureSummary:
    return service.summarize(request.workspace_id)
