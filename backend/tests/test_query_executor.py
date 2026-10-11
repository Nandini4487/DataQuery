from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from app.schemas.query import AnalysisPlan, FilterCondition, SortInstruction
from app.services.chart_service import infer_chart_spec
from app.services.file_service import save_csv_upload
from app.services.query_executor import execute_plan, execute_query


def test_total_revenue(sample_csv_text: str) -> None:
    """SPEC section 7.6 expected value: total revenue = 240000."""
    df = pd.read_csv(io.StringIO(sample_csv_text))
    plan = AnalysisPlan(
        operation="aggregate",
        columns=["revenue"],
        agg="sum",
    )
    result = execute_query(df=df, plan=plan)

    assert result["columns"] == ["revenue"]
    assert len(result["rows"]) == 1
    assert result["rows"][0]["revenue"] == 240000


def test_laptop_revenue(sample_csv_text: str) -> None:
    """SPEC section 7.6 expected value: Laptop revenue = 150000."""
    df = pd.read_csv(io.StringIO(sample_csv_text))
    plan = AnalysisPlan(
        operation="aggregate",
        columns=["revenue"],
        agg="sum",
        filters=[
            FilterCondition(column="product", operator="eq", value="Laptop"),
        ],
    )
    result = execute_query(df=df, plan=plan)

    assert result["columns"] == ["revenue"]
    assert len(result["rows"]) == 1
    assert result["rows"][0]["revenue"] == 150000


def test_phone_revenue(sample_csv_text: str) -> None:
    """SPEC section 7.6 expected value: Phone revenue = 90000."""
    df = pd.read_csv(io.StringIO(sample_csv_text))
    plan = AnalysisPlan(
        operation="aggregate",
        columns=["revenue"],
        agg="sum",
        filters=[
            FilterCondition(column="product", operator="eq", value="Phone"),
        ],
    )
    result = execute_query(df=df, plan=plan)

    assert result["columns"] == ["revenue"]
    assert len(result["rows"]) == 1
    assert result["rows"][0]["revenue"] == 90000


def test_top_product_by_revenue(sample_csv_text: str) -> None:
    """SPEC section 7.6 expected value: highest-revenue product = Laptop."""
    df = pd.read_csv(io.StringIO(sample_csv_text))
    plan = AnalysisPlan(
        operation="group_by",
        columns=["revenue"],
        group_by=["product"],
        agg="sum",
        sort=SortInstruction(column="revenue", direction="desc"),
        limit=1,
    )
    result = execute_query(df=df, plan=plan)

    assert len(result["rows"]) == 1
    assert result["rows"][0]["product"] == "Laptop"
    assert result["rows"][0]["revenue"] == 150000

    # Also test top_n operation
    top_n_plan = AnalysisPlan(
        operation="top_n",
        columns=["revenue"],
        group_by=["product"],
        agg="sum",
        limit=1,
    )
    top_result = execute_query(df=df, plan=top_n_plan)
    assert top_result["rows"][0]["product"] == "Laptop"
    assert top_result["rows"][0]["revenue"] == 150000


def test_row_count(sample_csv_text: str) -> None:
    """SPEC section 7.6 expected value: row count = 4."""
    df = pd.read_csv(io.StringIO(sample_csv_text))
    # Count operation
    count_plan = AnalysisPlan(operation="count")
    result = execute_query(df=df, plan=count_plan)

    assert result["rows"][0]["count"] == 4

    # Filter with no conditions returns 4 rows
    filter_plan = AnalysisPlan(operation="filter")
    filter_result = execute_query(df=df, plan=filter_plan)
    assert filter_result["row_count"] == 4
    assert len(filter_result["rows"]) == 4


def test_chart_type_scalar() -> None:
    """Single value result should produce a scalar chart spec."""
    result = {
        "columns": ["revenue"],
        "rows": [{"revenue": 240000}],
        "row_count": 1,
    }
    spec = infer_chart_spec(result)

    assert spec["type"] == "scalar"
    assert spec["x"] is None
    assert spec["y"] == "revenue"
    assert spec["data"] == [{"revenue": 240000}]


def test_chart_type_bar() -> None:
    """Grouped categorical aggregation should produce a bar chart spec."""
    result = {
        "columns": ["product", "revenue"],
        "rows": [
            {"product": "Laptop", "revenue": 150000},
            {"product": "Phone", "revenue": 90000},
        ],
        "row_count": 2,
    }
    spec = infer_chart_spec(result)

    assert spec["type"] == "bar"
    assert spec["x"] == "product"
    assert spec["y"] == "revenue"
    assert len(spec["data"]) == 2


def test_chart_type_line() -> None:
    """Time-series data should produce a line chart spec."""
    result = {
        "columns": ["date", "revenue"],
        "rows": [
            {"date": "2026-01-01", "revenue": 80000},
            {"date": "2026-01-02", "revenue": 50000},
            {"date": "2026-01-03", "revenue": 70000},
        ],
        "row_count": 3,
    }
    spec = infer_chart_spec(result)

    assert spec["type"] == "line"
    assert spec["x"] == "date"
    assert spec["y"] == "revenue"
    assert len(spec["data"]) == 3


def test_execute_plan_from_disk(
    tmp_upload_dir: Path,
    sample_csv_bytes: bytes,
) -> None:
    """Verify executing plan directly from stored dataset_id on disk."""
    dataset_id = save_csv_upload(sample_csv_bytes, "acceptance.csv")

    plan = AnalysisPlan(
        operation="group_by",
        columns=["revenue"],
        group_by=["product"],
        agg="sum",
    )
    plan_result = execute_plan(dataset_id=dataset_id, plan=plan)

    assert plan_result.row_count == 2
    assert "product" in plan_result.columns
    assert "revenue" in plan_result.columns
