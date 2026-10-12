from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.document import Citation


class AnswerResponse(BaseModel):
    """Unified response returned for questions answered by the system."""

    answer_text: str
    table: dict[str, Any] | list[dict[str, Any]] | None = None
    chart_spec: dict[str, Any] | None = None
    citations: list[Citation] = Field(default_factory=list)
    route: Literal["structured", "document", "combined"] = "structured"
    computed_by_engine: bool = True
    explanation_is_fallback: bool = False
