from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetMeta(BaseModel):
    """Metadata for an uploaded tabular dataset."""

    dataset_id: str
    filename: str
    file_size_bytes: int
    row_count: int | None = None
    created_at: str | None = None


class ProfileResponse(BaseModel):
    """Profiling statistics and schema information for a dataset."""

    dataset_id: str
    row_count: int
    col_count: int
    columns: list[str] = Field(default_factory=list)
    dtypes: dict[str, str] = Field(default_factory=dict)
    missing_values: dict[str, int] = Field(default_factory=dict)
    duplicate_rows: int = 0
    numeric_summary: dict[str, dict[str, Any]] = Field(default_factory=dict)


class PreviewResponse(BaseModel):
    """Preview of the first N rows of a dataset."""

    dataset_id: str
    total_rows: int
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error response shape across the entire application."""

    error: str
    message: str
