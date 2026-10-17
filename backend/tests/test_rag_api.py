from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.services.embedding_service import (
    reset_embedding_function,
    set_embedding_function,
)
from tests.conftest import FakeGenAIClient, FakeGenerateContentResponse


def make_pdf(pages_text: list[str]) -> bytes:
    """Helper to generate an in-memory PDF with the specified text per page."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _upload_dataset(client: TestClient, sample_csv_bytes: bytes) -> str:
    res = client.post(
        "/api/datasets",
        files={"file": ("data.csv", sample_csv_bytes, "text/csv")},
    )
    assert res.status_code == 201
    return res.json()["dataset_id"]


def _upload_doc(client: TestClient, dataset_id: str, filename: str, content: bytes, mime: str = "text/plain") -> str:
    res = client.post(
        f"/api/datasets/{dataset_id}/documents",
        files={"file": (filename, content, mime)},
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_document_question_returns_citations_from_stored_metadata(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Document route returns citations built server-side from stored metadata with filename and page."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    pdf_bytes = make_pdf(["Page 1 refund policy details.", "Page 2 warranty guidelines."])
    _upload_doc(client, ds_id, "policy.pdf", pdf_bytes, mime="application/pdf")

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "document", "reason": "Asks about refund policy"}')
        if "document analysis assistant" in system_inst:
            passage_num = 1
            for p_idx in range(1, 10):
                header = f"=== BEGIN PASSAGE [{p_idx}]"
                if header in contents:
                    block = contents.split(header)[1].split(f"=== END PASSAGE [{p_idx}]")[0]
                    if "refund policy" in block.lower():
                        passage_num = p_idx
                        break
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "Refunds are processed within 30 days as stated in the policy.",
                    "used_passages": [passage_num],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "What is the refund policy?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "document"
    assert "Refunds are processed within 30 days" in data["answer_text"]
    assert data["table"] is None
    assert data["chart_spec"] is None
    assert len(data["citations"]) == 1
    cit = data["citations"][0]
    assert cit["filename"] == "policy.pdf"
    assert cit["page_number"] == 1
    assert "refund policy" in cit["snippet"].lower()


def test_model_out_of_range_used_passages_dropped_and_duplicates_collapsed(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Out-of-range passage numbers (e.g. 99, -1) are dropped and duplicate numbers collapsed."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    _upload_doc(client, ds_id, "single_page.txt", b"Single passage content here.")

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "document", "reason": "text query"}')
        if "document analysis assistant" in system_inst:
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "Answer from passage.",
                    "used_passages": [1, 99, 1, -5, 0],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "What does the passage say?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["citations"]) == 1
    assert data["citations"][0]["filename"] == "single_page.txt"


def test_combined_question_returns_computed_table_and_citations(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Combined question returns exact computed table (240000 for total revenue) AND document citations."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    _upload_doc(client, ds_id, "targets.txt", b"Target sales revenue for Q4 was 200000.")

    plan_dict = {
        "supported": True,
        "reason": "",
        "plan": {
            "operation": "aggregate",
            "columns": ["revenue"],
            "agg": "sum",
        },
    }

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "combined", "reason": "Requires both total revenue and target"}')
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(plan_dict))
        if "document synthesis assistant" in system_inst:
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "Total revenue is 240000, exceeding the target of 200000.",
                    "used_passages": [1],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "Did total revenue meet the target?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "combined"
    assert data["table"]["rows"][0]["revenue"] == 240000
    assert data["computed_by_engine"] is True
    assert len(data["citations"]) == 1
    assert data["citations"][0]["filename"] == "targets.txt"
    assert "240000" in data["answer_text"]


def test_combined_with_failing_document_branch_still_returns_table(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """When the document branch in a combined question fails, the computed table is preserved and note added."""
    # Dataset uploaded, but no documents uploaded
    ds_id = _upload_dataset(client, sample_csv_bytes)

    plan_dict = {
        "supported": True,
        "reason": "",
        "plan": {
            "operation": "aggregate",
            "columns": ["revenue"],
            "agg": "sum",
        },
    }

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "combined", "reason": "Requires total revenue and target policy"}')
        if "BEGIN DATASET SCHEMA" in contents:
            return FakeGenerateContentResponse(json.dumps(plan_dict))
        # Explanation call for structured branch
        return FakeGenerateContentResponse("The total revenue is 240000.")

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "Compare total revenue against the policy targets."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "combined"
    assert data["table"]["rows"][0]["revenue"] == 240000
    assert data["citations"] == []
    assert "240000" in data["answer_text"]
    assert "No reference document is uploaded" in data["answer_text"]


def test_nothing_retrieved_makes_no_llm_call_and_returns_insufficient_info(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When vector retrieval returns empty, no answer LLM call is made and a clear message is returned."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    _upload_doc(client, ds_id, "doc.txt", b"Some irrelevant topic.")

    rag_llm_called = False

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        nonlocal rag_llm_called
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "document", "reason": "text question"}')
        if "document analysis assistant" in system_inst:
            rag_llm_called = True
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    # Force retrieve to return empty list
    monkeypatch.setattr("app.services.ask_service.retrieve", lambda **kwargs: [])

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "What is the quantum encryption key?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "document"
    assert "The uploaded documents do not contain enough information to answer this question." in data["answer_text"]
    assert data["citations"] == []
    assert rag_llm_called is False


def test_document_route_with_no_documents_returns_422_documents_required(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Document route on a dataset with 0 documents returns 422 documents_required."""
    ds_id = _upload_dataset(client, sample_csv_bytes)

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        return FakeGenerateContentResponse('{"route": "document", "reason": "Needs document"}')

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "What does section 4 say?"},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["error"] == "documents_required"
    assert "upload a reference document" in data["message"].lower()


def test_unsupported_route_returns_422_unsupported_question(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Unsupported route returns 422 with unsupported_question and the router's reason."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    router_reason = "This question asks for weather forecasts which are outside data scope."

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        return FakeGenerateContentResponse(json.dumps({
            "route": "unsupported",
            "reason": router_reason,
        }))

    fake_llm_client.models.generate_content = mock_generate_content

    res = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "What will the weather be tomorrow in Tokyo?"},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["error"] == "unsupported_question"
    assert data["message"] == router_reason


def test_embedding_failure_returns_503_embedding_unavailable(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Embedding failure on document route returns 503 embedding_unavailable."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    _upload_doc(client, ds_id, "doc.txt", b"Valid doc content.")

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        return FakeGenerateContentResponse('{"route": "document", "reason": "Document query"}')

    fake_llm_client.models.generate_content = mock_generate_content

    def explode_embeddings(texts: list[str]) -> list[list[float]]:
        raise RuntimeError("GPU VRAM C:\\internal\\cuda\\driver.dll fault")

    set_embedding_function(explode_embeddings)
    try:
        res = client.post(
            f"/api/datasets/{ds_id}/ask",
            json={"question": "What is in doc?"},
        )
        assert res.status_code == 503
        data = res.json()
        assert data["error"] == "embedding_unavailable"
        assert "driver.dll" not in data["message"]
    finally:
        reset_embedding_function()


def test_document_from_dataset_a_never_cited_for_dataset_b(
    client: TestClient,
    fake_llm_client: FakeGenAIClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Cross-dataset citation isolation: documents in dataset A are never cited in queries for dataset B."""
    ds_a = _upload_dataset(client, sample_csv_bytes)
    ds_b = _upload_dataset(client, sample_csv_bytes)

    _upload_doc(client, ds_a, "confidential_a.txt", b"Strictly confidential roadmap for company A.")
    _upload_doc(client, ds_b, "public_b.txt", b"Public marketing strategy for company B.")

    def mock_generate_content(model: str, contents: str, config: object = None) -> FakeGenerateContentResponse:
        system_inst = str(getattr(config, "system_instruction", "")) if config else ""
        if "query routing classifier" in system_inst or "BEGIN DATASET COLUMNS AND TYPES" in contents:
            return FakeGenerateContentResponse('{"route": "document", "reason": "document query"}')
        if "document analysis assistant" in system_inst:
            return FakeGenerateContentResponse(
                json.dumps({
                    "answer_text": "Answer citing retrieved passage.",
                    "used_passages": [1],
                })
            )
        return FakeGenerateContentResponse("{}")

    fake_llm_client.models.generate_content = mock_generate_content

    # Ask on dataset B
    res_b = client.post(
        f"/api/datasets/{ds_b}/ask",
        json={"question": "What is the marketing strategy?"},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert len(data_b["citations"]) == 1
    assert data_b["citations"][0]["filename"] == "public_b.txt"
    assert data_b["citations"][0]["document_id"] != ds_a
