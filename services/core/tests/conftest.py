import pytest
from fastapi.testclient import TestClient

from mensura_core.main import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client
