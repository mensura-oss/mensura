"""Vault embedding backends behind a single ``Embedder`` protocol.

Two backends implement the same protocol and return the same shape, so the schema, the
persistence rows, and the cosine ranking are all backend-agnostic:

- :class:`HashingEmbedder` — a deterministic, dependency-free **lexical** term-frequency
  hashing vectorizer (unigrams + bigrams hashed with ``blake2b`` into a fixed number of
  buckets, L2-normalized). Fully offline and reproducible across restarts, but lexical,
  not semantic.
- :class:`OllamaEmbedder` — a real **local neural** embedding model served by a local
  Ollama daemon over HTTP (``httpx``, already a Core dependency; no cloud). Vectors are
  L2-normalized and stored in the same sparse-dict shape.

Both ``embed`` calls return ``dict[str, float]`` — an L2-normalized vector keyed by a
string bucket/index — so :func:`cosine_similarity` is a plain sparse dot product and the
JSON ``vault_chunks.embedding`` column is untouched by the switch to real embeddings. A
dense embedding is simply a fully-populated dict (``{"0": v0, …, "767": v767}``).

:func:`build_vault_embedder` selects a backend from environment configuration and falls
back to the lexical embedder — with a clear logged reason — when the Ollama backend is
unavailable, so the product never silently pretends semantic embeddings are active.
"""

import hashlib
import logging
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from os import environ
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

# Hashing dimensionality. Sized generously so the sparse inverted index used for sub-linear
# search (see ``vault_index_repositories``) is *selective*: a chunk's non-zero bucket count is
# bounded by its distinct tokens (tens to low hundreds) regardless of this value, so a larger
# space costs no extra storage but sharply cuts hash collisions — turning "shares a query
# bucket" from "most chunks" (at 512, collisions dominate) into a small candidate set, while
# also improving lexical discrimination. Changing it changes the lexical vector space, so an
# index built at a different value reports a re-index (see ``_index_is_compatible``).
EMBEDDING_DIM = 16384

HASHING_BACKEND = "hashing"
OLLAMA_BACKEND = "ollama"

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "nomic-embed-text"
OLLAMA_EMBED_TIMEOUT_SECONDS = 60.0
OLLAMA_BATCH_SIZE = 64

ENV_EMBEDDER = "MENSURA_VAULT_EMBEDDER"
ENV_OLLAMA_URL = "MENSURA_OLLAMA_URL"
ENV_OLLAMA_MODEL = "MENSURA_OLLAMA_EMBED_MODEL"

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass(frozen=True, slots=True)
class EmbedderInfo:
    """Identity of the backend that produced a set of vectors.

    Persisted alongside an index (in its summary) so search can tell whether the currently
    configured embedder produces vectors in the *same* space as the stored ones. ``semantic``
    is ``True`` only for real neural embeddings, so callers can be honest about the mode.
    """

    backend: str
    model: str
    dim: int
    semantic: bool

    def matches(self, other: "EmbedderInfo") -> bool:
        """Same vector space (safe to compare a stored vector against a fresh query vector)."""
        return (self.backend, self.model, self.dim) == (other.backend, other.model, other.dim)


class Embedder(Protocol):
    @property
    def info(self) -> EmbedderInfo: ...

    def embed(self, text: str) -> dict[str, float]: ...

    def embed_documents(self, texts: Sequence[str]) -> list[dict[str, float]]: ...


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _bucket(token: str, dim: int) -> str:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return str(int.from_bytes(digest, "big") % dim)


def _l2_normalize(weights: Mapping[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in weights.values()))
    if norm == 0.0:
        return {}
    return {key: value / norm for key, value in weights.items()}


class HashingEmbedder:
    """Deterministic term-frequency hashing vectorizer over unigrams + bigrams (lexical).

    Uses ``blake2b`` (not Python's per-process-salted ``hash()``) so vectors persisted in one
    process match those computed for a query in another — search survives restarts.
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._dim = dim
        self._info = EmbedderInfo(
            backend=HASHING_BACKEND, model=f"blake2b-tf-{dim}", dim=dim, semantic=False
        )

    @property
    def info(self) -> EmbedderInfo:
        return self._info

    def embed(self, text: str) -> dict[str, float]:
        tokens = tokenize(text)
        if not tokens:
            return {}
        counts: Counter[str] = Counter()
        for token in tokens:
            counts[_bucket(token, self._dim)] += 1.0
        for first, second in pairwise(tokens):
            counts[_bucket(f"{first}\x1f{second}", self._dim)] += 1.0
        return _l2_normalize(counts)

    def embed_documents(self, texts: Sequence[str]) -> list[dict[str, float]]:
        return [self.embed(text) for text in texts]


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    """Dot product of two L2-normalized sparse vectors (== cosine similarity)."""
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(bucket, 0.0) for bucket, weight in left.items())


class EmbeddingBackendError(RuntimeError):
    """The configured embedding backend could not produce a vector (unreachable/failed)."""


class OllamaEmbeddingTransport(Protocol):
    def embed(self, base_url: str, model: str, inputs: Sequence[str]) -> list[list[float]]: ...


class HttpxOllamaEmbeddingTransport:
    """Calls a local Ollama daemon's ``/api/embed`` endpoint. Localhost by default; no cloud."""

    def embed(self, base_url: str, model: str, inputs: Sequence[str]) -> list[list[float]]:
        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/api/embed",
                json={"model": model, "input": list(inputs)},
                timeout=OLLAMA_EMBED_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise EmbeddingBackendError(f"Ollama request failed: {error}") from error
        if response.status_code != 200:
            raise EmbeddingBackendError(
                f"Ollama returned HTTP {response.status_code} for model '{model}'"
            )
        try:
            body: Any = response.json()
        except ValueError as error:
            raise EmbeddingBackendError("Ollama returned a non-JSON body") from error
        embeddings = body.get("embeddings") if isinstance(body, dict) else None
        if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
            raise EmbeddingBackendError("Ollama response did not contain one embedding per input")
        return embeddings


class OllamaEmbedder:
    """Real local neural embeddings via a local Ollama daemon, in the shared sparse-dict shape.

    Dense vectors are L2-normalized and keyed by their index as strings, so they persist and
    rank through the exact same path as the lexical vectors. ``embed_documents`` batches inputs
    into one HTTP call per :data:`OLLAMA_BATCH_SIZE` chunk. The vector dimensionality is
    discovered from the first successful embedding and then reported in :attr:`info`.
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_URL,
        transport: OllamaEmbeddingTransport | None = None,
        dim: int | None = None,
        batch_size: int = OLLAMA_BATCH_SIZE,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._transport = transport or HttpxOllamaEmbeddingTransport()
        self._dim = dim
        self._batch_size = max(1, batch_size)

    @property
    def info(self) -> EmbedderInfo:
        return EmbedderInfo(
            backend=OLLAMA_BACKEND, model=self._model, dim=self._dim or 0, semantic=True
        )

    def embed(self, text: str) -> dict[str, float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[dict[str, float]]:
        texts = list(texts)
        if not texts:
            return []
        vectors: list[dict[str, float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            raw = self._transport.embed(self._base_url, self._model, batch)
            vectors.extend(self._to_sparse(vector) for vector in raw)
        return vectors

    def _to_sparse(self, vector: Sequence[float]) -> dict[str, float]:
        if self._dim is None:
            self._dim = len(vector)
        return _l2_normalize({str(index): float(value) for index, value in enumerate(vector)})


def build_vault_embedder(
    *,
    mode: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    transport: OllamaEmbeddingTransport | None = None,
    probe: bool = True,
) -> Embedder:
    """Select a Vault embedding backend from configuration, honestly falling back to lexical.

    ``mode`` (env ``MENSURA_VAULT_EMBEDDER``): ``auto`` (default — use Ollama when reachable,
    else the lexical hashing embedder), ``ollama`` (require Ollama; still fall back to lexical
    if unavailable, but log a warning telling the operator how to set it up), or ``hashing``
    (force the offline lexical embedder, no probe/network). When ``probe`` is set, the Ollama
    backend is exercised once so an unreachable daemon or unpulled model is detected up front
    and the returned embedder's :attr:`~OllamaEmbedder.info` carries the discovered dimension.
    """
    mode = (mode or environ.get(ENV_EMBEDDER, "auto")).strip().lower()
    base_url = base_url or environ.get(ENV_OLLAMA_URL, DEFAULT_OLLAMA_URL)
    model = model or environ.get(ENV_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL)

    if mode == HASHING_BACKEND:
        return HashingEmbedder()
    if mode not in ("auto", OLLAMA_BACKEND):
        logger.warning("Unknown %s=%r; using the lexical hashing embedder.", ENV_EMBEDDER, mode)
        return HashingEmbedder()

    ollama = OllamaEmbedder(model=model, base_url=base_url, transport=transport)
    if not probe:
        return ollama
    try:
        ollama.embed("mensura vault embedding probe")
    except EmbeddingBackendError as error:
        if mode == OLLAMA_BACKEND:
            logger.warning(
                "%s=ollama but the Ollama backend at %s (model %r) is unavailable (%s); "
                "falling back to the offline lexical hashing embedder. Start Ollama and run "
                "`ollama pull %s`, then re-index for semantic search.",
                ENV_EMBEDDER,
                base_url,
                model,
                error,
                model,
            )
        else:
            logger.info(
                "Ollama embedding backend unavailable at %s (%s); using the offline lexical "
                "hashing embedder. Install/start Ollama and run `ollama pull %s` for semantic "
                "Vault search.",
                base_url,
                error,
                model,
            )
        return HashingEmbedder()
    return ollama
