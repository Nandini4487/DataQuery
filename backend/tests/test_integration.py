import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.file_service import get_dataset_dir
from app.services.retrieval_service import (
    get_chunks_collection,
    reset_chroma_client,
    retrieve,
)
from tests.conftest import (
    DeterministicFakeEmbeddingFunction,
    FakeGenAIClient,
    FakeGenerateContentResponse,
)


def _make_mock_generate_content(current_plan: dict[str, Any]) -> Any:
    def mock_generate_content(
        model: str,
        contents: str,
        config: object = None,
    ) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(current_plan))
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "structured", "reason": "Pure numerical calculation"}')
        return FakeGenerateContentResponse("The calculated result matches the computed table.")

    return mock_generate_content


def test_spec_acceptance_dataset_all_calculations(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """SPEC 7.3 & 7.6: Upload sample dataset and verify all expected computed values.

    Expected values from SPEC 7.6:
    - total revenue = 240000
    - Laptop revenue = 150000
    - Phone revenue = 90000
    - highest-revenue product = Laptop
    - row count = 4
    """
    # 1. Upload SPEC 7.6 dataset
    res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    assert res.status_code == 201
    dataset_id = res.json()["dataset_id"]

    # Test cases mapping questions to deterministic plans and expected values
    test_cases = [
        (
            "What is total revenue?",
            {
                "supported": True,
                "reason": "",
                "plan": {
                    "operation": "aggregate",
                    "columns": ["revenue"],
                    "agg": "sum",
                },
            },
            lambda table: table["rows"][0]["revenue"] == 240000,
        ),
        (
            "What is total revenue for Laptop?",
            {
                "supported": True,
                "reason": "",
                "plan": {
                    "operation": "aggregate",
                    "columns": ["revenue"],
                    "filters": [{"column": "product", "operator": "eq", "value": "Laptop"}],
                    "agg": "sum",
                },
            },
            lambda table: table["rows"][0]["revenue"] == 150000,
        ),
        (
            "What is total revenue for Phone?",
            {
                "supported": True,
                "reason": "",
                "plan": {
                    "operation": "aggregate",
                    "columns": ["revenue"],
                    "filters": [{"column": "product", "operator": "eq", "value": "Phone"}],
                    "agg": "sum",
                },
            },
            lambda table: table["rows"][0]["revenue"] == 90000,
        ),
        (
            "Which product has the highest revenue?",
            {
                "supported": True,
                "reason": "",
                "plan": {
                    "operation": "top_n",
                    "group_by": ["product"],
                    "columns": ["revenue"],
                    "agg": "sum",
                    "limit": 1,
                },
            },
            lambda table: table["rows"][0]["product"] == "Laptop" and table["rows"][0]["revenue"] == 150000,
        ),
        (
            "How many rows are in the dataset?",
            {
                "supported": True,
                "reason": "",
                "plan": {
                    "operation": "count",
                },
            },
            lambda table: table["rows"][0]["count"] == 4,
        ),
    ]

    for question, plan_dict, validator in test_cases:
        fake_llm_client.models.generate_content = _make_mock_generate_content(plan_dict)

        ask_res = client.post(
            f"/api/datasets/{dataset_id}/ask",
            json={"question": question},
        )
        assert ask_res.status_code == 200
        body = ask_res.json()
        assert body["route"] == "structured"
        assert body["computed_by_engine"] is True
        assert validator(body["table"]), f"Validation failed for question '{question}' with table {body['table']}"


def test_full_document_flow(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """SPEC 7.3: Full document flow: upload CSV, upload TXT with known fact, ask document question, assert citation."""
    # 1. Upload CSV
    csv_res = client.post(
        "/api/datasets",
        files={"file": ("dataset.csv", sample_csv_bytes, "text/csv")},
    )
    assert csv_res.status_code == 201
    dataset_id = csv_res.json()["dataset_id"]

    # 2. Upload TXT with a known fact
    doc_fact = "Enterprise refund requests must be filed within 30 days of invoice generation."
    doc_res = client.post(
        f"/api/datasets/{dataset_id}/documents",
        files={"file": ("policy.txt", doc_fact.encode("utf-8"), "text/plain")},
    )
    assert doc_res.status_code == 201
    doc_meta = doc_res.json()
    assert doc_meta["filename"] == "policy.txt"
    assert doc_meta["status"] == "indexed"

    # 3. Ask question routed to document
    def mock_generate_content(
        model: str,
        contents: str,
        config: object = None,
    ) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "document", "reason": "Requires policy documentation"}')
        if "document analysis assistant" in system_inst:
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "Refund requests must be filed within 30 days.",
                    "used_passages": [1],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    ask_res = client.post(
        f"/api/datasets/{dataset_id}/ask",
        json={"question": "What is the refund request window?"},
    )
    assert ask_res.status_code == 200
    body = ask_res.json()
    assert body["route"] == "document"
    assert "30 days" in body["answer_text"]
    assert len(body["citations"]) == 1

    citation = body["citations"][0]
    assert citation["filename"] == "policy.txt"
    assert citation["page_number"] == 1
    assert "30 days" in citation["snippet"]
    assert citation["document_id"] == doc_meta["id"]


def test_delete_cascade(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """SPEC 7.1 & 7.3: Deleting a dataset removes all files, metadata, and Chroma vectors."""
    # 1. Upload CSV
    csv_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    assert csv_res.status_code == 201
    dataset_id = csv_res.json()["dataset_id"]

    # 2. Upload document
    doc_res = client.post(
        f"/api/datasets/{dataset_id}/documents",
        files={"file": ("guide.txt", b"System setup guide content.", "text/plain")},
    )
    assert doc_res.status_code == 201

    # 3. Verify files exist on disk
    ds_dir = get_dataset_dir(dataset_id)
    assert ds_dir.exists()
    assert (ds_dir / "data.csv").exists()
    assert (ds_dir / "meta.json").exists()
    assert (ds_dir / "docs").exists()

    # 4. Verify vectors exist in ChromaDB
    collection = get_chunks_collection()
    vectors = collection.get(where={"dataset_id": dataset_id})
    assert len(vectors["ids"]) > 0

    # 5. Send DELETE request
    del_res = client.delete(f"/api/datasets/{dataset_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 6. Verify disk files are completely removed
    assert not ds_dir.exists()

    # 7. Verify vectors are completely removed from ChromaDB
    vectors_after = collection.get(where={"dataset_id": dataset_id})
    assert len(vectors_after["ids"]) == 0

    # 8. Verify endpoints return 404
    assert client.get(f"/api/datasets/{dataset_id}/profile").status_code == 404
    assert client.get(f"/api/datasets/{dataset_id}/preview").status_code == 404
    assert client.get(f"/api/datasets/{dataset_id}/documents").status_code == 404


def test_restart_survival(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    fake_embedding_fn: DeterministicFakeEmbeddingFunction,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SPEC 7.3: Dataset and document metadata survive server/client restart from disk."""
    # Configure shared persistent chroma directory
    chroma_dir = tmp_path / "restart_chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "chroma_persist_directory", str(chroma_dir))
    reset_chroma_client()

    # 1. Upload dataset and document
    csv_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    assert csv_res.status_code == 201
    dataset_id = csv_res.json()["dataset_id"]

    doc_res = client.post(
        f"/api/datasets/{dataset_id}/documents",
        files={"file": ("terms.txt", b"Standard terms and refund guidelines.", "text/plain")},
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    # 2. Simulate server restart: reset client cache and instantiate fresh TestClient
    reset_chroma_client()
    new_client = TestClient(app, raise_server_exceptions=False)

    # 3. Verify dataset profile is loaded from disk
    profile_res = new_client.get(f"/api/datasets/{dataset_id}/profile")
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["row_count"] == 4
    assert profile_data["col_count"] == 3

    # 4. Verify preview is loaded from disk
    preview_res = new_client.get(f"/api/datasets/{dataset_id}/preview")
    assert preview_res.status_code == 200
    assert len(preview_res.json()["rows"]) == 4

    # 5. Verify document metadata survived on disk
    docs_res = new_client.get(f"/api/datasets/{dataset_id}/documents")
    assert docs_res.status_code == 200
    docs_list = docs_res.json()["documents"]
    assert len(docs_list) == 1
    assert docs_list[0]["id"] == doc_id
    assert docs_list[0]["filename"] == "terms.txt"
    assert docs_list[0]["status"] == "indexed"

    # 6. Verify Chroma vector retrieval works across restarts
    retrieved = retrieve("refund guidelines", dataset_id=dataset_id, top_k=2)
    assert len(retrieved) > 0
    assert "Standard terms and refund guidelines." in retrieved[0].text

    reset_chroma_client()


def test_combined_question_integration(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """SPEC 7.3 step 5: Combined question returns both computed tabular result and document citations."""
    # 1. Upload CSV
    csv_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = csv_res.json()["dataset_id"]

    # 2. Upload document
    client.post(
        f"/api/datasets/{dataset_id}/documents",
        files={"file": ("revenue_policy.txt", b"Recognized revenue includes all delivered hardware orders.", "text/plain")},
    )

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
        config: object = None,
    ) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "combined", "reason": "Requires revenue calculation and policy context"}')
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(plan_dict))
        if "document synthesis assistant" in system_inst:
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "Total revenue is 240000, which qualifies as recognized revenue per policy.",
                    "used_passages": [1],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    ask_res = client.post(
        f"/api/datasets/{dataset_id}/ask",
        json={"question": "What was total revenue and how does the policy define recognized revenue?"},
    )
    assert ask_res.status_code == 200
    body = ask_res.json()
    assert body["route"] == "combined"
    assert body["computed_by_engine"] is True
    assert body["table"]["rows"][0]["revenue"] == 240000
    assert len(body["citations"]) == 1
    assert body["citations"][0]["filename"] == "revenue_policy.txt"
    assert "recognized revenue" in body["citations"][0]["snippet"].lower()


def test_cross_dataset_isolation_integration(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """SPEC 7.3 step 6: Document from dataset A is never retrieved or cited for dataset B."""
    # Create dataset A and document A
    res_a = client.post(
        "/api/datasets",
        files={"file": ("data_a.csv", sample_csv_bytes, "text/csv")},
    )
    ds_a = res_a.json()["dataset_id"]
    client.post(
        f"/api/datasets/{ds_a}/documents",
        files={"file": ("secret_a.txt", b"The confidential password for Dataset A is OMEGA-99.", "text/plain")},
    )

    # Create dataset B and document B
    res_b = client.post(
        "/api/datasets",
        files={"file": ("data_b.csv", sample_csv_bytes, "text/csv")},
    )
    ds_b = res_b.json()["dataset_id"]
    client.post(
        f"/api/datasets/{ds_b}/documents",
        files={"file": ("secret_b.txt", b"The confidential password for Dataset B is EPSILON-42.", "text/plain")},
    )

    def mock_generate_content(
        model: str,
        contents: str,
        config: object = None,
    ) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "document", "reason": "Requires secret document lookup"}')
        if "document analysis assistant" in system_inst:
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "The password is in the cited document.",
                    "used_passages": [1],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    # Ask against dataset B
    ask_res = client.post(
        f"/api/datasets/{ds_b}/ask",
        json={"question": "What is the confidential password?"},
    )
    assert ask_res.status_code == 200
    body = ask_res.json()
    assert len(body["citations"]) == 1
    # Citation MUST be secret_b.txt, never secret_a.txt
    assert body["citations"][0]["filename"] == "secret_b.txt"
    assert "EPSILON-42" in body["citations"][0]["snippet"]
    assert "OMEGA-99" not in body["citations"][0]["snippet"]
