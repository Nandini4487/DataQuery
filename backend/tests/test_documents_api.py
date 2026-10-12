from __future__ import annotations

import uuid
from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.embedding_service import (
    reset_embedding_function,
    set_embedding_function,
)
from app.services.retrieval_service import get_chunks_collection, retrieve


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
    """Helper to upload a test dataset CSV and return its dataset_id."""
    res = client.post(
        "/api/datasets",
        files={"file": ("data.csv", sample_csv_bytes, "text/csv")},
    )
    assert res.status_code == 201
    return res.json()["dataset_id"]


def test_upload_txt_and_pdf_succeed_and_list_shows_them(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Uploading valid TXT and PDF documents succeeds, records chunk_count, and lists them."""
    ds_id = _upload_dataset(client, sample_csv_bytes)

    # 1. Upload TXT
    txt_content = b"Financial report quarterly overview. Revenue rose by fifteen percent."
    res_txt = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("finance.txt", txt_content, "text/plain")},
    )
    assert res_txt.status_code == 201
    doc_txt = res_txt.json()
    assert doc_txt["dataset_id"] == ds_id
    assert doc_txt["filename"] == "finance.txt"
    assert doc_txt["file_type"] == "txt"
    assert doc_txt["status"] == "indexed"
    assert doc_txt["chunk_count"] == 1
    assert doc_txt["page_count"] == 1

    # 2. Upload PDF
    pdf_bytes = make_pdf(["Page 1: Annual strategic goals.", "Page 2: Risk analysis matrix."])
    res_pdf = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("strategy.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_pdf.status_code == 201
    doc_pdf = res_pdf.json()
    assert doc_pdf["dataset_id"] == ds_id
    assert doc_pdf["filename"] == "strategy.pdf"
    assert doc_pdf["file_type"] == "pdf"
    assert doc_pdf["status"] == "indexed"
    assert doc_pdf["chunk_count"] == 2
    assert doc_pdf["page_count"] == 2

    # 3. List documents
    res_list = client.get(f"/api/datasets/{ds_id}/documents")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] == 2
    doc_ids = [d["id"] for d in list_data["documents"]]
    assert doc_txt["id"] in doc_ids
    assert doc_pdf["id"] in doc_ids


def test_delete_one_document_removes_from_list_and_vectors(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Deleting one document removes it from the list and Chroma while preserving others."""
    ds_id = _upload_dataset(client, sample_csv_bytes)

    # Upload doc 1
    res1 = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("doc1.txt", b"Unique content for document one.", "text/plain")},
    )
    doc1_id = res1.json()["id"]

    # Upload doc 2
    res2 = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("doc2.txt", b"Unique content for document two.", "text/plain")},
    )
    doc2_id = res2.json()["id"]

    # Verify both documents have vectors
    results_before = retrieve("Unique content", dataset_id=ds_id, top_k=5)
    doc_ids_before = {r.metadata["document_id"] for r in results_before}
    assert doc1_id in doc_ids_before
    assert doc2_id in doc_ids_before

    # Delete doc 1
    res_del = client.delete(f"/api/datasets/{ds_id}/documents/{doc1_id}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # Verify doc 1 is absent from list
    res_list = client.get(f"/api/datasets/{ds_id}/documents")
    assert res_list.status_code == 200
    remaining_ids = [d["id"] for d in res_list.json()["documents"]]
    assert doc1_id not in remaining_ids
    assert doc2_id in remaining_ids

    # Verify doc 1's vectors are gone and doc 2 remains
    results_after = retrieve("Unique content", dataset_id=ds_id, top_k=5)
    doc_ids_after = {r.metadata["document_id"] for r in results_after}
    assert doc1_id not in doc_ids_after
    assert doc2_id in doc_ids_after


def test_upload_to_unknown_or_non_uuid_dataset_fails_safely(
    client: TestClient,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Unknown dataset returns 404; non-UUID dataset returns 400 with standard error shape."""
    # Unknown UUID dataset
    random_id = str(uuid.uuid4())
    res_404 = client.post(
        f"/api/datasets/{random_id}/documents",
        files={"file": ("notes.txt", b"Some notes.", "text/plain")},
    )
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert data_404["error"] == "not_found"
    assert "message" in data_404

    # Non-UUID dataset
    res_400 = client.post(
        "/api/datasets/not-a-real-uuid/documents",
        files={"file": ("notes.txt", b"Some notes.", "text/plain")},
    )
    assert res_400.status_code == 400
    data_400 = res_400.json()
    assert data_400["error"] == "invalid_dataset_id"
    assert "message" in data_400


def test_invalid_file_returns_standard_error_and_leaves_nothing(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Invalid documents (unsupported extension, corrupt header, empty) leave no disk/vector trace."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    docs_dir = Path(settings.upload_dir) / ds_id / "docs"

    # 1. Unsupported extension
    res_ext = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("notes.docx", b"Word document payload", "application/octet-stream")},
    )
    assert res_ext.status_code == 400
    assert res_ext.json()["error"] == "unsupported_file_type"

    # 2. Corrupt PDF header
    res_header = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("fake.pdf", b"NOT_A_PDF_HEADER_CONTENT", "application/pdf")},
    )
    assert res_header.status_code == 400
    assert res_header.json()["error"] == "corrupt_pdf"

    # 3. Empty file
    res_empty = client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert res_empty.status_code == 400
    assert res_empty.json()["error"] == "empty_file"

    # Verify no documents on disk or in Chroma
    if docs_dir.exists():
        assert list(docs_dir.glob("*")) == []
    col = get_chunks_collection()
    assert col.count() == 0


def test_simulated_embedding_failure_cleans_up_completely(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """If embedding fails, returns safe 503 embedding_unavailable and leaves no leftover files or vectors."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    docs_dir = Path(settings.upload_dir) / ds_id / "docs"

    def explode_embedding(texts: list[str]) -> list[list[float]]:
        raise RuntimeError("GPU CUDA out of memory in C:\\internal\\cuda\\driver.dll")

    set_embedding_function(explode_embedding)
    try:
        res = client.post(
            f"/api/datasets/{ds_id}/documents",
            files={"file": ("test.txt", b"Valid text that will fail during embedding.", "text/plain")},
        )
        assert res.status_code == 503
        data = res.json()
        assert data["error"] == "embedding_unavailable"
        assert "driver.dll" not in data["message"]
        assert "C:\\" not in data["message"]

        # Confirm cleanup: no files or metadata on disk
        if docs_dir.exists():
            assert list(docs_dir.glob("*")) == []

        # Confirm cleanup: no Chroma vectors
        col = get_chunks_collection()
        assert col.count() == 0
    finally:
        reset_embedding_function()


def test_dataset_delete_removes_document_files_metadata_and_vectors(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """Deleting a dataset cascades: deletes CSV, all document files, metadata, and all vectors."""
    ds_id = _upload_dataset(client, sample_csv_bytes)
    ds_dir = Path(settings.upload_dir) / ds_id

    # Upload 2 documents
    client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("doc1.txt", b"Text of document 1.", "text/plain")},
    )
    client.post(
        f"/api/datasets/{ds_id}/documents",
        files={"file": ("doc2.txt", b"Text of document 2.", "text/plain")},
    )

    # Verify vectors exist
    col = get_chunks_collection()
    assert col.count() == 2

    # Delete dataset
    res_del = client.delete(f"/api/datasets/{ds_id}")
    assert res_del.status_code == 200

    # Verify directory on disk is removed
    assert not ds_dir.exists()

    # Verify all vectors for that dataset are gone
    assert retrieve("Text", dataset_id=ds_id) == []
    assert col.count() == 0


def test_cross_dataset_isolation_and_delete_forbidden(
    client: TestClient,
    sample_csv_bytes: bytes,
    tmp_upload_dir: Path,
    temp_chroma_client: object,
) -> None:
    """A document in dataset A never appears in dataset B, and cannot be deleted via dataset B."""
    ds_a = _upload_dataset(client, sample_csv_bytes)
    ds_b = _upload_dataset(client, sample_csv_bytes)

    # Upload document to dataset A
    res_upload = client.post(
        f"/api/datasets/{ds_a}/documents",
        files={"file": ("private_a.txt", b"Confidential memo for dataset A.", "text/plain")},
    )
    assert res_upload.status_code == 201
    doc_a_id = res_upload.json()["id"]

    # List dataset B -> doc A must not appear
    res_b_list = client.get(f"/api/datasets/{ds_b}/documents")
    assert res_b_list.status_code == 200
    assert res_b_list.json()["total"] == 0
    assert res_b_list.json()["documents"] == []

    # Attempt to delete doc A using dataset B's URL -> must return 404
    res_cross_del = client.delete(f"/api/datasets/{ds_b}/documents/{doc_a_id}")
    assert res_cross_del.status_code == 404
    assert res_cross_del.json()["error"] == "not_found"

    # Confirm doc A is still intact in dataset A
    res_a_list = client.get(f"/api/datasets/{ds_a}/documents")
    assert res_a_list.status_code == 200
    assert res_a_list.json()["total"] == 1
    assert res_a_list.json()["documents"][0]["id"] == doc_a_id
