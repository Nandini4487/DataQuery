from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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
    agg: str | None = None
    sort: SortInstruction | dict[str, Any] | None = None
    limit: int | None = None


class PlannerOutput(BaseModel):
    """Output from the query planner: supported flag, reason if unsupported, and plan."""

    supported: bool
    reason: str = ""
    plan: AnalysisPlan | None = None


class PlanResult(BaseModel):
    """Result of executing an AnalysisPlan."""

    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AskRequest(BaseModel):
    """Request payload for asking questions against a dataset."""

    question: str = Field(..., min_length=1)

    @field_validator("question")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty or whitespace only.")
        return v
