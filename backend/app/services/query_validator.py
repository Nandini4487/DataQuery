from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException

from app.schemas.query import AnalysisPlan, FilterCondition, SortInstruction
from app.services.file_service import read_dataset

ALLOWED_OPERATIONS: frozenset[str] = frozenset(
    {"filter", "aggregate", "group_by", "sort", "count", "top_n"}
)
ALLOWED_AGGREGATIONS: frozenset[str] = frozenset(
    {"sum", "avg", "min", "max", "count"}
)
ALLOWED_OPERATORS: frozenset[str] = frozenset(
    {"eq", "ne", "gt", "lt", "gte", "lte", "in"}
)
ALLOWED_SORT_DIRECTIONS: frozenset[str] = frozenset({"asc", "desc"})
MAX_LIMIT: int = 1000


class QueryValidationError(HTTPException):
    """Raised when an AnalysisPlan fails validation. Always returns status code 422."""

    def __init__(
        self,
        message: str,
        error_code: str = "query_validation_error",
    ) -> None:
        super().__init__(
            status_code=422,
            detail={"error": error_code, "message": message},
        )
        self.message = message
        self.error_code = error_code

    def to_dict(self) -> dict[str, str]:
        """Return the standard error shape {"error", "message"}."""
        return {"error": self.error_code, "message": self.message}


def validate_plan(
    plan: AnalysisPlan | dict[str, Any],
    columns: list[str] | set[str] | None = None,
    numeric_columns: list[str] | set[str] | None = None,
    dtypes: dict[str, str] | None = None,
    df: pd.DataFrame | None = None,
    dataset_id: str | None = None,
    base_dir: Path | str | None = None,
) -> AnalysisPlan:
    """Validate an AnalysisPlan against allowlists and dataset schema.

    Enforces:
    - Operation in ALLOWED_OPERATIONS
    - Aggregation in ALLOWED_AGGREGATIONS
    - Operator in ALLOWED_OPERATORS
    - Sort direction in ALLOWED_SORT_DIRECTIONS
    - Result limit <= MAX_LIMIT (1000)
    - All referenced columns exist in the dataset
    - sum and avg aggregations target numeric columns only
    - Raises structured 422 QueryValidationError on any violation.
    """
    if isinstance(plan, dict):
        try:
            plan_obj = AnalysisPlan(**plan)
        except Exception as exc:
            raise QueryValidationError(
                f"Invalid analysis plan format: {exc}",
                error_code="invalid_plan_format",
            ) from exc
    else:
        plan_obj = plan

    # Resolve dataset schema (all columns and numeric columns)
    if df is not None:
        all_cols = {str(c) for c in df.columns}
        num_cols = {
            str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
        }
    elif dataset_id is not None:
        loaded_df = read_dataset(dataset_id, base_dir=base_dir)
        all_cols = {str(c) for c in loaded_df.columns}
        num_cols = {
            str(c)
            for c in loaded_df.columns
            if pd.api.types.is_numeric_dtype(loaded_df[c])
        }
    else:
        all_cols = {str(c) for c in (columns or [])}
        if numeric_columns is not None:
            num_cols = {str(c) for c in numeric_columns}
        elif dtypes is not None:
            num_cols = {
                str(col)
                for col, dt in dtypes.items()
                if any(
                    t in str(dt).lower()
                    for t in ("int", "float", "num", "double")
                )
            }
        else:
            num_cols = set()

    # 1. Validate operation
    if plan_obj.operation not in ALLOWED_OPERATIONS:
        raise QueryValidationError(
            f"Disallowed operation '{plan_obj.operation}'. "
            f"Allowed operations: {sorted(ALLOWED_OPERATIONS)}.",
            error_code="disallowed_operation",
        )

    # 2. Validate columns
    for col in plan_obj.columns:
        if col not in all_cols:
            raise QueryValidationError(
                f"Unknown column '{col}'. Allowed columns: {sorted(all_cols)}.",
                error_code="unknown_column",
            )

    # 3. Validate group_by columns
    if plan_obj.operation == "group_by" and not plan_obj.group_by:
        raise QueryValidationError(
            "Operation 'group_by' requires at least one group_by column.",
            error_code="missing_group_by",
        )
    for col in plan_obj.group_by:
        if col not in all_cols:
            raise QueryValidationError(
                f"Unknown group_by column '{col}'. Allowed columns: {sorted(all_cols)}.",
                error_code="unknown_column",
            )

    # 4. Validate filters
    for flt in plan_obj.filters:
        if isinstance(flt, FilterCondition):
            flt_col = flt.column
            flt_op = flt.operator
        elif isinstance(flt, dict):
            flt_col = flt.get("column", "")
            flt_op = flt.get("operator", "")
        else:
            raise QueryValidationError(
                "Invalid filter condition structure.",
                error_code="invalid_filter",
            )

        if flt_col not in all_cols:
            raise QueryValidationError(
                f"Unknown filter column '{flt_col}'. Allowed columns: {sorted(all_cols)}.",
                error_code="unknown_column",
            )
        if flt_op not in ALLOWED_OPERATORS:
            raise QueryValidationError(
                f"Disallowed filter operator '{flt_op}'. "
                f"Allowed operators: {sorted(ALLOWED_OPERATORS)}.",
                error_code="disallowed_operator",
            )

    # 5. Validate aggregation
    if plan_obj.agg is not None:
        if plan_obj.agg not in ALLOWED_AGGREGATIONS:
            raise QueryValidationError(
                f"Disallowed aggregation '{plan_obj.agg}'. "
                f"Allowed aggregations: {sorted(ALLOWED_AGGREGATIONS)}.",
                error_code="disallowed_aggregation",
            )
        # sum and avg must target numeric columns only
        if plan_obj.agg in ("sum", "avg"):
            if not plan_obj.columns:
                raise QueryValidationError(
                    f"Aggregation '{plan_obj.agg}' requires target column(s).",
                    error_code="missing_columns",
                )
            for col in plan_obj.columns:
                if col not in num_cols:
                    raise QueryValidationError(
                        f"Aggregation '{plan_obj.agg}' can only target numeric columns, "
                        f"but column '{col}' is not numeric.",
                        error_code="non_numeric_aggregation",
                    )
    elif plan_obj.operation == "aggregate":
        raise QueryValidationError(
            "Operation 'aggregate' requires an 'agg' field (sum, avg, min, max, count).",
            error_code="missing_aggregation",
        )

    # 6. Validate sort
    if plan_obj.sort is not None:
        if isinstance(plan_obj.sort, SortInstruction):
            sort_col = plan_obj.sort.column
            sort_dir = plan_obj.sort.direction
        elif isinstance(plan_obj.sort, dict):
            sort_col = plan_obj.sort.get("column")
            sort_dir = plan_obj.sort.get("direction", "asc")
        else:
            sort_col = None
            sort_dir = str(plan_obj.sort)

        if sort_col and sort_col not in all_cols:
            raise QueryValidationError(
                f"Unknown sort column '{sort_col}'. Allowed columns: {sorted(all_cols)}.",
                error_code="unknown_column",
            )
        if sort_dir not in ALLOWED_SORT_DIRECTIONS:
            raise QueryValidationError(
                f"Disallowed sort direction '{sort_dir}'. "
                f"Allowed directions: {sorted(ALLOWED_SORT_DIRECTIONS)}.",
                error_code="disallowed_sort_direction",
            )

    # 7. Validate limit
    if plan_obj.limit is not None:
        if plan_obj.limit > MAX_LIMIT:
            raise QueryValidationError(
                f"Limit {plan_obj.limit} exceeds maximum allowed limit of {MAX_LIMIT}.",
                error_code="limit_exceeded",
            )
        if plan_obj.limit <= 0:
            raise QueryValidationError(
                f"Limit must be a positive integer, got {plan_obj.limit}.",
                error_code="invalid_limit",
            )

    return plan_obj
