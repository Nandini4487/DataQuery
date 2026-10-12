from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


class ChunkingError(ValueError):
    """Raised when document chunking fails or exceeds configured limits."""

    def __init__(self, message: str, error_code: str = "chunking_error") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def to_dict(self) -> dict[str, str]:
        """Return the standard error shape {"error", "message"}."""
        return {"error": self.error_code, "message": self.message}


@dataclass(frozen=True)
class DocumentChunk:
    """A single text chunk extracted from a document page."""

    text: str
    dataset_id: str
    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int


def chunk_document_pages(
    pages: list[dict[str, Any]],
    dataset_id: str,
    document_id: str,
    filename: str,
    chunk_size_words: int | None = None,
    chunk_overlap_words: int | None = None,
    max_chunks: int | None = None,
) -> list[DocumentChunk]:
    """Split extracted pages into overlapping chunks measured in words.

    Words are used as an approximation of SPEC's 500-800 token target.
    A chunk never spans across two pages.
    Chunk indices run continuously across the entire document.
    Empty or whitespace-only chunks are skipped.
    Enforces max_chunks_per_document limit.
    """
    size = chunk_size_words if chunk_size_words is not None else settings.chunk_size_words
    overlap = chunk_overlap_words if chunk_overlap_words is not None else settings.chunk_overlap_words
    max_allowed = max_chunks if max_chunks is not None else settings.max_chunks_per_document

    if size <= 0:
        raise ChunkingError("chunk_size_words must be greater than 0.")
    if overlap < 0:
        raise ChunkingError("chunk_overlap_words must be non-negative.")
    if overlap >= size:
        raise ChunkingError(
            f"chunk_overlap_words ({overlap}) must be strictly less than chunk_size_words ({size})."
        )

    step = size - overlap
    chunks: list[DocumentChunk] = []
    current_chunk_index = 0

    for page_info in pages:
        page_num = page_info.get("page_number")
        raw_text = page_info.get("text", "")
        if not raw_text or not isinstance(raw_text, str):
            continue

        words = raw_text.split()
        if not words:
            continue

        start = 0
        total_words = len(words)

        while start < total_words:
            end = min(start + size, total_words)
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words).strip()

            if chunk_text:
                if len(chunks) >= max_allowed:
                    raise ChunkingError(
                        f"Document produces more chunks than the limit of {max_allowed} chunks.",
                        error_code="too_many_chunks",
                    )

                chunk = DocumentChunk(
                    text=chunk_text,
                    dataset_id=dataset_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=page_num,
                    chunk_index=current_chunk_index,
                )
                chunks.append(chunk)
                current_chunk_index += 1

            if end >= total_words:
                break
            start += step

    return chunks
