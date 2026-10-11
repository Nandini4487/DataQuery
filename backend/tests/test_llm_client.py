from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.services.llm_client import (
    LLMUnavailableError,
    generate_json,
    generate_text,
)


class MockContentResponse:
    """Mock Gemini response object."""

    def __init__(self, text: str) -> None:
        self.text = text


class MockModelsService:
    """Mock models service with configurable responses and side effects."""

    def __init__(self, side_effect: Any = None, text: str = "{}") -> None:
        self.side_effect = side_effect
        self.text = text
        self.call_count = 0
        self.last_contents = None
        self.last_config = None

    def generate_content(
        self,
        model: str,
        contents: str,
        config: Any = None,
    ) -> MockContentResponse:
        self.call_count += 1
        self.last_contents = contents
        self.last_config = config

        if callable(self.side_effect):
            res = self.side_effect()
            if isinstance(res, Exception):
                raise res
            return MockContentResponse(res)
        if isinstance(self.side_effect, Exception):
            raise self.side_effect
        if isinstance(self.side_effect, list):
            item = self.side_effect.pop(0)
            if isinstance(item, Exception):
                raise item
            return MockContentResponse(item)
        return MockContentResponse(self.text)


class MockClient:
    """Mock google.genai.Client."""

    def __init__(self, models: MockModelsService) -> None:
        self.models = models


def test_generate_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful generate_json returns parsed dictionary."""
    mock_models = MockModelsService(text='{"operation": "filter", "columns": ["revenue"]}')
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    result = generate_json("system instructions", "user prompt")
    assert result == {"operation": "filter", "columns": ["revenue"]}
    assert mock_models.call_count == 1


def test_generate_json_with_markdown_fences(monkeypatch: pytest.MonkeyPatch) -> None:
    """generate_json handles markdown code fences in response."""
    mock_models = MockModelsService(text='```json\n{"operation": "count", "columns": []}\n```')
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    result = generate_json("system instructions", "user prompt")
    assert result == {"operation": "count", "columns": []}


def test_generate_text_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful generate_text returns clean string."""
    mock_models = MockModelsService(text="Total revenue across all products is 240,000.")
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    result = generate_text("system instructions", "user prompt")
    assert result == "Total revenue across all products is 240,000."
    assert mock_models.call_count == 1


def test_timeout_becomes_llm_unavailable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout exceptions from provider or transport convert to LLMUnavailableError."""
    req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    timeout_exc = httpx.ReadTimeout("Connection timed out", request=req)
    mock_models = MockModelsService(side_effect=timeout_exc)
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    with pytest.raises(LLMUnavailableError) as exc_info:
        generate_json("sys", "user")

    assert "timed out" in str(exc_info.value).lower()


def test_missing_model_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing GEMINI_MODEL raises LLMUnavailableError with a clear message."""
    monkeypatch.setattr(settings, "gemini_model", "")

    with pytest.raises(LLMUnavailableError) as exc_info:
        generate_json("sys", "user")

    assert "GEMINI_MODEL is required" in str(exc_info.value)


def test_missing_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing GEMINI_API_KEY raises LLMUnavailableError with a clear message."""
    monkeypatch.setattr(settings, "gemini_api_key", "")

    with pytest.raises(LLMUnavailableError) as exc_info:
        generate_json("sys", "user")

    assert "GEMINI_API_KEY is required" in str(exc_info.value)


def test_error_message_never_contains_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error messages must never leak the API key even if the provider includes it."""
    secret_key = "AIzaSy-super-secret-token-do-not-leak"
    monkeypatch.setattr(settings, "gemini_api_key", secret_key)

    leaking_error = RuntimeError(f"Authentication failed for key {secret_key}: invalid token")
    mock_models = MockModelsService(side_effect=leaking_error)
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    with pytest.raises(LLMUnavailableError) as exc_info:
        generate_json("sys", "user")

    error_message = str(exc_info.value)
    assert secret_key not in error_message
    assert "[REDACTED]" not in error_message or secret_key not in error_message
    assert "LLM authentication failed" in error_message


def test_retry_on_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transient failures trigger a retry up to llm_max_retries."""
    monkeypatch.setattr(settings, "llm_max_retries", 1)
    req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    timeout_exc = httpx.ReadTimeout("Timeout on first attempt", request=req)

    # First attempt fails with timeout, second succeeds
    side_effects = [timeout_exc, '{"operation": "aggregate", "agg": "sum"}']
    mock_models = MockModelsService(side_effect=side_effects)
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    result = generate_json("sys", "user")
    assert result == {"operation": "aggregate", "agg": "sum"}
    assert mock_models.call_count == 2


def test_invalid_json_raises_llm_unavailable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid JSON output from model raises safe LLMUnavailableError."""
    mock_models = MockModelsService(text="This is plain text, not JSON.")
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: MockClient(mock_models))

    with pytest.raises(LLMUnavailableError) as exc_info:
        generate_json("sys", "user")

    assert "JSON" in str(exc_info.value)
