from __future__ import annotations

import pytest

from app.schemas.query import AnalysisPlan
from app.services.answer_service import (
    MAX_RESULT_ROWS_FOR_EXPLANATION,
    SYSTEM_PROMPT,
    explain,
)
from app.services.llm_client import LLMUnavailableError
from app.services.query_router import classify_question


def test_prompt_contains_only_truncated_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that a 100-row result is truncated to at most 20 rows before reaching the LLM."""
    captured_prompt: dict[str, str] = {}

    def mock_generate_text(system_prompt: str, user_content: str) -> str:
        captured_prompt["system_prompt"] = system_prompt
        captured_prompt["user_content"] = user_content
        return "Total 100 items computed, showing sample in table."

    monkeypatch.setattr("app.services.answer_service.generate_text", mock_generate_text)

    # 100 rows
    rows_100 = [{"row_id": f"row_{i:03d}", "val": i * 10} for i in range(100)]
    result_data = {
        "columns": ["row_id", "val"],
        "rows": rows_100,
        "row_count": 100,
    }
    plan = AnalysisPlan(operation="count")

    explanation = explain(
        question="Show me all rows",
        plan=plan,
        result=result_data,
    )

    assert explanation == "Total 100 items computed, showing sample in table."
    assert explanation.is_fallback is False

    user_content = captured_prompt["user_content"]

    # Verify first 20 rows (0..19) are present
    assert "row_000" in user_content
    assert "row_019" in user_content

    # Verify row 20 and beyond are NOT present
    assert "row_020" not in user_content
    assert "row_050" not in user_content
    assert "row_099" not in user_content
    assert MAX_RESULT_ROWS_FOR_EXPLANATION == 20


def test_empty_result_gives_sensible_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that when query result is empty, the LLM is prompted and returns a sensible message."""
    captured_prompt: dict[str, str] = {}

    def mock_generate_text(system_prompt: str, user_content: str) -> str:
        captured_prompt["system_prompt"] = system_prompt
        captured_prompt["user_content"] = user_content
        return "No matching records were found for this query."

    monkeypatch.setattr("app.services.answer_service.generate_text", mock_generate_text)

    empty_result = {
        "columns": ["product", "revenue"],
        "rows": [],
        "row_count": 0,
    }
    plan = AnalysisPlan(operation="filter", columns=["product"], filters=[])

    explanation = explain(
        question="Find sales for nonexistent product",
        plan=plan,
        result=empty_result,
    )

    assert explanation == "No matching records were found for this query."
    assert explanation.is_fallback is False
    assert "empty" in captured_prompt["system_prompt"].lower()


def test_empty_result_fallback_when_llm_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the LLM fails on an empty result, deterministic fallback provides a sensible message."""

    def mock_generate_text(system_prompt: str, user_content: str) -> str:
        raise LLMUnavailableError("Service unavailable.")

    monkeypatch.setattr("app.services.answer_service.generate_text", mock_generate_text)

    empty_result = {
        "columns": ["product", "revenue"],
        "rows": [],
        "row_count": 0,
    }
    plan = AnalysisPlan(operation="filter")

    explanation = explain(
        question="Find sales for nonexistent product",
        plan=plan,
        result=empty_result,
    )

    assert explanation == "The query returned 0 rows. No matching data was found."
    assert explanation.is_fallback is True


def test_llm_failure_returns_fallback_text_instead_of_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When LLM generation fails, explain() must return a deterministic fallback rather than raise."""

    def mock_generate_text(system_prompt: str, user_content: str) -> str:
        raise LLMUnavailableError("Quota exceeded or connection timed out.")

    monkeypatch.setattr("app.services.answer_service.generate_text", mock_generate_text)

    result_3_rows = {
        "columns": ["product", "revenue"],
        "rows": [
            {"product": "Laptop", "revenue": 1000},
            {"product": "Phone", "revenue": 2000},
            {"product": "Tablet", "revenue": 3000},
        ],
        "row_count": 3,
    }
    plan = AnalysisPlan(operation="group_by", group_by=["product"])

    explanation = explain(
        question="What is the revenue per product?",
        plan=plan,
        result=result_3_rows,
    )

    # Must return fallback text and not raise an exception
    assert explanation == "The result has 3 rows. See the table."
    assert explanation.is_fallback is True


def test_llm_empty_response_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the LLM returns an empty string or whitespace, fallback is used."""

    def mock_generate_text(system_prompt: str, user_content: str) -> str:
        return "   \n  "

    monkeypatch.setattr("app.services.answer_service.generate_text", mock_generate_text)

    result_1_row = {
        "columns": ["revenue"],
        "rows": [{"revenue": 240000}],
        "row_count": 1,
    }
    plan = AnalysisPlan(operation="aggregate", columns=["revenue"], agg="sum")

    explanation = explain(
        question="What is total revenue?",
        plan=plan,
        result=result_1_row,
    )

    assert explanation == "The result has 1 row. See the table."
    assert explanation.is_fallback is True


def test_system_prompt_contains_required_guardrails() -> None:
    """The system prompt must enforce grounding, no predictions, and plain empty handling."""
    prompt_lower = SYSTEM_PROMPT.lower()
    assert "only the numbers" in prompt_lower or "only" in prompt_lower
    assert "outside facts" in prompt_lower
    assert "empty" in prompt_lower
    assert "prediction" in prompt_lower
    assert "untrusted data" in prompt_lower


def test_query_router_stub() -> None:
    """The query router stub always returns 'structured' in Phase 2."""
    assert classify_question("What is total revenue?", "dataset-123") == "structured"
    assert classify_question("What does policy say about expenses?", "dataset-456") == "structured"
    assert classify_question("Random query") == "structured"
