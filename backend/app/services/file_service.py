from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import settings


class FileValidationError(ValueError):
    """Raised when an uploaded file fails validation."""

    def __init__(self, message: str, error_code: str = "invalid_file") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def to_dict(self) -> dict[str, str]:
        """Return the standard error shape {"error", "message"}."""
        return {"error": self.error_code, "message": self.message}


def validate_filename(filename: str) -> None:
    """Accept .csv files only. Rejects missing, non-string, or unsupported extensions."""
    if not filename or not isinstance(filename, str):
        raise FileValidationError(
            "Filename must be provided as a non-empty string.",
            error_code="invalid_filename",
        )
    clean = filename.strip().lower()
    if not clean.endswith(".csv"):
        raise FileValidationError(
            f"Unsupported file extension for '{filename}'. Only .csv files are supported.",
            error_code="unsupported_file_type",
        )


def validate_dataset_id(dataset_id: Any) -> str:
    """Validate that dataset_id is a valid UUID to prevent path traversal."""
    if not dataset_id:
        raise FileValidationError(
            "dataset_id must be a non-empty string or UUID.",
            error_code="invalid_dataset_id",
        )
    if isinstance(dataset_id, uuid.UUID):
        return str(dataset_id)
    raw = str(dataset_id).strip()
    try:
        parsed = uuid.UUID(raw)
        if str(parsed).lower() != raw.lower():
            raise ValueError("UUID string format mismatch")
        return str(parsed)
    except (ValueError, TypeError, AttributeError) as exc:
        raise FileValidationError(
            f"Invalid dataset_id '{dataset_id}': must be a valid UUID.",
            error_code="invalid_dataset_id",
        ) from exc


def get_dataset_dir(dataset_id: Any, base_dir: Path | str | None = None) -> Path:
    """Resolve and return the directory path for a dataset."""
    clean_id = validate_dataset_id(dataset_id)
    root = Path(base_dir) if base_dir is not None else Path(settings.upload_dir)
    return root / clean_id


def get_dataset_file_path(dataset_id: Any, base_dir: Path | str | None = None) -> Path:
    """Resolve and return the canonical data.csv path for a dataset."""
    return get_dataset_dir(dataset_id, base_dir=base_dir) / "data.csv"


# Alias for callers preferring get_dataset_path
get_dataset_path = get_dataset_file_path


def validate_csv_content(
    content: bytes,
    max_size_mb: int | None = None,
) -> tuple[pd.DataFrame, str]:
    """Validate raw CSV upload content.

    Enforces:
    1. Size limit (default settings.max_upload_size_mb).
    2. Null byte rejection (reject binary files).
    3. Decoding UTF-8 with fallback to Latin-1.
    4. Successful pandas parsing.
    5. Non-empty dataset (must have columns and at least one row).
    """
    limit_mb = max_size_mb if max_size_mb is not None else settings.max_upload_size_mb
    max_size_bytes = limit_mb * 1024 * 1024

    if len(content) > max_size_bytes:
        raise FileValidationError(
            f"File size ({len(content)} bytes) exceeds the {limit_mb} MB limit.",
            error_code="file_too_large",
        )

    if b"\x00" in content:
        raise FileValidationError(
            "File contains null bytes; binary files are not allowed.",
            error_code="null_bytes_detected",
        )

    # Decode UTF-8 (fallback Latin-1)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as exc:
            raise FileValidationError(
                "Unable to decode file content as UTF-8 or Latin-1.",
                error_code="decode_error",
            ) from exc

    if "\x00" in text:
        raise FileValidationError(
            "File contains null bytes; binary files are not allowed.",
            error_code="null_bytes_detected",
        )

    if not text.strip():
        raise FileValidationError(
            "CSV file is empty.",
            error_code="empty_csv",
        )

    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as exc:
        raise FileValidationError(
            f"Failed to parse CSV: {exc}",
            error_code="unparsable_csv",
        ) from exc

    if df.empty or len(df.columns) == 0:
        raise FileValidationError(
            "CSV file is empty or contains no data rows.",
            error_code="empty_csv",
        )

    return df, text


def save_csv_upload(
    content: bytes,
    filename: str,
    base_dir: Path | str | None = None,
    max_size_mb: int | None = None,
) -> str:
    """Validate and save an uploaded CSV file.

    Generates a UUID dataset_id and stores the file at uploads/<dataset_id>/data.csv.
    Never uses the uploaded filename in the storage path.
    Returns the generated dataset_id.
    """
    validate_filename(filename)
    _df, text = validate_csv_content(content, max_size_mb=max_size_mb)

    dataset_id = str(uuid.uuid4())
    target_dir = get_dataset_dir(dataset_id, base_dir=base_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / "data.csv"
    file_path.write_text(text, encoding="utf-8")

    return dataset_id


# Aliases for convenience across services
save_dataset = save_csv_upload
save_csv_file = save_csv_upload


def read_dataset(dataset_id: Any, base_dir: Path | str | None = None) -> pd.DataFrame:
    """Read a stored dataset CSV by dataset_id."""
    file_path = get_dataset_file_path(dataset_id, base_dir=base_dir)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset '{dataset_id}' not found at {file_path}")
    return pd.read_csv(file_path)
