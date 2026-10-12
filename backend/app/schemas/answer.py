from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnswerResponse(BaseModel):
    """Unified response returned for questions answered by the system."""

    answer_text: str
    table: dict[str, Any] | list[dict[str, Any]] | None = None
    chart_spec: dict[str, Any] | None = None
    citations: list[Any] = Field(default_factory=list)
    computed_by_engine: bool = True
    explanation_is_fallback: bool = False
