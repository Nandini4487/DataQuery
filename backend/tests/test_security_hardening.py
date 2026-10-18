from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import read_stream_limited
from app.services.file_service import FileValidationError
from app.services.retrieval_service import get_chroma_client, reset_chroma_client


@pytest.mark.asyncio
async def test_streaming_upload_aborts_early_without_reading_whole_body() -> None:
    """Assert that read_stream_limited aborts early as soon as the size limit is exceeded.

    The remainder of the payload is never read into server memory.
    """
    chunk_size = 64 * 1024  # 64 KB
    total_chunks = 20
    chunk_data = b"X" * chunk_size
    read_count = 0

    async def mock_read(size: int = -1) -> bytes:
        nonlocal read_count
        if read_count < total_chunks:
            read_count += 1
            return chunk_data
        return b""

    mock_upload = AsyncMock(spec=UploadFile)
    mock_upload.read = mock_read

    # Max limit: 256 KB (4 chunks). The 5th chunk should trigger early abort.
    max_bytes = 4 * chunk_size

    with pytest.raises(FileValidationError) as exc_info:
        await read_stream_limited(mock_upload, max_bytes=max_bytes, chunk_size=chunk_size)

    assert exc_info.value.error_code == "file_too_large"
    # Verify early abort: only 5 chunks were read, not all 20 chunks!
    assert read_count == 5
    assert read_count < total_chunks


def test_rate_limiting_11th_upload_returns_429(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 11th dataset upload within a minute returns 429 in the standard error shape with Retry-After."""
    monkeypatch.setattr(settings, "rate_limiting_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_dataset_upload", "10/minute")

    # Send 10 valid uploads
    for i in range(10):
        files = {"file": (f"test_{i}.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        res = client.post("/api/datasets", files=files)
        assert res.status_code == 201, f"Expected 201 on upload {i + 1}, got {res.status_code}"

    # 11th upload must trigger 429 rate limit
    files = {"file": ("test_11.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
    res_11 = client.post("/api/datasets", files=files)
    assert res_11.status_code == 429
    body = res_11.json()
    assert body["error"] == "rate_limited"
    assert "Too many requests" in body["message"]
    assert "Retry-After" in res_11.headers


def test_rate_limiting_21st_ask_returns_429_and_makes_no_llm_call(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    fake_llm_client: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 21st ask within a minute returns 429 and makes zero LLM calls."""
    # First upload a dataset with rate limiting temporarily off
    monkeypatch.setattr(settings, "rate_limiting_enabled", False)
    files = {"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
    upload_res = client.post("/api/datasets", files=files)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    # Now enable rate limiting for ask endpoint
    monkeypatch.setattr(settings, "rate_limiting_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_ask", "20/minute")

    fake_llm_client.models.default_response = (  # type: ignore[attr-defined]
        '{"supported": true, "reason": "", "plan": {"operation": "count"}}'
    )

    # Send 20 ask requests
    for i in range(20):
        res = client.post(f"/api/datasets/{dataset_id}/ask", json={"question": "What is total revenue?"})
        assert res.status_code == 200, f"Expected 200 on ask {i + 1}, got {res.status_code}"

    call_count_after_20 = fake_llm_client.models.call_count  # type: ignore[attr-defined]

    # 21st ask must trigger 429 rate limit
    res_21 = client.post(f"/api/datasets/{dataset_id}/ask", json={"question": "What is total revenue?"})
    assert res_21.status_code == 429
    body = res_21.json()
    assert body["error"] == "rate_limited"
    assert "Too many requests" in body["message"]
    assert "Retry-After" in res_21.headers

    # Assert that zero additional LLM calls were made on the 21st request
    assert fake_llm_client.models.call_count == call_count_after_20  # type: ignore[attr-defined]


def test_max_dataset_columns_exceeded_rejected(
    client: TestClient,
    tmp_upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CSV upload with columns exceeding max_dataset_columns returns 400 too_many_columns."""
    monkeypatch.setattr(settings, "max_dataset_columns", 5)

    header = ",".join([f"col_{i}" for i in range(10)])
    row = ",".join(["1"] * 10)
    csv_text = f"{header}\n{row}\n"

    files = {"file": ("wide.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets", files=files)
    assert res.status_code == 400
    body = res.json()
    assert body["error"] == "too_many_columns"
    assert "exceeds maximum limit of 5 columns" in body["message"]


def test_max_dataset_rows_exceeded_rejected(
    client: TestClient,
    tmp_upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CSV upload with rows exceeding max_dataset_rows returns 400 too_many_rows."""
    monkeypatch.setattr(settings, "max_dataset_rows", 3)

    csv_text = "product,val\nA,1\nB,2\nC,3\nD,4\nE,5\n"
    files = {"file": ("tall.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets", files=files)
    assert res.status_code == 400
    body = res.json()
    assert body["error"] == "too_many_rows"
    assert "exceeds maximum limit of 3 rows" in body["message"]


def test_request_validation_error_returns_standard_shape_without_leaking_raw_values(
    client: TestClient,
    tmp_upload_dir: Path,
) -> None:
    """Pydantic RequestValidationError returns standard error shape with a generic message."""
    # Send empty body / invalid schema to /ask
    res = client.post("/api/datasets/11111111-1111-4111-8111-111111111111/ask", json={})
    assert res.status_code == 422
    body = res.json()
    assert body["error"] == "validation_error"
    assert body["message"] == "Invalid request parameters or payload."
    assert "detail" not in body


def test_chromadb_anonymized_telemetry_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ChromaDB PersistentClient has anonymized_telemetry set to False."""
    chroma_dir = tmp_path / "test_telemetry_chroma"
    monkeypatch.setattr(settings, "chroma_persist_directory", str(chroma_dir))
    reset_chroma_client()
    try:
        chroma = get_chroma_client()
        assert chroma.get_settings().anonymized_telemetry is False
    finally:
        reset_chroma_client()


def test_cors_restricted_methods_and_headers(client: TestClient) -> None:
    """CORS preflight reflects configured origin and restricted methods/headers."""
    res = client.options(
        "/api/health",
        headers={
            "Origin": settings.frontend_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    allow_origin = res.headers.get("Access-Control-Allow-Origin")
    allow_methods = res.headers.get("Access-Control-Allow-Methods", "")
    assert allow_origin == settings.frontend_origin
    # Assert methods are restricted and not wildcard "*"
    assert "*" not in allow_methods
    for method in ["GET", "POST", "DELETE", "OPTIONS"]:
        assert method in allow_methods


def test_unparsable_csv_error_message_is_sanitized(
    client: TestClient,
    tmp_upload_dir: Path,
) -> None:
    """Unparsable CSV does not reflect internal python/pandas exception text in client message."""
    bad_csv = b"col1,col2\n1,\"unclosed quote\n2,3\n"
    files = {"file": ("broken.csv", io.BytesIO(bad_csv), "text/csv")}
    res = client.post("/api/datasets", files=files)
    assert res.status_code == 400
    body = res.json()
    assert body["error"] == "unparsable_csv"
    assert body["message"] == "Failed to parse CSV file. Please ensure it is a valid, well-formed CSV."
    assert "Traceback" not in body["message"]
    assert "Exception" not in body["message"]


def test_corrupt_pdf_error_message_is_sanitized(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """Corrupt PDF does not reflect PyMuPDF internal exception text in client message."""
    # First create dataset
    files = {"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
    upload_res = client.post("/api/datasets", files=files)
    dataset_id = upload_res.json()["dataset_id"]

    # Upload corrupt PDF with valid %PDF- magic bytes header but garbage body
    corrupt_pdf = b"%PDF-1.4\nGARBAGE NOT REAL PDF BYTES\n"
    pdf_files = {"file": ("corrupt.pdf", io.BytesIO(corrupt_pdf), "application/pdf")}
    res = client.post(f"/api/datasets/{dataset_id}/documents", files=pdf_files)
    assert res.status_code == 400
    body = res.json()
    assert body["error"] == "corrupt_pdf"
    assert body["message"] == "Failed to open or parse PDF file. The file may be corrupt or invalid."
    assert "Traceback" not in body["message"]
    assert "mupdf" not in body["message"].lower()


def test_internal_server_error_returns_standard_shape(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """Unexpected 500 error returns standard {"error", "message"} shape (no 'detail' key)."""
    with patch("app.api.datasets.save_csv_upload", side_effect=RuntimeError("Disk failure")):
        files = {"file": ("test.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        res = client.post("/api/datasets", files=files)
        assert res.status_code == 500
        body = res.json()
        assert body["error"] == "internal_error"
        assert body["message"] == "Failed to process upload."
        assert "detail" not in body
