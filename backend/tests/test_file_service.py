from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.schemas.answer import AnswerResponse
from app.schemas.dataset import (
    DatasetMeta,
    ErrorResponse,
    PreviewResponse,
    ProfileResponse,
)
from app.schemas.query import AnalysisPlan, FilterCondition, PlanResult, SortInstruction
from app.services.file_service import (
    FileValidationError,
    get_dataset_dir,
    get_dataset_file_path,
    read_dataset,
    save_csv_upload,
    validate_csv_content,
    validate_dataset_id,
    validate_filename,
)


def test_valid_csv_accepted(tmp_upload_dir: Path, sample_csv_bytes: bytes) -> None:
    """Valid CSV should be saved to uploads/<dataset_id>/data.csv and return a UUID."""
    dataset_id = save_csv_upload(sample_csv_bytes, "acceptance.csv")

    # dataset_id must be a valid UUID string
    parsed_uuid = uuid.UUID(dataset_id)
    assert str(parsed_uuid) == dataset_id

    # The file path must exist at uploads/<dataset_id>/data.csv
    file_path = tmp_upload_dir / dataset_id / "data.csv"
    assert file_path.exists()
    assert file_path.is_file()

    # Read back through helper and verify data
    df = read_dataset(dataset_id)
    assert len(df) == 4
    assert list(df.columns) == ["product", "city", "revenue"]
    assert df["revenue"].sum() == 240000


def test_null_bytes_rejected(tmp_upload_dir: Path) -> None:
    """Files containing null bytes must be rejected as binary files."""
    bad_bytes = b"product,city,revenue\nLaptop\x00,Delhi,80000\n"

    with pytest.raises(FileValidationError) as exc_info:
        save_csv_upload(bad_bytes, "null_test.csv")

    assert exc_info.value.error_code == "null_bytes_detected"
    assert "null bytes" in str(exc_info.value)
    assert exc_info.value.to_dict() == {
        "error": "null_bytes_detected",
        "message": exc_info.value.message,
    }


def test_oversized_file_rejected(tmp_upload_dir: Path) -> None:
    """Files exceeding the upload limit must be rejected."""
    # Test with custom small limit of 1 MB
    oversized_bytes = b"a,b\n1,2\n" + (b"x" * (1 * 1024 * 1024 + 1))

    with pytest.raises(FileValidationError) as exc_info:
        save_csv_upload(oversized_bytes, "oversized.csv", max_size_mb=1)

    assert exc_info.value.error_code == "file_too_large"
    assert "exceeds" in str(exc_info.value)


def test_wrong_extension_rejected() -> None:
    """Only .csv files may be accepted; other extensions must be rejected."""
    invalid_filenames = [
        "data.xlsx",
        "data.txt",
        "data.csv.exe",
        "data.json",
        "data",
        "",
    ]
    for name in invalid_filenames:
        with pytest.raises(FileValidationError):
            validate_filename(name)


def test_unparsable_csv_rejected() -> None:
    """Malformed CSV data that pandas cannot parse must be rejected."""
    # Unclosed quote with irregular line structure
    malformed_csv = b'col1,col2\n"unclosed quote line\n1,2,3,4,5\n'

    with pytest.raises(FileValidationError) as exc_info:
        validate_csv_content(malformed_csv)

    assert exc_info.value.error_code in ("unparsable_csv", "empty_csv")


def test_empty_csv_rejected() -> None:
    """Empty files, whitespace-only files, or header-only CSVs must be rejected."""
    # Completely empty bytes
    with pytest.raises(FileValidationError) as exc1:
        validate_csv_content(b"")
    assert exc1.value.error_code == "empty_csv"

    # Whitespace only
    with pytest.raises(FileValidationError) as exc2:
        validate_csv_content(b"   \n  \n   \t  ")
    assert exc2.value.error_code == "empty_csv"

    # Header only, no rows
    with pytest.raises(FileValidationError) as exc3:
        validate_csv_content(b"product,city,revenue\n")
    assert exc3.value.error_code == "empty_csv"


def test_non_uuid_dataset_id_rejected() -> None:
    """Non-UUID identifiers and path traversal attempts must be rejected."""
    invalid_ids = [
        "../etc/passwd",
        "../../uploads",
        "12345",
        "not-a-uuid",
        "",
        "   ",
        "123e4567-e89b-12d3-a456-426614174000/extra",
    ]
    for bad_id in invalid_ids:
        with pytest.raises(FileValidationError) as exc_info:
            validate_dataset_id(bad_id)
        assert exc_info.value.error_code == "invalid_dataset_id"


def test_valid_uuid_dataset_id_accepted() -> None:
    """Valid UUID strings or uuid.UUID instances must be accepted."""
    test_uuid = uuid.uuid4()
    assert validate_dataset_id(str(test_uuid)) == str(test_uuid)
    assert validate_dataset_id(test_uuid) == str(test_uuid)


def test_latin1_fallback_accepted(tmp_upload_dir: Path) -> None:
    """CSV encoded in Latin-1 should decode cleanly and save."""
    # Byte \xe9 is 'é' in Latin-1, which is invalid standalone UTF-8
    latin1_content = "product,city,revenue\nCaf\xe9,Paris,100\n".encode("latin-1")
    dataset_id = save_csv_upload(latin1_content, "cafe.csv")

    df = read_dataset(dataset_id)
    assert len(df) == 1
    assert df.iloc[0]["product"] == "Café"


def test_path_traversal_prevention_in_file_paths(tmp_upload_dir: Path) -> None:
    """Path helpers should reject path traversal attempts."""
    traversal_id = "../../malicious"
    with pytest.raises(FileValidationError):
        get_dataset_dir(traversal_id)

    with pytest.raises(FileValidationError):
        get_dataset_file_path(traversal_id)


def test_schemas_instantiation() -> None:
    """Verify all required schemas instantiate with expected fields and defaults."""
    # 1. Dataset schemas
    meta = DatasetMeta(
        dataset_id=str(uuid.uuid4()),
        filename="sales.csv",
        file_size_bytes=1024,
    )
    assert meta.filename == "sales.csv"

    profile = ProfileResponse(
        dataset_id=meta.dataset_id,
        row_count=4,
        col_count=3,
        columns=["product", "city", "revenue"],
        dtypes={"revenue": "int64"},
    )
    assert profile.row_count == 4

    preview = PreviewResponse(
        dataset_id=meta.dataset_id,
        total_rows=4,
        columns=["product", "city", "revenue"],
        rows=[{"product": "Laptop", "city": "Delhi", "revenue": 80000}],
    )
    assert len(preview.rows) == 1

    err = ErrorResponse(error="invalid_file", message="File is invalid")
    assert err.error == "invalid_file"
    assert err.message == "File is invalid"

    # 2. Query schemas
    plan = AnalysisPlan(
        operation="aggregate",
        columns=["revenue"],
        filters=[FilterCondition(column="city", operator="eq", value="Delhi")],
        group_by=[],
        agg="sum",
        sort=SortInstruction(column="revenue", direction="desc"),
        limit=10,
    )
    assert plan.agg == "sum"
    assert plan.operation == "aggregate"

    result = PlanResult(
        columns=["revenue"],
        rows=[{"revenue": 120000}],
        row_count=1,
    )
    assert result.row_count == 1

    # 3. Answer schemas
    answer = AnswerResponse(
        answer_text="Total revenue is 240000.",
        table={"columns": ["total"], "rows": [{"total": 240000}]},
        chart_spec={"type": "scalar"},
    )
    assert answer.citations == []
    assert answer.answer_text == "Total revenue is 240000."
