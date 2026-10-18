from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, File, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import limiter, read_stream_limited
from app.schemas.document import DocumentListResponse, DocumentMeta
from app.services import retrieval_service
from app.services.chunking_service import ChunkingError, chunk_document_pages
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentValidationError,
    get_docs_dir,
    get_document,
    list_documents,
    save_document,
    validate_dataset_id,
    validate_document_id,
)
from app.services.document_service import (
    delete_document as delete_document_files,
)
from app.services.embedding_service import EmbeddingError
from app.services.file_service import (
    FileValidationError,
    get_dataset_file_path,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["documents"])


@router.post(
    "/{id}/documents",
    response_model=DocumentMeta,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a reference document (PDF or TXT)",
)
@limiter.limit(lambda: settings.rate_limit_document_upload)
async def upload_document(
    request: Request,
    id: str,
    file: UploadFile = File(...),  # noqa: B008
) -> Any:
    """Validate, store, chunk, embed, and index an uploaded document for a dataset."""
    # 1. Validate dataset_id as a UUID
    try:
        clean_ds_id = validate_dataset_id(id)
    except (DocumentValidationError, FileValidationError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    # 2. Verify dataset exists
    csv_path = get_dataset_file_path(clean_ds_id)
    if not csv_path.exists():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )

    # 3. Filename check
    if not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_filename", "message": "No filename was provided."},
        )

    # 4. Save and extract document content and page text
    try:
        max_bytes = settings.max_document_size_mb * 1024 * 1024
        content = await read_stream_limited(file, max_bytes=max_bytes)
        meta, pages = save_document(
            dataset_id=clean_ds_id,
            filename=file.filename,
            content=content,
        )
    except (DocumentValidationError, FileValidationError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )
    except Exception:
        logger.exception("Unexpected error saving document.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "Failed to save document."},
        )

    # 5. Chunk, embed, index into Chroma, and update saved metadata
    try:
        chunks = chunk_document_pages(
            pages=pages,
            dataset_id=clean_ds_id,
            document_id=meta.id,
            filename=meta.filename,
        )
        retrieval_service.index_chunks(chunks)

        # Update metadata JSON on disk to status 'indexed' and update chunk_count
        docs_dir = get_docs_dir(clean_ds_id)
        meta_path = docs_dir / f"{meta.id}.meta.json"
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data["metadata"]["status"] = "indexed"
        data["metadata"]["chunk_count"] = len(chunks)
        meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return DocumentMeta.model_validate(data["metadata"])

    except Exception as exc:  # noqa: BLE001
        logger.warning("Document processing failed for %s: %s", meta.id, type(exc).__name__)
        # Cleanup: remove saved file, metadata, and any partial vectors
        try:
            delete_document_files(clean_ds_id, meta.id)
        except Exception:
            logger.exception("Failed to clean up document files after indexing error.")

        try:
            retrieval_service.delete_document(clean_ds_id, meta.id)
        except Exception:
            logger.exception("Failed to clean up vectors after indexing error.")

        if isinstance(exc, ChunkingError):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"error": exc.error_code, "message": exc.message},
            )
        if isinstance(exc, EmbeddingError):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "embedding_unavailable",
                    "message": "Embedding service is temporarily unavailable.",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "Failed to process and index document."},
        )


@router.get(
    "/{id}/documents",
    response_model=DocumentListResponse,
    summary="List all documents associated with a dataset",
)
async def list_documents_endpoint(id: str) -> Any:
    """Return all indexed documents for a dataset from disk."""
    try:
        clean_ds_id = validate_dataset_id(id)
    except (DocumentValidationError, FileValidationError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    csv_path = get_dataset_file_path(clean_ds_id)
    if not csv_path.exists():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )

    docs = list_documents(clean_ds_id)
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete(
    "/{id}/documents/{doc_id}",
    summary="Delete a document, its files, metadata, and vectors",
)
async def delete_document_endpoint(id: str, doc_id: str) -> Any:
    """Delete a document, its disk files, metadata, and Chroma vectors."""
    try:
        clean_ds_id = validate_dataset_id(id)
    except (DocumentValidationError, FileValidationError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    try:
        clean_doc_id = validate_document_id(doc_id)
    except DocumentValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    csv_path = get_dataset_file_path(clean_ds_id)
    if not csv_path.exists():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )

    try:
        get_document(clean_ds_id, clean_doc_id)
    except DocumentNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Document '{doc_id}' not found."},
        )

    # Delete Chroma vectors and disk files
    retrieval_service.delete_document(clean_ds_id, clean_doc_id)
    delete_document_files(clean_ds_id, clean_doc_id)

    return {
        "status": "deleted",
        "dataset_id": clean_ds_id,
        "document_id": clean_doc_id,
        "message": "Document deleted successfully.",
    }
