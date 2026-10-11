from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.schemas.query import AnalysisPlan, FilterCondition, PlanResult
from app.services.file_service import read_dataset


def _apply_filter(df: pd.DataFrame, flt: FilterCondition | dict[str, Any]) -> pd.DataFrame:
    """Apply a single filter condition using pure pandas boolean masking."""
    if isinstance(flt, FilterCondition):
        col = flt.column
        op = flt.operator
        val = flt.value
    elif isinstance(flt, dict):
        col = flt.get("column", "")
        op = flt.get("operator", "eq")
        val = flt.get("value")
    else:
        return df

    if col not in df.columns:
        return df

    series = df[col]
    if op == "eq":
        mask = series == val
    elif op == "ne":
        mask = series != val
    elif op == "gt":
        mask = series > val
    elif op == "lt":
        mask = series < val
    elif op == "gte":
        mask = series >= val
    elif op == "lte":
        mask = series <= val
    elif op == "in":
        val_list = val if isinstance(val, (list, tuple, set)) else [val]
        mask = series.isin(val_list)
    else:
        raise ValueError(f"Unsupported filter operator: '{op}'")

    return df[mask]


def execute_query(
    df: pd.DataFrame | None = None,
    plan: AnalysisPlan | dict[str, Any] | None = None,
    dataset_id: str | None = None,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Execute an AnalysisPlan deterministically using Pandas methods only.

    No eval(), exec(), or df.query() with strings is ever used.
    Returns plain dict with {"columns": [...], "rows": [...], "row_count": int}.
    """
    if plan is None:
        raise ValueError("An AnalysisPlan must be provided.")

    if isinstance(plan, dict):
        plan_obj = AnalysisPlan(**plan)
    else:
        plan_obj = plan

    if df is None:
        if dataset_id is None:
            raise ValueError("Either a DataFrame or a dataset_id must be provided.")
        current_df = read_dataset(dataset_id, base_dir=base_dir)
    else:
        current_df = df.copy()

    # Step 1: Apply filters using boolean masks
    for flt in plan_obj.filters:
        current_df = _apply_filter(current_df, flt)

    # Step 2: Execute operation
    op = plan_obj.operation

    if op == "aggregate":
        agg_name = plan_obj.agg or "count"
        target_cols = (
            plan_obj.columns
            if plan_obj.columns
            else list(current_df.select_dtypes(include="number").columns)
        )
        row_dict: dict[str, Any] = {}
        for col in target_cols:
            if col not in current_df.columns:
                continue
            series = current_df[col].dropna()
            if agg_name == "sum":
                val = series.sum()
            elif agg_name == "avg":
                val = series.mean()
            elif agg_name == "min":
                val = series.min()
            elif agg_name == "max":
                val = series.max()
            elif agg_name == "count":
                val = series.count()
            else:
                raise ValueError(f"Unsupported aggregation '{agg_name}'")

            if hasattr(val, "item"):
                val = val.item()
            elif pd.isna(val):
                val = None
            row_dict[col] = val

        result_df = pd.DataFrame([row_dict])

    elif op == "group_by":
        agg_name = plan_obj.agg or "sum"
        agg_func = "mean" if agg_name == "avg" else agg_name
        group_cols = plan_obj.group_by
        target_cols = [c for c in plan_obj.columns if c not in group_cols]
        if not target_cols:
            num_cols = list(current_df.select_dtypes(include="number").columns)
            target_cols = [c for c in num_cols if c not in group_cols]

        if not target_cols:
            # Fallback to count of first column
            grouped = current_df.groupby(group_cols, as_index=False).size()
            grouped = grouped.rename(columns={"size": "count"})
            result_df = grouped
        else:
            result_df = current_df.groupby(group_cols, as_index=False)[
                target_cols
            ].agg(agg_func)

        # Apply sort if specified
        if plan_obj.sort is not None:
            sort_col = (
                plan_obj.sort.column
                if hasattr(plan_obj.sort, "column")
                else plan_obj.sort.get("column")
            )
            sort_dir = (
                plan_obj.sort.direction
                if hasattr(plan_obj.sort, "direction")
                else plan_obj.sort.get("direction", "asc")
            )
            if sort_col and sort_col in result_df.columns:
                result_df = result_df.sort_values(
                    by=sort_col, ascending=(sort_dir == "asc")
                )

        if plan_obj.limit is not None:
            result_df = result_df.head(plan_obj.limit)

    elif op == "top_n":
        if plan_obj.group_by:
            agg_name = plan_obj.agg or "sum"
            agg_func = "mean" if agg_name == "avg" else agg_name
            group_cols = plan_obj.group_by
            target_cols = [c for c in plan_obj.columns if c not in group_cols]
            if not target_cols:
                num_cols = list(current_df.select_dtypes(include="number").columns)
                target_cols = [c for c in num_cols if c not in group_cols]

            grouped = current_df.groupby(group_cols, as_index=False)[
                target_cols
            ].agg(agg_func)
            sort_target = target_cols[0] if target_cols else group_cols[0]
            result_df = grouped.sort_values(by=sort_target, ascending=False)
        else:
            sort_target = (
                plan_obj.columns[0]
                if plan_obj.columns
                else current_df.columns[0]
            )
            result_df = current_df.sort_values(
                by=sort_target, ascending=False
            )

        n = plan_obj.limit if plan_obj.limit is not None else 1
        result_df = result_df.head(n)

    elif op == "count":
        cnt = len(current_df)
        result_df = pd.DataFrame([{"count": cnt}])

    elif op in ("filter", "sort"):
        result_df = current_df
        if plan_obj.sort is not None:
            sort_col = (
                plan_obj.sort.column
                if hasattr(plan_obj.sort, "column")
                else plan_obj.sort.get("column")
            )
            sort_dir = (
                plan_obj.sort.direction
                if hasattr(plan_obj.sort, "direction")
                else plan_obj.sort.get("direction", "asc")
            )
            if sort_col and sort_col in result_df.columns:
                result_df = result_df.sort_values(
                    by=sort_col, ascending=(sort_dir == "asc")
                )

        if plan_obj.limit is not None:
            result_df = result_df.head(plan_obj.limit)

        if plan_obj.columns:
            valid_cols = [c for c in plan_obj.columns if c in result_df.columns]
            result_df = result_df[valid_cols]

    else:
        raise ValueError(f"Unsupported operation: '{op}'")

    # Clean NaNs and format as plain lists and dicts
    cleaned_df = result_df.where(pd.notnull(result_df), None)
    columns_list = [str(c) for c in cleaned_df.columns]
    rows_list = cleaned_df.to_dict(orient="records")

    # Convert any remaining numpy scalar values to python native types
    for row in rows_list:
        for k, v in row.items():
            if hasattr(v, "item"):
                row[k] = v.item()

    return {
        "columns": columns_list,
        "rows": rows_list,
        "row_count": len(rows_list),
    }


def execute_plan(
    df: pd.DataFrame | None = None,
    plan: AnalysisPlan | dict[str, Any] | None = None,
    dataset_id: str | None = None,
    base_dir: Path | str | None = None,
) -> PlanResult:
    """Execute an AnalysisPlan and return a typed PlanResult."""
    raw = execute_query(
        df=df,
        plan=plan,
        dataset_id=dataset_id,
        base_dir=base_dir,
    )
    return PlanResult(**raw)
