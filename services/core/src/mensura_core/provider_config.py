import json
import os
import sys
from pathlib import Path
from typing import Literal, Protocol

import keyring
from keyring.errors import KeyringError
from pydantic import ValidationError

from mensura_core.models import ModelIdentifier, ResourceModel

KEYRING_SERVICE = "dev.mensura.studio"
OPENAI_KEYRING_ACCOUNT = "openai-api-key"


class OpenAIProviderSettings(ResourceModel):
    model: ModelIdentifier


class ProviderSettingsFile(ResourceModel):
    schema_version: Literal["1"] = "1"
    openai: OpenAIProviderSettings | None = None


class ProviderSettingsRepository(Protocol):
    def get_openai(self) -> OpenAIProviderSettings | None: ...

    def save_openai(self, settings: OpenAIProviderSettings) -> None: ...


class CredentialStore(Protocol):
    def get_openai_api_key(self) -> str | None: ...

    def set_openai_api_key(self, api_key: str) -> None: ...


class ProviderConfigurationStorageError(Exception):
    """The local settings or operating-system credential backend is unavailable."""


class JsonProviderSettingsRepository:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_provider_settings_path()

    def get_openai(self) -> OpenAIProviderSettings | None:
        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            return ProviderSettingsFile.model_validate(payload).openai
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise ProviderConfigurationStorageError from error

    def save_openai(self, settings: OpenAIProviderSettings) -> None:
        try:
            self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = self._path.with_suffix(f"{self._path.suffix}.tmp")
            content = json.dumps(
                ProviderSettingsFile(openai=settings).model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            temporary.write_text(f"{content}\n", encoding="utf-8")
            temporary.chmod(0o600)
            temporary.replace(self._path)
        except OSError as error:
            raise ProviderConfigurationStorageError from error


class KeyringCredentialStore:
    def get_openai_api_key(self) -> str | None:
        try:
            return keyring.get_password(KEYRING_SERVICE, OPENAI_KEYRING_ACCOUNT)
        except KeyringError as error:
            raise ProviderConfigurationStorageError from error

    def set_openai_api_key(self, api_key: str) -> None:
        try:
            keyring.set_password(KEYRING_SERVICE, OPENAI_KEYRING_ACCOUNT, api_key)
        except KeyringError as error:
            raise ProviderConfigurationStorageError from error


class InMemoryProviderSettingsRepository:
    def __init__(self) -> None:
        self.settings: OpenAIProviderSettings | None = None

    def get_openai(self) -> OpenAIProviderSettings | None:
        return self.settings

    def save_openai(self, settings: OpenAIProviderSettings) -> None:
        self.settings = settings


class InMemoryCredentialStore:
    def __init__(self, openai_api_key: str | None = None) -> None:
        self.openai_api_key = openai_api_key

    def get_openai_api_key(self) -> str | None:
        return self.openai_api_key

    def set_openai_api_key(self, api_key: str) -> None:
        self.openai_api_key = api_key


def default_provider_settings_path() -> Path:
    configured_directory = os.environ.get("MENSURA_CONFIG_DIR")
    if configured_directory:
        return Path(configured_directory).expanduser() / "providers.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Mensura" / "providers.json"
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "Mensura" / "providers.json"
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base / "mensura" / "providers.json"
