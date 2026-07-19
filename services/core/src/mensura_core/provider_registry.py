from collections.abc import Callable

from mensura_core.exceptions import (
    ProviderConfigurationMissingError,
    ProviderConfigurationUnavailableError,
    UnsupportedProviderError,
)
from mensura_core.models import (
    OpenAIProviderConfigure,
    PromptVersion,
    ProviderCollection,
    ProviderDescriptor,
    ProviderId,
    ProviderKind,
)
from mensura_core.openai_provider import (
    HttpxOpenAIResponseTransport,
    OpenAIResponseTransport,
    OpenAIReviewProvider,
)
from mensura_core.provider_adapter import DeterministicReviewProvider, ProviderAdapter
from mensura_core.provider_config import (
    CredentialStore,
    OpenAIProviderSettings,
    ProviderConfigurationStorageError,
    ProviderSettingsRepository,
)

TransportFactory = Callable[[], OpenAIResponseTransport]


class ProviderRegistry:
    def __init__(
        self,
        settings: ProviderSettingsRepository,
        credentials: CredentialStore,
        *,
        deterministic: ProviderAdapter | None = None,
        openai_transport_factory: TransportFactory = HttpxOpenAIResponseTransport,
    ) -> None:
        self._settings = settings
        self._credentials = credentials
        self._deterministic = deterministic or DeterministicReviewProvider()
        self._openai_transport_factory = openai_transport_factory

    def list_providers(self) -> ProviderCollection:
        try:
            settings = self._settings.get_openai()
            has_key = self._credentials.get_openai_api_key() is not None
        except ProviderConfigurationStorageError as error:
            raise ProviderConfigurationUnavailableError from error
        items = [
            ProviderDescriptor(
                id=ProviderId.DETERMINISTIC,
                name="Deterministic review",
                kind=ProviderKind.DETERMINISTIC,
                configured=True,
                model=None,
                prompt_version=PromptVersion.REVIEW_V2,
            ),
            ProviderDescriptor(
                id=ProviderId.OPENAI,
                name="OpenAI",
                kind=ProviderKind.REAL,
                configured=settings is not None and has_key,
                model=settings.model if settings is not None else None,
                prompt_version=PromptVersion.REVIEW_V2,
            ),
        ]
        return ProviderCollection(items=items, total=len(items))

    def configure_openai(self, payload: OpenAIProviderConfigure) -> ProviderDescriptor:
        settings = OpenAIProviderSettings(model=payload.model)
        try:
            self._credentials.set_openai_api_key(payload.api_key.get_secret_value())
            self._settings.save_openai(settings)
        except ProviderConfigurationStorageError as error:
            raise ProviderConfigurationUnavailableError from error
        return ProviderDescriptor(
            id=ProviderId.OPENAI,
            name="OpenAI",
            kind=ProviderKind.REAL,
            configured=True,
            model=settings.model,
            prompt_version=PromptVersion.REVIEW_V2,
        )

    def resolve(self, provider_id: str) -> ProviderAdapter:
        if provider_id == ProviderId.DETERMINISTIC:
            return self._deterministic
        if provider_id != ProviderId.OPENAI:
            raise UnsupportedProviderError(provider_id)
        try:
            settings = self._settings.get_openai()
            api_key = self._credentials.get_openai_api_key()
        except ProviderConfigurationStorageError as error:
            raise ProviderConfigurationUnavailableError from error
        if settings is None or api_key is None:
            raise ProviderConfigurationMissingError(provider_id)
        return OpenAIReviewProvider(
            model=settings.model,
            api_key=api_key,
            transport=self._openai_transport_factory(),
        )
