from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import limiter, read_stream_limited
from app.schemas.dataset import DatasetMeta, PreviewResponse, ProfileResponse
from app.services import retrieval_service
from app.services.file_service import (
    FileValidationError,
    delete_dataset,
    get_dataset_meta,
    read_dataset,
    save_csv_upload,
    validate_dataset_id,
)
from app.services.profiling_service import get_dataset_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "",
    response_model=DatasetMeta,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new CSV dataset",
)
@router.post(
    "/",
    response_model=DatasetMeta,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@limiter.limit(lambda: settings.rate_limit_dataset_upload)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
) -> Any:
    """Upload and validate a CSV dataset. Persists data and metadata to disk."""
    if not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_filename", "message": "No filename was provided."},
        )

    try:
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        content = await read_stream_limited(file, max_bytes=max_bytes)
        dataset_id = save_csv_upload(content=content, filename=file.filename)
        meta = get_dataset_meta(dataset_id)
        return meta
    except FileValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )
    except Exception:
        logger.exception("Unexpected error while saving upload.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "Failed to process upload."},
        )


@router.get(
    "/{id}/profile",
    response_model=ProfileResponse,
    summary="Get profiling statistics for a dataset",
)
async def get_profile(id: str) -> Any:
    """Return statistical profile and schema information for the dataset."""
    try:
        clean_id = validate_dataset_id(id)
    except FileValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    try:
        return get_dataset_profile(clean_id)
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )


@router.get(
    "/{id}/preview",
    response_model=PreviewResponse,
    summary="Preview first 100 rows of a dataset",
)
async def get_preview(id: str) -> Any:
    """Return preview rows (up to 100) and column names for the dataset."""
    try:
        clean_id = validate_dataset_id(id)
    except FileValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    try:
        df = read_dataset(clean_id)
        preview_df = df.head(100)
        # Replace NaN/null values with None for compliant JSON serialization
        preview_df = preview_df.where(pd.notnull(preview_df), None)
        rows = preview_df.to_dict(orient="records")

        return PreviewResponse(
            dataset_id=clean_id,
            total_rows=int(df.shape[0]),
            columns=[str(col) for col in df.columns],
            rows=rows,
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )


@router.delete(
    "/{id}",
    summary="Delete a dataset and its stored files",
)
async def delete_dataset_endpoint(id: str) -> Any:
    """Delete a dataset and its entire storage folder from disk."""
    try:
        clean_id = validate_dataset_id(id)
    except FileValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    try:
        delete_dataset(clean_id)
        retrieval_service.delete_dataset(clean_id)
        return {
            "status": "deleted",
            "dataset_id": clean_id,
            "message": "Dataset deleted successfully.",
        }
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )
