from typing import Annotated, cast

from fastapi import Depends, Request

from mensura_core.context_pack_service import ContextPackService
from mensura_core.guard_service import GuardService
from mensura_core.provider_registry import ProviderRegistry
from mensura_core.service import CoreService
from mensura_core.vault_service import VaultService


def get_core_service(request: Request) -> CoreService:
    return cast(CoreService, request.app.state.core_service)


CoreServiceDependency = Annotated[CoreService, Depends(get_core_service)]


def get_guard_service(request: Request) -> GuardService:
    return cast(GuardService, request.app.state.guard_service)


GuardServiceDependency = Annotated[GuardService, Depends(get_guard_service)]


def get_vault_service(request: Request) -> VaultService:
    return cast(VaultService, request.app.state.vault_service)


VaultServiceDependency = Annotated[VaultService, Depends(get_vault_service)]


def get_context_pack_service(request: Request) -> ContextPackService:
    return cast(ContextPackService, request.app.state.context_pack_service)


ContextPackServiceDependency = Annotated[ContextPackService, Depends(get_context_pack_service)]


def get_provider_registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


ProviderRegistryDependency = Annotated[ProviderRegistry, Depends(get_provider_registry)]
