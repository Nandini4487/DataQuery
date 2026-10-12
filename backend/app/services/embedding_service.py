from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when text embedding fails or the model cannot be loaded."""

    def __init__(
        self,
        message: str = "Failed to generate text embeddings.",
        error_code: str = "embedding_error",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def to_dict(self) -> dict[str, str]:
        """Return the standard error shape {"error", "message"}."""
        return {"error": self.error_code, "message": self.message}


# Global injected embedding function (e.g. for deterministic unit tests)
_injected_embedding_fn: Callable[[list[str]], list[list[float]]] | None = None
# Lazily loaded default embedding function instance
_default_embedding_fn: Any = None


def set_embedding_function(
    fn: Callable[[list[str]], list[list[float]]] | None,
) -> None:
    """Inject a custom embedding function (e.g. for deterministic testing)."""
    global _injected_embedding_fn
    _injected_embedding_fn = fn


def get_embedding_function() -> Callable[[list[str]], list[list[float]]] | None:
    """Return the currently injected embedding function, if any."""
    return _injected_embedding_fn


def reset_embedding_function() -> None:
    """Reset to the default lazy-loaded provider."""
    global _injected_embedding_fn
    _injected_embedding_fn = None


def _get_active_provider() -> Any:
    """Resolve the active embedding provider.

    Returns the injected function if present; otherwise lazily initializes
    ChromaDB's DefaultEmbeddingFunction (local ONNX all-MiniLM-L6-v2).
    """
    global _default_embedding_fn

    if _injected_embedding_fn is not None:
        return _injected_embedding_fn

    if _default_embedding_fn is not None:
        return _default_embedding_fn

    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        _default_embedding_fn = DefaultEmbeddingFunction()
        return _default_embedding_fn
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialize default embedding function: %s", type(exc).__name__)
        # Ensure safe message with no stack traces or file paths
        raise EmbeddingError("Failed to initialize embedding model. Please check local environment.") from None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate vector embeddings for a list of texts.

    Handles empty input lists immediately without loading or calling the model.
    """
    if not texts:
        return []

    provider = _get_active_provider()
    try:
        raw_embeddings = provider(texts)
        # Standardize return format to list[list[float]]
        converted: list[list[float]] = []
        for emb in raw_embeddings:
            if hasattr(emb, "tolist"):
                converted.append([float(x) for x in emb.tolist()])
            elif hasattr(emb, "__iter__"):
                converted.append([float(x) for x in emb])
            else:
                converted.append([float(emb)])
        return converted
    except EmbeddingError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Embedding generation failed: %s", type(exc).__name__)
        # Safe message with no internal paths or stack trace
        raise EmbeddingError("Failed to generate text embeddings.") from None


def embed_query(query: str) -> list[float]:
    """Generate vector embedding for a single search query."""
    if not isinstance(query, str):
        raise EmbeddingError("Search query must be a string.")

    results = embed_texts([query])
    if not results:
        return []
    return results[0]
