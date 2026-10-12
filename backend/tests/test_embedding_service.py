from __future__ import annotations

import pytest

import app.services.embedding_service as es
from app.services.embedding_service import (
    EmbeddingError,
    embed_query,
    embed_texts,
    reset_embedding_function,
    set_embedding_function,
)


def test_fake_function_used_when_injected() -> None:
    """When a custom embedding function is injected, it is used for embedding."""
    calls: list[list[str]] = []

    def mock_ef(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[1.0, 2.0, 3.0] for _ in texts]

    set_embedding_function(mock_ef)
    try:
        embeddings = embed_texts(["alpha", "beta"])
        assert len(embeddings) == 2
        assert embeddings[0] == [1.0, 2.0, 3.0]
        assert calls == [["alpha", "beta"]]

        query_emb = embed_query("search text")
        assert query_emb == [1.0, 2.0, 3.0]
        assert calls[-1] == ["search text"]
    finally:
        reset_embedding_function()


def test_empty_list_returns_empty_without_calling_model() -> None:
    """An empty input list must immediately return empty without invoking the model."""
    called = False

    def explode_if_called(texts: list[str]) -> list[list[float]]:
        nonlocal called
        called = True
        raise AssertionError("Embedding model should never be called for empty input!")

    set_embedding_function(explode_if_called)
    try:
        result = embed_texts([])
        assert result == []
        assert not called
    finally:
        reset_embedding_function()


def test_import_and_service_creation_does_not_load_real_model() -> None:
    """Importing the module must not eagerly load Chroma's DefaultEmbeddingFunction."""
    # Ensure default embedding function instance remains unloaded
    assert es._default_embedding_fn is None


def test_model_failure_becomes_embedding_error_with_safe_message() -> None:
    """Underlying exceptions must become EmbeddingError with a safe message and no paths."""

    def failing_ef(texts: list[str]) -> list[list[float]]:
        raise RuntimeError("CRITICAL: C:\\Windows\\System32\\driver.sys memory leak at 0xDEADBEEF")

    set_embedding_function(failing_ef)
    try:
        with pytest.raises(EmbeddingError) as exc_info:
            embed_texts(["sample text"])

        err = exc_info.value
        assert "driver.sys" not in err.message
        assert "0xDEADBEEF" not in err.message
        assert "C:\\" not in err.message
        assert err.message == "Failed to generate text embeddings."
        assert err.to_dict() == {
            "error": "embedding_error",
            "message": "Failed to generate text embeddings.",
        }
    finally:
        reset_embedding_function()
