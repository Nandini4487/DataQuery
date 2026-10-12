from __future__ import annotations

from pathlib import Path

import chromadb
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.embedding_service import (
    reset_embedding_function,
    set_embedding_function,
)
from app.services.retrieval_service import (
    reset_chroma_client,
    set_chroma_client,
)


@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous TestClient for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def sample_csv_text() -> str:
    """Sample acceptance dataset from SPEC section 7.6."""
    return (
        "product,city,revenue\n"
        "Laptop,Delhi,80000\n"
        "Phone,Mumbai,50000\n"
        "Laptop,Mumbai,70000\n"
        "Phone,Delhi,40000\n"
    )


@pytest.fixture()
def sample_csv_bytes(sample_csv_text: str) -> bytes:
    """Sample acceptance dataset bytes encoded in UTF-8."""
    return sample_csv_text.encode("utf-8")


@pytest.fixture()
def tmp_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temporary upload directory fixture isolated per test."""
    upload_path = tmp_path / "uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "upload_dir", str(upload_path))
    return upload_path


class FakeGenerateContentResponse:
    """Fake response mimicking google.genai GenerateContentResponse."""

    def __init__(self, text: str = "{}") -> None:
        self.text = text


class FakeModelsService:
    """Fake models service mimicking client.models."""

    def __init__(self, default_response: str = '{"operation": "count"}') -> None:
        self.default_response = default_response
        self.last_contents: str | None = None
        self.last_config: object | None = None
        self.call_count: int = 0

    def generate_content(
        self,
        model: str,
        contents: str,
        config: object | None = None,
    ) -> FakeGenerateContentResponse:
        self.call_count += 1
        self.last_contents = contents
        self.last_config = config
        return FakeGenerateContentResponse(self.default_response)


class FakeGenAIClient:
    """Fake client mimicking google.genai.Client."""

    def __init__(self, default_response: str = '{"operation": "count"}') -> None:
        self.models = FakeModelsService(default_response=default_response)


@pytest.fixture(autouse=True)
def dummy_gemini_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy GEMINI_API_KEY and GEMINI_MODEL for all tests (zero real Gemini calls)."""
    monkeypatch.setattr(settings, "gemini_api_key", "dummy-gemini-test-key")
    monkeypatch.setattr(settings, "gemini_model", "dummy-gemini-test-model")


@pytest.fixture()
def fake_llm_client(monkeypatch: pytest.MonkeyPatch) -> FakeGenAIClient:
    """Fixture providing a fake LLM client intercepted before google-genai."""
    fake = FakeGenAIClient()
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: fake)
    return fake


class DeterministicFakeEmbeddingFunction:
    """Deterministic offline fake embedding function producing 8-dimensional unit vectors."""

    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        results: list[list[float]] = []
        for text in texts:
            vec = [0.0] * 8
            for i, byte in enumerate(text.encode("utf-8")):
                vec[i % 8] += float(byte)
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0:
                vec = [round(v / norm, 6) for v in vec]
            results.append(vec)
        return results


@pytest.fixture(autouse=True)
def guard_chroma_persist_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no test ever writes into the real data/chroma directory."""
    temp_dir = tmp_path / "guard_test_chroma"
    monkeypatch.setattr(settings, "chroma_persist_directory", str(temp_dir))
    reset_chroma_client()
    yield
    reset_chroma_client()


@pytest.fixture()
def fake_embedding_fn() -> DeterministicFakeEmbeddingFunction:
    """Fixture providing an offline deterministic fake embedding function."""
    fake = DeterministicFakeEmbeddingFunction()
    set_embedding_function(fake)
    yield fake
    reset_embedding_function()


@pytest.fixture()
def temp_chroma_client(
    tmp_path: Path,
    fake_embedding_fn: DeterministicFakeEmbeddingFunction,
) -> chromadb.ClientAPI:
    """Fixture providing an isolated Chroma PersistentClient backed by a temp directory."""
    chroma_dir = tmp_path / "isolated_chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    set_chroma_client(client)
    yield client
    reset_chroma_client()

