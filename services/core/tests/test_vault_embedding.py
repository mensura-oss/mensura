"""Tests for the Vault embedding backends and the backend-selection factory.

The Ollama backend is exercised through an injected fake transport (and a monkeypatched
``httpx.post`` for the HTTP transport itself) so nothing here depends on a running daemon.
"""

import math
from collections.abc import Sequence

import httpx
import pytest

from mensura_core.vault_embedding import (
    DEFAULT_OLLAMA_MODEL,
    EMBEDDING_DIM,
    ENV_EMBEDDER,
    ENV_OLLAMA_MODEL,
    EmbeddingBackendError,
    HashingEmbedder,
    HttpxOllamaEmbeddingTransport,
    OllamaEmbedder,
    build_vault_embedder,
    cosine_similarity,
)


class FakeOllamaTransport:
    """Returns a deterministic dense vector per input and records the batch sizes it saw."""

    def __init__(self, vector: Sequence[float] = (1.0, 2.0, 2.0)) -> None:
        self._vector = list(vector)
        self.batches: list[int] = []
        self.calls = 0

    def embed(self, base_url: str, model: str, inputs: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        self.batches.append(len(inputs))
        return [list(self._vector) for _ in inputs]


class FailingOllamaTransport:
    def embed(self, base_url: str, model: str, inputs: Sequence[str]) -> list[list[float]]:
        raise EmbeddingBackendError("connection refused")


# ------------------------------------------------------------------ HashingEmbedder


def test_hashing_embedder_info_is_lexical() -> None:
    info = HashingEmbedder().info
    assert info.backend == "hashing"
    assert info.semantic is False
    assert info.dim == EMBEDDING_DIM


def test_hashing_embed_documents_matches_single_embed() -> None:
    embedder = HashingEmbedder()
    texts = ["authenticate the user", "", "render the canvas"]
    assert embedder.embed_documents(texts) == [embedder.embed(text) for text in texts]


# ------------------------------------------------------------------ OllamaEmbedder


def test_ollama_embed_normalizes_and_reports_dim() -> None:
    embedder = OllamaEmbedder(model="nomic", transport=FakeOllamaTransport((1.0, 2.0, 2.0)))
    vector = embedder.embed("some chunk text")
    # L2-normalized dense dict keyed by index-as-string: 1/3, 2/3, 2/3.
    assert set(vector) == {"0", "1", "2"}
    assert vector["0"] == pytest.approx(1 / 3)
    assert math.isclose(math.sqrt(sum(v * v for v in vector.values())), 1.0)
    # Dimensionality is discovered from the first embedding and reported honestly.
    assert embedder.info.dim == 3
    assert embedder.info.backend == "ollama"
    assert embedder.info.semantic is True


def test_ollama_self_similarity_is_one_and_orthogonal_is_zero() -> None:
    embedder = OllamaEmbedder(transport=FakeOllamaTransport())
    left = embedder.embed("anything")
    assert cosine_similarity(left, left) == pytest.approx(1.0)
    assert cosine_similarity({"0": 1.0}, {"1": 1.0}) == 0.0


def test_ollama_embed_documents_batches_calls() -> None:
    transport = FakeOllamaTransport()
    embedder = OllamaEmbedder(transport=transport, batch_size=2)
    vectors = embedder.embed_documents([f"chunk {i}" for i in range(5)])
    assert len(vectors) == 5
    assert transport.batches == [2, 2, 1]  # one HTTP call per batch, not per chunk


def test_ollama_embed_documents_empty_makes_no_call() -> None:
    transport = FakeOllamaTransport()
    assert OllamaEmbedder(transport=transport).embed_documents([]) == []
    assert transport.calls == 0


def test_ollama_transport_failure_raises_backend_error() -> None:
    embedder = OllamaEmbedder(transport=FailingOllamaTransport())
    with pytest.raises(EmbeddingBackendError):
        embedder.embed("text")


# ------------------------------------------------------ HttpxOllamaEmbeddingTransport


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_httpx_transport_posts_to_embed_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_post(url: str, *, json: dict, timeout: float) -> _FakeResponse:
        seen["url"] = url
        seen["json"] = json
        return _FakeResponse(200, {"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    monkeypatch.setattr(httpx, "post", fake_post)
    result = HttpxOllamaEmbeddingTransport().embed(
        "http://localhost:11434/", "nomic-embed-text", ["a", "b"]
    )
    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert seen["url"] == "http://localhost:11434/api/embed"
    assert seen["json"] == {"model": "nomic-embed-text", "input": ["a", "b"]}


def test_httpx_transport_maps_non_200_to_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(404, {"error": "no model"}))
    with pytest.raises(EmbeddingBackendError):
        HttpxOllamaEmbeddingTransport().embed("http://localhost:11434", "missing", ["x"])


def test_httpx_transport_maps_transport_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(EmbeddingBackendError):
        HttpxOllamaEmbeddingTransport().embed("http://localhost:11434", "m", ["x"])


def test_httpx_transport_rejects_mismatched_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(200, {"embeddings": [[0.1]]}))
    with pytest.raises(EmbeddingBackendError):
        HttpxOllamaEmbeddingTransport().embed("http://localhost:11434", "m", ["x", "y"])


# ------------------------------------------------------------------ factory


def test_factory_forced_hashing_never_probes() -> None:
    transport = FailingOllamaTransport()
    embedder = build_vault_embedder(mode="hashing", transport=transport)  # type: ignore[arg-type]
    assert isinstance(embedder, HashingEmbedder)


def test_factory_auto_uses_ollama_when_reachable() -> None:
    embedder = build_vault_embedder(mode="auto", transport=FakeOllamaTransport())
    assert isinstance(embedder, OllamaEmbedder)
    assert embedder.info.semantic is True
    assert embedder.info.dim == 3  # discovered by the probe embedding


def test_factory_auto_falls_back_to_lexical_when_unreachable() -> None:
    embedder = build_vault_embedder(mode="auto", transport=FailingOllamaTransport())
    assert isinstance(embedder, HashingEmbedder)


def test_factory_forced_ollama_still_falls_back_when_unreachable() -> None:
    # Honest degradation: requested semantic, backend down → lexical (a warning is logged).
    embedder = build_vault_embedder(mode="ollama", transport=FailingOllamaTransport())
    assert isinstance(embedder, HashingEmbedder)


def test_factory_unknown_mode_uses_lexical() -> None:
    assert isinstance(build_vault_embedder(mode="nonsense"), HashingEmbedder)


def test_factory_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EMBEDDER, "ollama")
    monkeypatch.setenv(ENV_OLLAMA_MODEL, "custom-embed")
    embedder = build_vault_embedder(transport=FakeOllamaTransport())
    assert isinstance(embedder, OllamaEmbedder)
    assert embedder.info.model == "custom-embed"


def test_factory_no_probe_returns_ollama_without_calling() -> None:
    transport = FakeOllamaTransport()
    embedder = build_vault_embedder(mode="ollama", transport=transport, probe=False)
    assert isinstance(embedder, OllamaEmbedder)
    assert transport.calls == 0
    assert DEFAULT_OLLAMA_MODEL  # default model constant is exported for docs/wiring
