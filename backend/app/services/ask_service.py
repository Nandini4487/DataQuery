from __future__ import annotations

import logging

from app.core.config import settings
from app.schemas.answer import AnswerResponse
from app.services.answer_service import (
    answer_combined_question,
    answer_document_question,
    explain,
)
from app.services.chart_service import infer_chart_spec
from app.services.document_service import list_documents
from app.services.embedding_service import EmbeddingError
from app.services.file_service import read_dataset, validate_dataset_id
from app.services.llm_client import LLMUnavailableError
from app.services.query_executor import execute_query
from app.services.query_planner import PlanError, plan_query
from app.services.query_router import classify_question
from app.services.retrieval_service import retrieve

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
    """Raised when planner or router determines question cannot be answered."""

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


class DocumentsRequiredError(AskServiceError):
    """Raised when a document question is asked but no documents have been uploaded."""

    def __init__(
        self,
        message: str = "No reference documents have been uploaded for this dataset. Please upload a reference document first.",
    ) -> None:
        super().__init__(message, "documents_required")


class EmbeddingUnavailableError(AskServiceError):
    """Raised when the embedding service fails."""

    def __init__(
        self,
        message: str = "Embedding service is temporarily unavailable.",
    ) -> None:
        super().__init__(message, "embedding_unavailable")


def process_ask(dataset_id: str, question: str) -> AnswerResponse:
    """Execute the full ask question pipeline across structured, document, combined, and unsupported routes."""
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

    # 1. Load tabular dataset
    df = read_dataset(clean_id)
    columns = list(df.columns)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # 2. Get list of indexed document filenames
    docs = list_documents(clean_id)
    doc_filenames = [d.filename for d in docs]

    # 3. Route question via LLM router
    try:
        router_output = classify_question(
            question=clean_question,
            columns=columns,
            dtypes=dtypes,
            document_filenames=doc_filenames,
        )
    except LLMUnavailableError as exc:
        raise ProviderUnavailableError() from exc
    except Exception as exc:
        logger.warning("Router call failed: %s", exc)
        raise ProviderUnavailableError() from exc

    route = router_output.route

    # --- Route: unsupported ---
    if route == "unsupported":
        reason = (
            router_output.reason.strip()
            or "This question cannot be answered with the current dataset schema or reference documents."
        )
        raise UnsupportedQuestionError(reason)

    # --- Route: structured ---
    if route == "structured":
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

        result = execute_query(df=df, plan=planner_output.plan)
        chart_spec = infer_chart_spec(result)
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
            route="structured",
            computed_by_engine=True,
            explanation_is_fallback=is_fallback,
        )

    # --- Route: document ---
    if route == "document":
        if not docs:
            raise DocumentsRequiredError(
                "No reference documents have been uploaded for this dataset. Please upload a reference document first."
            )

        try:
            passages = retrieve(
                query=clean_question,
                dataset_id=clean_id,
                top_k=settings.rag_top_k,
            )
        except EmbeddingError as exc:
            raise EmbeddingUnavailableError() from exc

        if not passages:
            return AnswerResponse(
                answer_text="The uploaded documents do not contain enough information to answer this question.",
                table=None,
                chart_spec=None,
                citations=[],
                route="document",
                computed_by_engine=False,
                explanation_is_fallback=False,
            )

        try:
            answer_text, citations = answer_document_question(
                question=clean_question,
                passages=passages,
            )
        except LLMUnavailableError as exc:
            raise ProviderUnavailableError() from exc

        return AnswerResponse(
            answer_text=answer_text,
            table=None,
            chart_spec=None,
            citations=citations,
            route="document",
            computed_by_engine=False,
            explanation_is_fallback=False,
        )

    # --- Route: combined ---
    if route == "combined":
        # Branch 1: Document branch
        doc_passages = []
        doc_failure_msg = ""
        if not docs:
            doc_failure_msg = "No reference document is uploaded for this dataset."
        else:
            try:
                doc_passages = retrieve(
                    query=clean_question,
                    dataset_id=clean_id,
                    top_k=settings.rag_top_k,
                )
                if not doc_passages:
                    doc_failure_msg = "The uploaded documents do not contain enough information to answer the document part of this question."
            except EmbeddingError:
                doc_failure_msg = "The document part could not be answered because the embedding service was unavailable."
            except Exception as exc:  # noqa: BLE001
                logger.warning("Document retrieval failed in combined route: %s", exc)
                doc_failure_msg = "The document part could not be answered due to a retrieval error."

        # Branch 2: Structured branch
        structured_ok = False
        structured_result = None
        structured_chart_spec = None
        structured_plan = None
        structured_failure_msg = ""

        try:
            planner_output = plan_query(
                question=clean_question,
                columns=columns,
                dtypes=dtypes,
            )
            if not planner_output.supported:
                structured_failure_msg = f"The dataset could not answer the numerical part: {planner_output.reason.strip() or 'unsupported query'}."
            elif planner_output.plan is None:
                structured_failure_msg = "The dataset could not answer the numerical part: invalid query plan."
            else:
                structured_plan = planner_output.plan
                structured_result = execute_query(df=df, plan=structured_plan)
                structured_chart_spec = infer_chart_spec(structured_result)
                structured_ok = True
        except LLMUnavailableError:
            structured_failure_msg = "The data query planner was unavailable."
        except PlanError as exc:
            structured_failure_msg = f"Data query planning failed: {exc.message}."
        except Exception as exc:  # noqa: BLE001
            logger.warning("Structured execution failed in combined route: %s", exc)
            structured_failure_msg = "Data query execution failed."

        # Synthesis
        if not structured_ok and not doc_passages:
            combined_err = f"{structured_failure_msg} {doc_failure_msg}".strip()
            raise UnsupportedQuestionError(combined_err or "Neither the dataset nor documents could answer this question.")

        # Structured succeeded, document failed / no docs
        if structured_ok and not doc_passages:
            explanation = explain(
                question=clean_question,
                plan=structured_plan,
                result=structured_result,
            )
            is_fallback = bool(getattr(explanation, "is_fallback", False))
            combined_text = f"{explanation!s}\n\n(Note: {doc_failure_msg})"
            return AnswerResponse(
                answer_text=combined_text,
                table=structured_result,
                chart_spec=structured_chart_spec,
                citations=[],
                route="combined",
                computed_by_engine=True,
                explanation_is_fallback=is_fallback,
            )

        # Document succeeded, structured failed
        if not structured_ok and doc_passages:
            try:
                doc_ans, doc_cits = answer_document_question(
                    question=clean_question,
                    passages=doc_passages,
                )
            except LLMUnavailableError as exc:
                raise ProviderUnavailableError() from exc

            combined_text = f"{doc_ans}\n\n(Note: {structured_failure_msg})"
            return AnswerResponse(
                answer_text=combined_text,
                table=None,
                chart_spec=None,
                citations=doc_cits,
                route="combined",
                computed_by_engine=False,
                explanation_is_fallback=False,
            )

        # Both succeeded!
        ans_text, citations, is_fallback = answer_combined_question(
            question=clean_question,
            result=structured_result,
            passages=doc_passages,
        )
        return AnswerResponse(
            answer_text=ans_text,
            table=structured_result,
            chart_spec=structured_chart_spec,
            citations=citations,
            route="combined",
            computed_by_engine=True,
            explanation_is_fallback=is_fallback,
        )

    # Fallback safety
    raise UnsupportedQuestionError("Unrecognized route for question.")
