from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf

from app.core.config import settings
from app.schemas.document import DocumentMeta

logger = logging.getLogger(__name__)


class DocumentValidationError(ValueError):
    """Raised when an uploaded document fails validation."""

    def __init__(self, message: str, error_code: str = "invalid_document") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def to_dict(self) -> dict[str, str]:
        """Return the standard error shape {"error", "message"}."""
        return {"error": self.error_code, "message": self.message}


class DocumentNotFoundError(FileNotFoundError):
    """Raised when a requested document does not exist."""

    def __init__(self, message: str = "Document not found.") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = "not_found"

    def to_dict(self) -> dict[str, str]:
        """Return the standard error shape {"error", "message"}."""
        return {"error": self.error_code, "message": self.message}


def validate_uuid_id(value: Any, field_name: str = "id") -> str:
    """Validate that a string or UUID is a valid UUID to prevent path traversal."""
    if not value:
        raise DocumentValidationError(
            f"{field_name} must be a non-empty string or UUID.",
            error_code=f"invalid_{field_name}",
        )
    if isinstance(value, uuid.UUID):
        return str(value)
    raw = str(value).strip()
    try:
        parsed = uuid.UUID(raw)
        if str(parsed).lower() != raw.lower():
            raise ValueError("UUID string format mismatch")
        return str(parsed)
    except (ValueError, TypeError, AttributeError) as exc:
        raise DocumentValidationError(
            f"Invalid {field_name} '{value}': must be a valid UUID.",
            error_code=f"invalid_{field_name}",
        ) from exc


def validate_dataset_id(dataset_id: Any) -> str:
    """Validate that dataset_id is a valid UUID."""
    return validate_uuid_id(dataset_id, "dataset_id")


def validate_document_id(document_id: Any) -> str:
    """Validate that document_id is a valid UUID."""
    return validate_uuid_id(document_id, "document_id")


def get_docs_dir(dataset_id: Any, base_dir: Path | str | None = None) -> Path:
    """Return the resolved storage directory uploads/<dataset_id>/docs/."""
    clean_ds_id = validate_dataset_id(dataset_id)
    root = Path(base_dir or settings.upload_dir).resolve()
    return root / clean_ds_id / "docs"


def save_document(
    dataset_id: str,
    filename: str,
    content: bytes,
    base_dir: Path | str | None = None,
) -> tuple[DocumentMeta, list[dict[str, Any]]]:
    """Validate, extract text from, and persist an uploaded PDF or TXT document.

    Enforces:
    - Accepts .pdf and .txt only.
    - Size limit: settings.max_document_size_mb.
    - PDF: requires %PDF- header; rejects encrypted, corrupt, over-page-limit,
      or image-only PDFs ('No extractable text. Only text-based PDFs are supported.').
    - TXT: decodes UTF-8 (fallback latin-1); rejects null bytes and empty files.
    - Extracts text per page (TXT treated as page 1).
    - Generates server-side UUID document_id; never uses uploaded filename for storage.
    - Persists file and metadata JSON on disk.

    Returns:
        (DocumentMeta, list of page dicts [{"page_number": int, "text": str}])
    """
    clean_ds_id = validate_dataset_id(dataset_id)

    # 1. Filename validation and extension check
    if not filename or not isinstance(filename, str):
        raise DocumentValidationError(
            "Filename must be provided as a non-empty string.",
            error_code="invalid_filename",
        )
    clean_name = filename.strip()
    lower_name = clean_name.lower()
    if lower_name.endswith(".pdf"):
        file_type = "pdf"
    elif lower_name.endswith(".txt"):
        file_type = "txt"
    else:
        raise DocumentValidationError(
            f"Unsupported file type for '{filename}'. Only .pdf and .txt files are supported.",
            error_code="unsupported_file_type",
        )

    # 2. File size validation
    max_bytes = settings.max_document_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise DocumentValidationError(
            f"File size ({len(content)} bytes) exceeds maximum limit of {settings.max_document_size_mb} MB.",
            error_code="file_too_large",
        )
    if len(content) == 0:
        raise DocumentValidationError(
            "Uploaded file is empty (0 bytes).",
            error_code="empty_file",
        )

    # 3. Document text extraction per page
    pages: list[dict[str, Any]] = []

    if file_type == "pdf":
        if not content.startswith(b"%PDF-"):
            raise DocumentValidationError(
                "Invalid PDF file: Missing %PDF- header.",
                error_code="corrupt_pdf",
            )
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
        except Exception as exc:
            logger.warning("Failed to open PDF file: %s", type(exc).__name__)
            raise DocumentValidationError(
                "Failed to open or parse PDF file. The file may be corrupt or invalid.",
                error_code="corrupt_pdf",
            ) from exc

        try:
            if doc.is_encrypted:
                raise DocumentValidationError(
                    "Encrypted or password-protected PDFs are not supported.",
                    error_code="encrypted_pdf",
                )

            page_count = len(doc)
            if page_count == 0:
                raise DocumentValidationError(
                    "PDF file has 0 pages.",
                    error_code="empty_file",
                )
            if page_count > settings.max_pdf_pages:
                raise DocumentValidationError(
                    f"PDF page count ({page_count}) exceeds maximum limit of {settings.max_pdf_pages} pages.",
                    error_code="too_many_pages",
                )

            total_chars = 0
            for idx in range(page_count):
                page = doc[idx]
                text = page.get_text() or ""
                clean_page_text = text.strip()
                total_chars += len(clean_page_text)
                pages.append({"page_number": idx + 1, "text": clean_page_text})

            # Check if text was extractable across all pages (e.g. image-only PDF)
            total_extracted = "".join(p["text"] for p in pages).strip()
            if not total_extracted:
                raise DocumentValidationError(
                    "No extractable text. Only text-based PDFs are supported.",
                    error_code="no_text_content",
                )

            if total_chars > settings.max_extracted_chars:
                raise DocumentValidationError(
                    f"Extracted text length ({total_chars}) exceeds limit of {settings.max_extracted_chars} characters.",
                    error_code="document_too_long",
                )
        finally:
            doc.close()

    else:  # txt
        if b"\x00" in content:
            raise DocumentValidationError(
                "Text file contains invalid null bytes (binary content rejected).",
                error_code="binary_file_rejected",
            )
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                decoded = content.decode("latin-1")
            except Exception as exc:
                raise DocumentValidationError(
                    "Failed to decode text file as UTF-8 or latin-1.",
                    error_code="decode_error",
                ) from exc

        clean_text = decoded.strip()
        if not clean_text:
            raise DocumentValidationError(
                "Text file is empty or whitespace only.",
                error_code="empty_file",
            )

        if len(clean_text) > settings.max_extracted_chars:
            raise DocumentValidationError(
                f"Text length ({len(clean_text)}) exceeds limit of {settings.max_extracted_chars} characters.",
                error_code="document_too_long",
            )

        pages = [{"page_number": 1, "text": clean_text}]

    # 4. Generate server-side UUID document_id and persist
    document_id = str(uuid.uuid4())
    docs_dir = get_docs_dir(clean_ds_id, base_dir=base_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Store raw document with UUID filename
    doc_path = docs_dir / f"{document_id}.{file_type}"
    doc_path.write_bytes(content)

    meta = DocumentMeta(
        id=document_id,
        dataset_id=clean_ds_id,
        filename=clean_name,
        file_type=file_type,
        status="uploaded",
        page_count=len(pages),
        chunk_count=0,
        created_at=datetime.now(UTC),
    )

    # Store metadata and extracted pages in companion JSON file
    meta_path = docs_dir / f"{document_id}.meta.json"
    meta_payload = {
        "metadata": meta.model_dump(mode="json"),
        "pages": pages,
    }
    meta_path.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")

    return meta, pages


def get_document(
    dataset_id: str,
    document_id: str,
    base_dir: Path | str | None = None,
) -> DocumentMeta:
    """Retrieve document metadata from disk."""
    clean_ds_id = validate_dataset_id(dataset_id)
    clean_doc_id = validate_document_id(document_id)
    docs_dir = get_docs_dir(clean_ds_id, base_dir=base_dir)
    meta_path = docs_dir / f"{clean_doc_id}.meta.json"

    if not meta_path.exists():
        raise DocumentNotFoundError(f"Document '{clean_doc_id}' not found.")

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return DocumentMeta.model_validate(data["metadata"])


def get_document_pages(
    dataset_id: str,
    document_id: str,
    base_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve extracted page contents for a document from disk."""
    clean_ds_id = validate_dataset_id(dataset_id)
    clean_doc_id = validate_document_id(document_id)
    docs_dir = get_docs_dir(clean_ds_id, base_dir=base_dir)
    meta_path = docs_dir / f"{clean_doc_id}.meta.json"

    if not meta_path.exists():
        raise DocumentNotFoundError(f"Document '{clean_doc_id}' not found.")

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return data.get("pages", [])


def list_documents(
    dataset_id: str,
    base_dir: Path | str | None = None,
) -> list[DocumentMeta]:
    """List all documents for a dataset sorted by created_at."""
    clean_ds_id = validate_dataset_id(dataset_id)
    docs_dir = get_docs_dir(clean_ds_id, base_dir=base_dir)
    if not docs_dir.exists():
        return []

    docs: list[DocumentMeta] = []
    for meta_file in docs_dir.glob("*.meta.json"):
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            docs.append(DocumentMeta.model_validate(data["metadata"]))
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            logger.warning("Failed to parse metadata file %s: %s", meta_file, exc)

    docs.sort(key=lambda d: d.created_at)
    return docs


def delete_document(
    dataset_id: str,
    document_id: str,
    base_dir: Path | str | None = None,
) -> None:
    """Delete document content and metadata files from disk."""
    clean_ds_id = validate_dataset_id(dataset_id)
    clean_doc_id = validate_document_id(document_id)
    docs_dir = get_docs_dir(clean_ds_id, base_dir=base_dir)
    meta_path = docs_dir / f"{clean_doc_id}.meta.json"

    if not meta_path.exists():
        raise DocumentNotFoundError(f"Document '{clean_doc_id}' not found.")

    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        file_type = data.get("metadata", {}).get("file_type", "")
        doc_file = docs_dir / f"{clean_doc_id}.{file_type}"
        if doc_file.exists():
            doc_file.unlink()
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        logger.warning("Failed to delete document file for %s: %s", clean_doc_id, exc)

    meta_path.unlink()
