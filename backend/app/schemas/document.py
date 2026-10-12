from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentMeta(BaseModel):
    """Metadata representing an uploaded document."""

    id: str
    dataset_id: str
    filename: str
    file_type: Literal["pdf", "txt"]
    status: str = "uploaded"
    page_count: int = 1
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Citation(BaseModel):
    """Source citation referencing evidence retrieved from an uploaded document."""

    document_id: str
    filename: str
    page_number: int | None = None
    chunk_index: int
    snippet: str


class DocumentListResponse(BaseModel):
    """List response for documents associated with a dataset."""

    documents: list[DocumentMeta] = Field(default_factory=list)
    total: int = 0
