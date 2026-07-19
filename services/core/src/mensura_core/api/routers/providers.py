from fastapi import APIRouter

from mensura_core.api.dependencies import ProviderRegistryDependency
from mensura_core.api.problems import PROVIDER_CONFIGURATION_RESPONSE, VALIDATION_RESPONSE
from mensura_core.models import OpenAIProviderConfigure, ProviderCollection, ProviderDescriptor

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get(
    "",
    response_model=ProviderCollection,
    responses=PROVIDER_CONFIGURATION_RESPONSE,
    summary="List available local providers",
)
def list_providers(registry: ProviderRegistryDependency) -> ProviderCollection:
    return registry.list_providers()


@router.put(
    "/openai/config",
    response_model=ProviderDescriptor,
    responses={**VALIDATION_RESPONSE, **PROVIDER_CONFIGURATION_RESPONSE},
    summary="Configure the local OpenAI BYOK provider",
)
def configure_openai_provider(
    payload: OpenAIProviderConfigure,
    registry: ProviderRegistryDependency,
) -> ProviderDescriptor:
    return registry.configure_openai(payload)
