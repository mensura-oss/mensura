"""Deterministic test doubles for the Vault embedding backends.

These stand in for a real local neural embedder (Ollama) so the suite never depends on a
running daemon (per the cycle's testing constraint). ``FakeSemanticEmbedder`` maps text into
a tiny concept space so we can prove the *semantic* ranking path — a query and a document that
share a concept but NO tokens still rank together, which the lexical embedder cannot do.
"""

from collections.abc import Sequence

from mensura_core.vault_embedding import EmbedderInfo, EmbeddingBackendError, tokenize


class FakeSemanticEmbedder:
    """A dense embedder that assigns each text a one-hot vector over a fixed concept space.

    Concept membership is keyword-based, so semantically-related text with different vocabulary
    (e.g. the query ``"sign in"`` and a file that says ``authenticate``/``password``) lands in
    the same concept and scores cosine ``1.0`` — the semantic win a lexical model misses.
    """

    DIM = 3
    _CONCEPTS: tuple[tuple[str, ...], ...] = (
        (
            "authenticate",
            "authentication",
            "login",
            "logout",
            "password",
            "credential",
            "credentials",
            "signin",
            "sign",
            "session",
            "token",
            "verify",
            "verification",
            "user",
            "username",
        ),
        ("render", "canvas", "pixel", "pixels", "draw", "graphics", "viewport"),
    )

    @property
    def info(self) -> EmbedderInfo:
        return EmbedderInfo(backend="ollama", model="fake-semantic", dim=self.DIM, semantic=True)

    def embed(self, text: str) -> dict[str, float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[dict[str, float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> dict[str, float]:
        tokens = set(tokenize(text))
        for index, keywords in enumerate(self._CONCEPTS):
            if tokens & set(keywords):
                return {str(index): 1.0}
        return {str(len(self._CONCEPTS)): 1.0}  # the "other" concept


class BrokenEmbedder:
    """A semantic embedder whose backend is always unavailable (raises on every call)."""

    @property
    def info(self) -> EmbedderInfo:
        return EmbedderInfo(backend="ollama", model="unreachable-model", dim=0, semantic=True)

    def embed(self, text: str) -> dict[str, float]:
        raise EmbeddingBackendError("backend is down")

    def embed_documents(self, texts: Sequence[str]) -> list[dict[str, float]]:
        raise EmbeddingBackendError("backend is down")
