import json

import pytest
from fastapi.testclient import TestClient

from mensura_core.main import create_app
from mensura_core.provider_config import (
    InMemoryCredentialStore,
    InMemoryProviderSettingsRepository,
    JsonProviderSettingsRepository,
    OpenAIProviderSettings,
    ProviderConfigurationStorageError,
)


def test_provider_discovery_is_redacted_and_deterministic_is_always_available() -> None:
    settings = InMemoryProviderSettingsRepository()
    credentials = InMemoryCredentialStore()
    with TestClient(
        create_app(
            provider_settings_repository=settings,
            credential_store=credentials,
        )
    ) as client:
        response = client.get("/api/v1/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"] == [
        {
            "id": "mensura.builtin",
            "name": "Deterministic review",
            "kind": "deterministic",
            "configured": True,
            "model": None,
            "promptVersion": "review.v2",
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "kind": "real",
            "configured": False,
            "model": None,
            "promptVersion": "review.v2",
        },
    ]
    assert "apiKey" not in response.text


def test_openai_configuration_is_validated_stored_and_never_returned() -> None:
    settings = InMemoryProviderSettingsRepository()
    credentials = InMemoryCredentialStore()
    with TestClient(
        create_app(
            provider_settings_repository=settings,
            credential_store=credentials,
        )
    ) as client:
        invalid = client.put(
            "/api/v1/providers/openai/config",
            json={"apiKey": "short", "model": "not a valid model"},
        )
        configured = client.put(
            "/api/v1/providers/openai/config",
            json={"apiKey": "sk-test-secret-that-is-long-enough", "model": "gpt-5-mini"},
        )
        discovered = client.get("/api/v1/providers")

    assert invalid.status_code == 422
    assert invalid.json()["type"] == "urn:mensura:problem:validation-error"
    assert configured.status_code == 200
    assert configured.json() == {
        "id": "openai",
        "name": "OpenAI",
        "kind": "real",
        "configured": True,
        "model": "gpt-5-mini",
        "promptVersion": "review.v2",
    }
    assert "secret" not in configured.text
    assert credentials.openai_api_key == "sk-test-secret-that-is-long-enough"
    assert settings.settings == OpenAIProviderSettings(model="gpt-5-mini")
    assert discovered.json()["items"][1]["configured"] is True
    assert "apiKey" not in discovered.text


def test_json_settings_repository_persists_only_non_secret_model(tmp_path) -> None:
    path = tmp_path / "providers.json"
    repository = JsonProviderSettingsRepository(path)

    repository.save_openai(OpenAIProviderSettings(model="gpt-5-mini"))

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {"schemaVersion": "1", "openai": {"model": "gpt-5-mini"}}
    assert repository.get_openai() == OpenAIProviderSettings(model="gpt-5-mini")

    path.write_text('{"schemaVersion":"2","openai":{"model":"gpt-5-mini"}}')
    with pytest.raises(ProviderConfigurationStorageError):
        repository.get_openai()
