from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    """Single filter criterion used in an analysis plan."""

    column: str
    operator: str
    value: Any


class SortInstruction(BaseModel):
    """Sort instruction with target column and direction."""

    column: str
    direction: Literal["asc", "desc"] = "asc"


class AnalysisPlan(BaseModel):
    """Constrained structured analysis plan for deterministic execution."""

    operation: str
    columns: list[str] = Field(default_factory=list)
    filters: list[FilterCondition | dict[str, Any]] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    agg: Literal["sum", "avg", "min", "max", "count"] | None = None
    sort: SortInstruction | dict[str, Any] | None = None
    limit: int | None = None


class PlanResult(BaseModel):
    """Result of executing an AnalysisPlan."""

    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
