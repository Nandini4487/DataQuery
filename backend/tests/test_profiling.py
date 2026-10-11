from __future__ import annotations

import io
import uuid
from pathlib import Path

import pandas as pd
import pytest

from app.services.file_service import save_csv_upload
from app.services.profiling_service import compute_profile, get_dataset_profile


def test_profiling_spec_sample_dataset(sample_csv_text: str) -> None:
    """Verify SPEC section 7.6 sample dataset metrics: 4 rows, 3 cols, correct dtypes and summary."""
    df = pd.read_csv(io.StringIO(sample_csv_text))
    dataset_id = str(uuid.uuid4())
    profile = compute_profile(df, dataset_id)

    # Core row and column counts
    assert profile.row_count == 4
    assert profile.col_count == 3
    assert profile.columns == ["product", "city", "revenue"]

    # Inferred data types
    assert profile.dtypes["revenue"] in ("int64", "int32")
    assert profile.dtypes["product"] in ("object", "string", "str")
    assert profile.dtypes["city"] in ("object", "string", "str")

    # Missing values and duplicates
    assert profile.missing_values == {"product": 0, "city": 0, "revenue": 0}
    assert profile.duplicate_rows == 0

    # Numeric summary for revenue: min=40000, max=80000, mean=60000.0
    assert "revenue" in profile.numeric_summary
    rev_summary = profile.numeric_summary["revenue"]
    assert rev_summary["min"] == 40000
    assert rev_summary["max"] == 80000
    assert rev_summary["mean"] == 60000.0


def test_profiling_from_disk(tmp_upload_dir: Path, sample_csv_bytes: bytes) -> None:
    """Load dataset from disk by dataset_id and verify profiling output."""
    dataset_id = save_csv_upload(sample_csv_bytes, "acceptance.csv")
    profile = get_dataset_profile(dataset_id)

    assert profile.dataset_id == dataset_id
    assert profile.row_count == 4
    assert profile.col_count == 3
    assert "revenue" in profile.numeric_summary


def test_profiling_with_missing_and_duplicates() -> None:
    """Verify missing values and duplicate rows detection."""
    df = pd.DataFrame(
        {
            "num": [10, 20, 20, None],
            "label": ["A", "B", "B", "C"],
        }
    )
    profile = compute_profile(df, "test-id")

    assert profile.row_count == 4
    assert profile.col_count == 2
    assert profile.missing_values["num"] == 1
    assert profile.missing_values["label"] == 0
    assert profile.duplicate_rows == 1
    assert profile.numeric_summary["num"]["min"] == 10
    assert profile.numeric_summary["num"]["max"] == 20
    assert profile.numeric_summary["num"]["mean"] == pytest.approx(16.6667, rel=1e-3)


def test_profiling_nonexistent_dataset_raises_not_found(tmp_upload_dir: Path) -> None:
    """Querying a non-existent dataset on disk should raise FileNotFoundError."""
    random_id = str(uuid.uuid4())
    with pytest.raises(FileNotFoundError):
        get_dataset_profile(random_id)
