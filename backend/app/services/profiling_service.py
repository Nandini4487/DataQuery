from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.schemas.dataset import ProfileResponse
from app.services.file_service import read_dataset, validate_dataset_id


def compute_profile(df: pd.DataFrame, dataset_id: str) -> ProfileResponse:
    """Compute profiling statistics and schema metadata for a DataFrame."""
    row_count = int(df.shape[0])
    col_count = int(df.shape[1])
    columns = [str(col) for col in df.columns]
    dtypes = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    missing_values = {str(col): int(df[col].isna().sum()) for col in df.columns}
    duplicate_rows = int(df.duplicated().sum())

    numeric_summary: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            non_null = df[col].dropna()
            if len(non_null) > 0:
                col_min = non_null.min()
                col_max = non_null.max()
                col_mean = non_null.mean()

                is_int = pd.api.types.is_integer_dtype(df[col])
                numeric_summary[str(col)] = {
                    "min": int(col_min) if is_int else float(col_min),
                    "max": int(col_max) if is_int else float(col_max),
                    "mean": float(col_mean),
                }
            else:
                numeric_summary[str(col)] = {
                    "min": None,
                    "max": None,
                    "mean": None,
                }

    return ProfileResponse(
        dataset_id=dataset_id,
        row_count=row_count,
        col_count=col_count,
        columns=columns,
        dtypes=dtypes,
        missing_values=missing_values,
        duplicate_rows=duplicate_rows,
        numeric_summary=numeric_summary,
    )


def get_dataset_profile(
    dataset_id: str | uuid.UUID,
    base_dir: Path | str | None = None,
) -> ProfileResponse:
    """Load dataset from disk and compute its profile."""
    clean_id = validate_dataset_id(dataset_id)
    df = read_dataset(clean_id, base_dir=base_dir)
    return compute_profile(df, clean_id)


# Alias for callers preferring profile_dataset
profile_dataset = get_dataset_profile
