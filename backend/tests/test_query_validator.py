from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.query import AnalysisPlan, FilterCondition, SortInstruction
from app.services.file_service import save_csv_upload
from app.services.query_validator import QueryValidationError, validate_plan


def test_valid_plan_passes() -> None:
    """Valid plans across operations pass validation cleanly."""
    columns = ["product", "city", "revenue"]
    numeric_columns = ["revenue"]

    # Valid aggregate sum plan
    agg_plan = AnalysisPlan(
        operation="aggregate",
        columns=["revenue"],
        agg="sum",
    )
    validated_agg = validate_plan(
        agg_plan,
        columns=columns,
        numeric_columns=numeric_columns,
    )
    assert validated_agg.operation == "aggregate"
    assert validated_agg.agg == "sum"

    # Valid filter + sort + limit plan
    filter_plan = AnalysisPlan(
        operation="filter",
        columns=["product", "revenue"],
        filters=[
            FilterCondition(column="city", operator="eq", value="Delhi"),
        ],
        sort=SortInstruction(column="revenue", direction="desc"),
        limit=50,
    )
    validated_filter = validate_plan(
        filter_plan,
        columns=columns,
        numeric_columns=numeric_columns,
    )
    assert validated_filter.operation == "filter"
    assert validated_filter.limit == 50

    # Valid group_by plan
    group_plan = AnalysisPlan(
        operation="group_by",
        columns=["revenue"],
        group_by=["product"],
        agg="avg",
    )
    validated_group = validate_plan(
        group_plan,
        columns=columns,
        numeric_columns=numeric_columns,
    )
    assert validated_group.group_by == ["product"]


def test_unknown_column_rejected() -> None:
    """Plans referencing non-existent columns must be rejected with 422."""
    columns = ["product", "city", "revenue"]
    numeric_columns = ["revenue"]

    # Unknown column in columns list
    plan1 = AnalysisPlan(operation="filter", columns=["profit"])
    with pytest.raises(QueryValidationError) as exc1:
        validate_plan(plan1, columns=columns, numeric_columns=numeric_columns)
    assert exc1.value.status_code == 422
    assert exc1.value.error_code == "unknown_column"
    assert "profit" in exc1.value.message

    # Unknown column in filter
    plan2 = AnalysisPlan(
        operation="filter",
        filters=[FilterCondition(column="country", operator="eq", value="India")],
    )
    with pytest.raises(QueryValidationError) as exc2:
        validate_plan(plan2, columns=columns, numeric_columns=numeric_columns)
    assert exc2.value.status_code == 422
    assert exc2.value.error_code == "unknown_column"

    # Unknown column in group_by
    plan3 = AnalysisPlan(
        operation="group_by",
        columns=["revenue"],
        group_by=["category"],
        agg="sum",
    )
    with pytest.raises(QueryValidationError) as exc3:
        validate_plan(plan3, columns=columns, numeric_columns=numeric_columns)
    assert exc3.value.status_code == 422
    assert exc3.value.error_code == "unknown_column"

    # Unknown column in sort
    plan4 = AnalysisPlan(
        operation="sort",
        sort=SortInstruction(column="discount", direction="asc"),
    )
    with pytest.raises(QueryValidationError) as exc4:
        validate_plan(plan4, columns=columns, numeric_columns=numeric_columns)
    assert exc4.value.status_code == 422
    assert exc4.value.error_code == "unknown_column"


def test_disallowed_operation_rejected() -> None:
    """Operations not in the allowlist must be rejected with 422."""
    disallowed_ops = ["delete", "drop_table", "raw_sql", "eval", "pivot"]

    for op in disallowed_ops:
        plan = AnalysisPlan(operation=op)
        with pytest.raises(QueryValidationError) as exc:
            validate_plan(plan, columns=["product", "revenue"])
        assert exc.value.status_code == 422
        assert exc.value.error_code == "disallowed_operation"
        assert op in exc.value.message


def test_disallowed_aggregation_rejected() -> None:
    """Aggregations not in the allowlist (sum, avg, min, max, count) must be rejected with 422."""
    disallowed_aggs = ["median", "variance", "std", "quantile", "mode"]

    for agg in disallowed_aggs:
        plan = AnalysisPlan(
            operation="aggregate",
            columns=["revenue"],
            agg=agg,
        )
        with pytest.raises(QueryValidationError) as exc:
            validate_plan(
                plan,
                columns=["product", "revenue"],
                numeric_columns=["revenue"],
            )
        assert exc.value.status_code == 422
        assert exc.value.error_code == "disallowed_aggregation"


def test_sum_and_avg_on_text_column_rejected() -> None:
    """sum and avg aggregations targeting text/non-numeric columns must be rejected with 422."""
    columns = ["product", "city", "revenue"]
    numeric_columns = ["revenue"]

    # sum on product (text)
    sum_plan = AnalysisPlan(
        operation="aggregate",
        columns=["product"],
        agg="sum",
    )
    with pytest.raises(QueryValidationError) as exc_sum:
        validate_plan(
            sum_plan,
            columns=columns,
            numeric_columns=numeric_columns,
        )
    assert exc_sum.value.status_code == 422
    assert exc_sum.value.error_code == "non_numeric_aggregation"
    assert "product" in exc_sum.value.message

    # avg on city (text)
    avg_plan = AnalysisPlan(
        operation="aggregate",
        columns=["city"],
        agg="avg",
    )
    with pytest.raises(QueryValidationError) as exc_avg:
        validate_plan(
            avg_plan,
            columns=columns,
            numeric_columns=numeric_columns,
        )
    assert exc_avg.value.status_code == 422
    assert exc_avg.value.error_code == "non_numeric_aggregation"
    assert "city" in exc_avg.value.message


def test_limit_over_1000_rejected() -> None:
    """Limits greater than 1000 must be rejected with 422."""
    plan = AnalysisPlan(
        operation="filter",
        columns=["product"],
        limit=1001,
    )
    with pytest.raises(QueryValidationError) as exc:
        validate_plan(plan, columns=["product"])
    assert exc.value.status_code == 422
    assert exc.value.error_code == "limit_exceeded"
    assert "1000" in exc.value.message


def test_disallowed_operator_rejected() -> None:
    """Filter operators not in the allowlist must be rejected with 422."""
    disallowed_ops = ["like", "contains", "regex", "startswith", "between"]

    for op in disallowed_ops:
        plan = AnalysisPlan(
            operation="filter",
            filters=[FilterCondition(column="product", operator=op, value="x")],
        )
        with pytest.raises(QueryValidationError) as exc:
            validate_plan(plan, columns=["product"])
        assert exc.value.status_code == 422
        assert exc.value.error_code == "disallowed_operator"


def test_disallowed_sort_direction_rejected() -> None:
    """Sort directions other than asc/desc must be rejected with 422."""
    plan = AnalysisPlan(
        operation="sort",
        sort={"column": "revenue", "direction": "descending"},
    )
    with pytest.raises(QueryValidationError) as exc:
        validate_plan(plan, columns=["revenue"])
    assert exc.value.status_code == 422
    assert exc.value.error_code == "disallowed_sort_direction"


def test_validation_against_disk_dataset(
    tmp_upload_dir: Path,
    sample_csv_bytes: bytes,
) -> None:
    """Validate plan against a dataset stored on disk by dataset_id."""
    dataset_id = save_csv_upload(sample_csv_bytes, "acceptance.csv")

    # Valid plan against disk dataset
    valid_plan = AnalysisPlan(
        operation="aggregate",
        columns=["revenue"],
        agg="sum",
    )
    result = validate_plan(valid_plan, dataset_id=dataset_id)
    assert result.agg == "sum"

    # Invalid plan against disk dataset: sum on text column 'product'
    invalid_plan = AnalysisPlan(
        operation="aggregate",
        columns=["product"],
        agg="sum",
    )
    with pytest.raises(QueryValidationError) as exc:
        validate_plan(invalid_plan, dataset_id=dataset_id)
    assert exc.value.status_code == 422
    assert exc.value.error_code == "non_numeric_aggregation"
