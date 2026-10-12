from __future__ import annotations

import uuid
from pathlib import Path

import pymupdf
import pytest

from app.core.config import settings
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentValidationError,
    delete_document,
    get_document,
    get_document_pages,
    list_documents,
    save_document,
)


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


@pytest.fixture()
def sample_dataset_id() -> str:
    """Return a valid UUID dataset id."""
    return str(uuid.uuid4())


def test_valid_pdf_accepted_with_page_numbers(tmp_path: Path, sample_dataset_id: str) -> None:
    """Valid PDF with multiple pages is accepted, preserving page numbers."""
    pdf_bytes = make_pdf(["Page 1: Terms & Conditions", "Page 2: Revenue Recognition Guidelines"])
    meta, pages = save_document(
        dataset_id=sample_dataset_id,
        filename="policy.pdf",
        content=pdf_bytes,
        base_dir=tmp_path,
    )

    assert meta.filename == "policy.pdf"
    assert meta.file_type == "pdf"
    assert meta.page_count == 2
    assert meta.status == "uploaded"

    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert "Terms & Conditions" in pages[0]["text"]
    assert pages[1]["page_number"] == 2
    assert "Revenue Recognition" in pages[1]["text"]


def test_valid_txt_accepted_with_page_number_one(tmp_path: Path, sample_dataset_id: str) -> None:
    """Valid TXT document is accepted and treated as page 1."""
    txt_content = b"All sales over 50,000 require manager approval."
    meta, pages = save_document(
        dataset_id=sample_dataset_id,
        filename="business_rules.txt",
        content=txt_content,
        base_dir=tmp_path,
    )

    assert meta.filename == "business_rules.txt"
    assert meta.file_type == "txt"
    assert meta.page_count == 1
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert "manager approval" in pages[0]["text"]


def test_wrong_header_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """A file claiming to be a PDF without the %PDF- header is rejected."""
    corrupt_content = b"NOT_A_REAL_PDF_HEADER_123456789"
    with pytest.raises(DocumentValidationError) as exc_info:
        save_document(
            dataset_id=sample_dataset_id,
            filename="fake.pdf",
            content=corrupt_content,
            base_dir=tmp_path,
        )

    assert exc_info.value.error_code == "corrupt_pdf"
    assert "header" in exc_info.value.message.lower()


def test_null_bytes_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """TXT files containing null bytes are rejected as binary content."""
    binary_content = b"Some valid text before null byte \x00 and after."
    with pytest.raises(DocumentValidationError) as exc_info:
        save_document(
            dataset_id=sample_dataset_id,
            filename="notes.txt",
            content=binary_content,
            base_dir=tmp_path,
        )

    assert exc_info.value.error_code == "binary_file_rejected"
    assert "null bytes" in exc_info.value.message.lower()


def test_empty_files_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """Empty PDF or TXT files (0 bytes or whitespace only) are rejected."""
    # 0 bytes
    with pytest.raises(DocumentValidationError) as exc_pdf:
        save_document(
            dataset_id=sample_dataset_id,
            filename="empty.pdf",
            content=b"",
            base_dir=tmp_path,
        )
    assert exc_pdf.value.error_code == "empty_file"

    # Whitespace only TXT
    with pytest.raises(DocumentValidationError) as exc_txt:
        save_document(
            dataset_id=sample_dataset_id,
            filename="spaces.txt",
            content=b"   \n\t  ",
            base_dir=tmp_path,
        )
    assert exc_txt.value.error_code == "empty_file"


def test_oversized_file_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """Files exceeding max_document_size_mb are rejected."""
    oversized_bytes = b"x" * (settings.max_document_size_mb * 1024 * 1024 + 1)
    with pytest.raises(DocumentValidationError) as exc_info:
        save_document(
            dataset_id=sample_dataset_id,
            filename="huge.txt",
            content=oversized_bytes,
            base_dir=tmp_path,
        )

    assert exc_info.value.error_code == "file_too_large"


def test_too_many_pages_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """PDFs exceeding max_pdf_pages are rejected."""
    # Generate PDF with 101 pages
    doc = pymupdf.open()
    for _ in range(settings.max_pdf_pages + 1):
        doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    with pytest.raises(DocumentValidationError) as exc_info:
        save_document(
            dataset_id=sample_dataset_id,
            filename="encyclopedia.pdf",
            content=pdf_bytes,
            base_dir=tmp_path,
        )

    assert exc_info.value.error_code == "too_many_pages"
    assert str(settings.max_pdf_pages) in exc_info.value.message


def test_image_only_pdf_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """PDFs with no extractable text are rejected with the required message."""
    # Create PDF with blank pages (no text inserted)
    pdf_bytes = make_pdf(["", ""])
    with pytest.raises(DocumentValidationError) as exc_info:
        save_document(
            dataset_id=sample_dataset_id,
            filename="scanned_receipt.pdf",
            content=pdf_bytes,
            base_dir=tmp_path,
        )

    assert exc_info.value.error_code == "no_text_content"
    assert "No extractable text. Only text-based PDFs are supported." in exc_info.value.message


def test_non_uuid_ids_rejected(tmp_path: Path, sample_dataset_id: str) -> None:
    """Non-UUID dataset_id or document_id values are rejected."""
    pdf_bytes = make_pdf(["Sample page"])

    # Invalid dataset_id
    with pytest.raises(DocumentValidationError) as exc_ds:
        save_document(
            dataset_id="not-a-valid-uuid-1234",
            filename="doc.pdf",
            content=pdf_bytes,
            base_dir=tmp_path,
        )
    assert exc_ds.value.error_code == "invalid_dataset_id"

    # Invalid document_id
    with pytest.raises(DocumentValidationError) as exc_doc:
        get_document(
            dataset_id=sample_dataset_id,
            document_id="../../path_traversal",
            base_dir=tmp_path,
        )
    assert exc_doc.value.error_code == "invalid_document_id"


def test_metadata_survives_rereading_from_disk(tmp_path: Path, sample_dataset_id: str) -> None:
    """Document metadata and extracted text survive re-reading from disk."""
    pdf_bytes = make_pdf(["Page 1 content for persistent retrieval."])
    meta, _ = save_document(
        dataset_id=sample_dataset_id,
        filename="persistent_manual.pdf",
        content=pdf_bytes,
        base_dir=tmp_path,
    )

    # Re-read via get_document
    loaded_meta = get_document(
        dataset_id=sample_dataset_id,
        document_id=meta.id,
        base_dir=tmp_path,
    )
    assert loaded_meta.id == meta.id
    assert loaded_meta.dataset_id == sample_dataset_id
    assert loaded_meta.filename == "persistent_manual.pdf"
    assert loaded_meta.page_count == 1
    assert loaded_meta.file_type == "pdf"

    # Re-read via list_documents
    doc_list = list_documents(dataset_id=sample_dataset_id, base_dir=tmp_path)
    assert len(doc_list) == 1
    assert doc_list[0].id == meta.id

    # Re-read extracted pages
    loaded_pages = get_document_pages(
        dataset_id=sample_dataset_id,
        document_id=meta.id,
        base_dir=tmp_path,
    )
    assert len(loaded_pages) == 1
    assert loaded_pages[0]["page_number"] == 1
    assert "Page 1 content" in loaded_pages[0]["text"]


def test_delete_document_removes_files(tmp_path: Path, sample_dataset_id: str) -> None:
    """delete_document removes both the document file and metadata JSON from disk."""
    txt_content = b"Temporary document content."
    meta, _ = save_document(
        dataset_id=sample_dataset_id,
        filename="temp.txt",
        content=txt_content,
        base_dir=tmp_path,
    )

    delete_document(dataset_id=sample_dataset_id, document_id=meta.id, base_dir=tmp_path)

    # Subsequent get raises DocumentNotFoundError
    with pytest.raises(DocumentNotFoundError):
        get_document(dataset_id=sample_dataset_id, document_id=meta.id, base_dir=tmp_path)

    assert list_documents(dataset_id=sample_dataset_id, base_dir=tmp_path) == []
