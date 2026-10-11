from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient


def test_upload_dataset_api(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """POST /api/datasets uploads file, returns metadata, and writes to disk."""
    response = client.post(
        "/api/datasets",
        files={"file": ("sales_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()

    assert "dataset_id" in data
    dataset_id = data["dataset_id"]
    assert str(uuid.UUID(dataset_id)) == dataset_id
    assert data["filename"] == "sales_data.csv"
    assert data["file_size_bytes"] == len(sample_csv_bytes)
    assert data["row_count"] == 4

    # Verify metadata and file on disk to ensure it survives server restart
    meta_file = tmp_upload_dir / dataset_id / "meta.json"
    data_file = tmp_upload_dir / dataset_id / "data.csv"
    assert meta_file.exists()
    assert data_file.exists()


def test_get_profile_api(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """GET /api/datasets/{id}/profile returns dataset statistics."""
    upload_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    res = client.get(f"/api/datasets/{dataset_id}/profile")
    assert res.status_code == 200
    profile = res.json()

    assert profile["dataset_id"] == dataset_id
    assert profile["row_count"] == 4
    assert profile["col_count"] == 3
    assert profile["columns"] == ["product", "city", "revenue"]
    assert profile["numeric_summary"]["revenue"]["mean"] == 60000.0


def test_get_preview_api(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """GET /api/datasets/{id}/preview returns first 100 rows."""
    upload_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    res = client.get(f"/api/datasets/{dataset_id}/preview")
    assert res.status_code == 200
    preview = res.json()

    assert preview["dataset_id"] == dataset_id
    assert preview["total_rows"] == 4
    assert len(preview["rows"]) == 4
    assert preview["rows"][0]["product"] == "Laptop"
    assert preview["rows"][0]["city"] == "Delhi"
    assert preview["rows"][0]["revenue"] == 80000


def test_delete_dataset_api(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """DELETE /api/datasets/{id} removes dataset folder from disk."""
    upload_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]
    dataset_folder = tmp_upload_dir / dataset_id
    assert dataset_folder.exists()

    del_res = client.delete(f"/api/datasets/{dataset_id}")
    assert del_res.status_code == 200
    assert not dataset_folder.exists()

    # Subsequent GET returns 404 with standard error shape
    get_res = client.get(f"/api/datasets/{dataset_id}/profile")
    assert get_res.status_code == 404
    body = get_res.json()
    assert "error" in body
    assert "message" in body


def test_unknown_id_returns_standard_error(client: TestClient) -> None:
    """Unknown dataset_id returns 404 with standard {"error", "message"} shape."""
    unknown_id = str(uuid.uuid4())

    for url, method in [
        (f"/api/datasets/{unknown_id}/profile", "get"),
        (f"/api/datasets/{unknown_id}/preview", "get"),
        (f"/api/datasets/{unknown_id}", "delete"),
    ]:
        res = getattr(client, method)(url)
        assert res.status_code == 404
        body = res.json()
        assert "error" in body
        assert "message" in body
        assert body["error"] == "not_found"


def test_invalid_uuid_id_returns_standard_error(client: TestClient) -> None:
    """Invalid non-UUID identifier returns 400 with standard {"error", "message"} shape."""
    invalid_id = "not-a-valid-uuid"

    for url, method in [
        (f"/api/datasets/{invalid_id}/profile", "get"),
        (f"/api/datasets/{invalid_id}/preview", "get"),
        (f"/api/datasets/{invalid_id}", "delete"),
    ]:
        res = getattr(client, method)(url)
        assert res.status_code == 400
        body = res.json()
        assert "error" in body
        assert "message" in body
        assert body["error"] == "invalid_dataset_id"


def test_upload_invalid_file_returns_standard_error(client: TestClient) -> None:
    """Uploading non-CSV or empty file returns 400 with standard error shape."""
    # Wrong extension
    res = client.post(
        "/api/datasets",
        files={"file": ("doc.txt", b"some text", "text/plain")},
    )
    assert res.status_code == 400
    body = res.json()
    assert "error" in body
    assert "message" in body
    assert body["error"] == "unsupported_file_type"

    # Empty file
    res_empty = client.post(
        "/api/datasets",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert res_empty.status_code == 400
    body_empty = res_empty.json()
    assert "error" in body_empty
    assert "message" in body_empty
    assert body_empty["error"] == "empty_csv"


def test_ask_valid_dataset_returns_table_and_chart(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """POST /api/datasets/{id}/ask returns AnswerResponse with table and chart_spec."""
    upload_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post(
        f"/api/datasets/{dataset_id}/ask",
        json={"question": "What is the total revenue?"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["answer_text"] == "Stub response (LLM not connected yet)"
    assert "table" in data
    assert data["table"] is not None
    assert "columns" in data["table"]
    assert "rows" in data["table"]
    assert data["table"]["rows"][0]["revenue"] == 240000

    assert "chart_spec" in data
    assert data["chart_spec"] is not None
    assert "type" in data["chart_spec"]
    assert "data" in data["chart_spec"]
    assert data["citations"] == []


def test_ask_unknown_dataset_returns_standard_error(client: TestClient) -> None:
    """POST /api/datasets/{id}/ask with unknown dataset_id returns 404 standard error."""
    unknown_id = str(uuid.uuid4())
    res = client.post(
        f"/api/datasets/{unknown_id}/ask",
        json={"question": "Any question?"},
    )
    assert res.status_code == 404
    body = res.json()
    assert "error" in body
    assert "message" in body
    assert body["error"] == "not_found"


def test_ask_empty_question_returns_422(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
) -> None:
    """POST /api/datasets/{id}/ask with empty, whitespace, or missing question returns 422."""
    upload_res = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    # Empty string
    res_empty = client.post(
        f"/api/datasets/{dataset_id}/ask",
        json={"question": ""},
    )
    assert res_empty.status_code == 422

    # Whitespace only
    res_spaces = client.post(
        f"/api/datasets/{dataset_id}/ask",
        json={"question": "   \n\t "},
    )
    assert res_spaces.status_code == 422

    # Missing question key
    res_missing = client.post(
        f"/api/datasets/{dataset_id}/ask",
        json={},
    )
    assert res_missing.status_code == 422
