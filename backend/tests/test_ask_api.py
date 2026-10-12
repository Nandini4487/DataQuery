from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.services.query_executor
from tests.conftest import FakeGenAIClient, FakeGenerateContentResponse


@pytest.fixture()
def uploaded_dataset_id(client: TestClient, sample_csv_bytes: bytes, tmp_upload_dir: Path) -> str:
    """Helper fixture to upload the SPEC 7.6 dataset and return its dataset_id."""
    res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    assert res.status_code == 201
    return res.json()["dataset_id"]


def test_ask_total_revenue_returns_240000(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    uploaded_dataset_id: str,
) -> None:
    """'What is total revenue?' with a mocked plan returns 240000 in the table."""
    plan_dict = {
        "supported": True,
        "reason": "",
        "plan": {
            "operation": "aggregate",
            "columns": ["revenue"],
            "agg": "sum",
        },
    }

    def mock_generate_content(
        model: str,
        contents: str,
        config: object | None = None,
    ) -> FakeGenerateContentResponse:
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(plan_dict))
        return FakeGenerateContentResponse("The total revenue across all sales is 240000.")

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "What is total revenue?"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["table"]["rows"][0]["revenue"] == 240000
    assert data["computed_by_engine"] is True
    assert data["explanation_is_fallback"] is False
    assert "240000" in data["answer_text"]


def test_ask_highest_revenue_product_returns_laptop(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    uploaded_dataset_id: str,
) -> None:
    """'highest revenue product' returns Laptop."""
    plan_dict = {
        "supported": True,
        "reason": "",
        "plan": {
            "operation": "group_by",
            "group_by": ["product"],
            "columns": ["revenue"],
            "agg": "sum",
            "sort": {"column": "revenue", "direction": "desc"},
            "limit": 1,
        },
    }

    def mock_generate_content(
        model: str,
        contents: str,
        config: object | None = None,
    ) -> FakeGenerateContentResponse:
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(plan_dict))
        return FakeGenerateContentResponse("The highest revenue product is Laptop with 150000 in sales.")

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "highest revenue product"},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data["table"]["rows"]) == 1
    assert data["table"]["rows"][0]["product"] == "Laptop"
    assert data["table"]["rows"][0]["revenue"] == 150000
    assert data["computed_by_engine"] is True
    assert data["explanation_is_fallback"] is False
    assert "Laptop" in data["answer_text"]


def test_ask_mocked_supported_false_returns_422_unsupported_question(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    uploaded_dataset_id: str,
) -> None:
    """Mocked supported=false returns 422 with error unsupported_question and the model reason."""
    reason_msg = "Predicting future revenue is not supported by the query engine."
    unsupported_dict = {
        "supported": False,
        "reason": reason_msg,
        "plan": None,
    }

    fake_llm_client.models.generate_content = lambda model, contents, config=None: FakeGenerateContentResponse(
        json.dumps(unsupported_dict)
    )

    res = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "Predict future revenue for 2030"},
    )

    assert res.status_code == 422
    body = res.json()
    assert body["error"] == "unsupported_question"
    assert body["message"] == reason_msg


def test_ask_mocked_plan_with_unknown_column_returns_422_invalid_plan_and_no_executor(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    uploaded_dataset_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mocked plan with unknown column returns 422 invalid_plan and executor is never called."""
    bad_plan = {
        "supported": True,
        "reason": "",
        "plan": {
            "operation": "aggregate",
            "columns": ["nonexistent_margin"],
            "agg": "sum",
        },
    }

    fake_llm_client.models.generate_content = lambda model, contents, config=None: FakeGenerateContentResponse(
        json.dumps(bad_plan)
    )

    executor_called = False
    original_execute_query = app.services.query_executor.execute_query

    def spy_execute_query(*args: Any, **kwargs: Any) -> Any:
        nonlocal executor_called
        executor_called = True
        return original_execute_query(*args, **kwargs)

    monkeypatch.setattr(app.services.query_executor, "execute_query", spy_execute_query)

    res = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "What is total margin?"},
    )

    assert res.status_code == 422
    body = res.json()
    assert body["error"] == "invalid_plan"
    assert "invalid" in body["message"].lower() or "disallowed" in body["message"].lower()
    assert executor_called is False


def test_ask_mocked_planner_timeout_returns_503_provider_unavailable(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    uploaded_dataset_id: str,
) -> None:
    """Mocked planner timeout returns 503 provider_unavailable."""

    def mock_timeout(model: str, contents: str, config: object | None = None) -> FakeGenerateContentResponse:
        raise TimeoutError("Gemini call timed out after 20 seconds.")

    fake_llm_client.models.generate_content = mock_timeout

    res = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "What is total revenue?"},
    )

    assert res.status_code == 503
    body = res.json()
    assert body["error"] == "provider_unavailable"
    assert "unavailable" in body["message"].lower()


def test_ask_mocked_answer_service_failure_returns_200_with_fallback(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    uploaded_dataset_id: str,
) -> None:
    """Mocked answer-service failure still returns 200 with fallback explanation and computed table."""
    plan_dict = {
        "supported": True,
        "reason": "",
        "plan": {
            "operation": "aggregate",
            "columns": ["revenue"],
            "agg": "sum",
        },
    }

    def mock_content_flow(
        model: str,
        contents: str,
        config: object | None = None,
    ) -> FakeGenerateContentResponse:
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(plan_dict))
        # Answer service explanation call fails
        raise TimeoutError("Explanation model call timed out.")

    fake_llm_client.models.generate_content = mock_content_flow

    res = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "What is total revenue?"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["table"]["rows"][0]["revenue"] == 240000
    assert data["computed_by_engine"] is True
    assert data["explanation_is_fallback"] is True
    assert "The result has 1 row. See the table." in data["answer_text"]


def test_ask_empty_question_returns_422(
    client: TestClient,
    uploaded_dataset_id: str,
) -> None:
    """Empty question returns 422."""
    res_empty = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": ""},
    )
    assert res_empty.status_code == 422

    res_spaces = client.post(
        f"/api/datasets/{uploaded_dataset_id}/ask",
        json={"question": "    "},
    )
    assert res_spaces.status_code == 422


def test_ask_unknown_dataset_returns_standard_error(
    client: TestClient,
) -> None:
    """Unknown dataset returns 404 standard error."""
    nonexistent_id = str(uuid.uuid4())
    res = client.post(
        f"/api/datasets/{nonexistent_id}/ask",
        json={"question": "What is total revenue?"},
    )

    assert res.status_code == 404
    body = res.json()
    assert body["error"] == "not_found"
    assert nonexistent_id in body["message"]
