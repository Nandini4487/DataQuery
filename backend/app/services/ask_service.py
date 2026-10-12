from __future__ import annotations

import logging

from app.core.config import settings
from app.schemas.answer import AnswerResponse
from app.services.answer_service import explain
from app.services.chart_service import infer_chart_spec
from app.services.file_service import read_dataset, validate_dataset_id
from app.services.llm_client import LLMUnavailableError
from app.services.query_executor import execute_query
from app.services.query_planner import PlanError, plan_query
from app.services.query_router import classify_question

logger = logging.getLogger(__name__)


class AskServiceError(Exception):
    """Base exception for ask service."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class QuestionValidationError(AskServiceError):
    """Raised when a question is empty or exceeds character limits."""

    def __init__(self, message: str, error_code: str = "validation_error") -> None:
        super().__init__(message, error_code)


class UnsupportedQuestionError(AskServiceError):
    """Raised when planner determines question cannot be answered with current data."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "unsupported_question")


class InvalidPlanError(AskServiceError):
    """Raised when a generated query plan is disallowed, malformed, or targets non-existent columns."""

    def __init__(
        self,
        message: str = "The generated query plan is invalid or contains disallowed operations.",
    ) -> None:
        super().__init__(message, "invalid_plan")


class ProviderUnavailableError(AskServiceError):
    """Raised when the LLM service / provider is unreachable, timed out, or exhausted."""

    def __init__(
        self,
        message: str = "The AI provider is currently unavailable. Please try again later.",
    ) -> None:
        super().__init__(message, "provider_unavailable")


def process_ask(dataset_id: str, question: str) -> AnswerResponse:
    """Execute the full ask question pipeline.

    Flow:
    1. Validate dataset_id format and load dataset.
    2. Validate question (not empty, within max_question_chars).
    3. Route question (structured | document | combined | unsupported stub).
    4. Plan question with Gemini planner (validates columns & operations).
    5. Execute validated plan deterministically with Pandas engine.
    6. Infer chart specification.
    7. Generate grounded plain-English explanation with answer service.
    8. Return complete AnswerResponse.
    """
    clean_id = validate_dataset_id(dataset_id)

    clean_question = question.strip() if question else ""
    if not clean_question:
        raise QuestionValidationError(
            "Question cannot be empty or whitespace only.",
            error_code="empty_question",
        )
    if len(question) > settings.max_question_chars:
        raise QuestionValidationError(
            f"Question length ({len(question)}) exceeds maximum limit of "
            f"{settings.max_question_chars} characters.",
            error_code="question_too_long",
        )

    # Load dataset (raises FileNotFoundError if not found)
    df = read_dataset(clean_id)

    # Route question (stub returns 'structured')
    _ = classify_question(question=clean_question, dataset_id=clean_id)

    # Extract schema (columns and dtypes only, no row values)
    columns = list(df.columns)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # Plan query via LLM planner
    try:
        planner_output = plan_query(
            question=clean_question,
            columns=columns,
            dtypes=dtypes,
        )
    except LLMUnavailableError as exc:
        raise ProviderUnavailableError() from exc
    except PlanError as exc:
        if exc.error_code == "llm_unavailable":
            raise ProviderUnavailableError() from exc
        logger.warning("Plan error during query planning: %s (code: %s)", exc.message, exc.error_code)
        raise InvalidPlanError() from exc

    if not planner_output.supported:
        reason = planner_output.reason.strip() or "This question cannot be answered with the current dataset schema."
        raise UnsupportedQuestionError(reason)

    if planner_output.plan is None:
        raise InvalidPlanError()

    # Execute plan deterministically (Pandas engine owns all numbers)
    result = execute_query(df=df, plan=planner_output.plan)

    # Infer chart spec
    chart_spec = infer_chart_spec(result)

    # Generate plain-English explanation
    explanation = explain(
        question=clean_question,
        plan=planner_output.plan,
        result=result,
    )

    is_fallback = bool(getattr(explanation, "is_fallback", False))

    return AnswerResponse(
        answer_text=str(explanation),
        table=result,
        chart_spec=chart_spec,
        citations=[],
        computed_by_engine=True,
        explanation_is_fallback=is_fallback,
    )
