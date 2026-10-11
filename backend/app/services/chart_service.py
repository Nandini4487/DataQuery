from __future__ import annotations

from typing import Any

from app.schemas.query import PlanResult

TIME_COLUMN_KEYWORDS: tuple[str, ...] = (
    "date",
    "time",
    "year",
    "month",
    "day",
    "timestamp",
    "period",
    "quarter",
)


def _is_numeric_val(val: Any) -> bool:
    """Check if value is numeric and not boolean."""
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def infer_chart_spec(
    result: dict[str, Any] | PlanResult | list[dict[str, Any]],
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Pick chart type from result shape and return chart_spec {type, x, y, data}.

    Inference rules:
    - scalar: single value (1 row, 1 column or single metric)
    - line: time series (contains a date/time column and a numeric metric)
    - bar: grouped aggregation (contains categorical/text dimension and numeric metric)
    """
    if isinstance(result, PlanResult):
        res_columns = result.columns
        res_rows = result.rows
    elif isinstance(result, dict):
        res_columns = result.get("columns", [])
        res_rows = result.get("rows", [])
    elif isinstance(result, list):
        res_rows = result
        res_columns = columns or (list(result[0].keys()) if result else [])
    else:
        res_columns = columns or []
        res_rows = []

    if columns and not res_columns:
        res_columns = columns

    if not res_rows:
        return {
            "type": "empty",
            "x": None,
            "y": None,
            "data": [],
        }

    # Identify column data types based on row values
    first_row = res_rows[0]
    time_cols: list[str] = []
    numeric_cols: list[str] = []
    text_cols: list[str] = []

    for col in res_columns:
        col_lower = col.lower()
        val = first_row.get(col)

        is_numeric = _is_numeric_val(val)
        is_time_name = any(kw in col_lower for kw in TIME_COLUMN_KEYWORDS)

        if is_time_name:
            time_cols.append(col)
        elif is_numeric:
            numeric_cols.append(col)
        else:
            text_cols.append(col)

    # 1. Scalar chart: single row and single value
    if len(res_rows) == 1 and (len(res_columns) == 1 or len(numeric_cols) == 1):
        target_y = numeric_cols[0] if numeric_cols else res_columns[0]
        return {
            "type": "scalar",
            "x": None,
            "y": target_y,
            "data": res_rows,
        }

    # 2. Line chart: time series
    if time_cols and numeric_cols:
        return {
            "type": "line",
            "x": time_cols[0],
            "y": numeric_cols[0],
            "data": res_rows,
        }

    # 3. Bar chart: grouped aggregation (categorical + numeric)
    if text_cols and numeric_cols:
        return {
            "type": "bar",
            "x": text_cols[0],
            "y": numeric_cols[0],
            "data": res_rows,
        }

    # Fallback: if multiple rows and numeric columns exist
    if len(res_columns) >= 2:
        return {
            "type": "bar",
            "x": res_columns[0],
            "y": res_columns[1],
            "data": res_rows,
        }

    return {
        "type": "scalar",
        "x": None,
        "y": res_columns[0] if res_columns else None,
        "data": res_rows,
    }


# Aliases for convenience across services
build_chart_spec = infer_chart_spec
get_chart_spec = infer_chart_spec
