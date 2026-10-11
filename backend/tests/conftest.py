from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


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
