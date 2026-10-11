from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.answer import AnswerResponse
from app.schemas.query import AnalysisPlan, AskRequest
from app.services.chart_service import infer_chart_spec
from app.services.file_service import (
    FileValidationError,
    read_dataset,
    validate_dataset_id,
)
from app.services.query_executor import execute_query
from app.services.query_validator import validate_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["ask"])


@router.post(
    "/{id}/ask",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question against a dataset (stub for Phase 1)",
)
async def ask_question(id: str, request: AskRequest) -> Any:
    """Stub endpoint for Phase 1.

    Validates dataset_id, loads dataset, and executes a fixed plan
    (sum of first numeric column if present, or row count) through the real
    validator, executor, and chart service. Returns an AnswerResponse.
    """
    try:
        clean_id = validate_dataset_id(id)
    except FileValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )

    try:
        df = read_dataset(clean_id)
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )

    # Determine fixed plan: sum of first numeric column if present, otherwise count
    num_cols = list(df.select_dtypes(include="number").columns)
    if num_cols:
        plan = AnalysisPlan(
            operation="aggregate",
            columns=[num_cols[0]],
            agg="sum",
        )
    else:
        plan = AnalysisPlan(operation="count")

    # Run through the real query validator
    validated_plan = validate_plan(plan, df=df)

    # Run through the real query executor
    result = execute_query(df=df, plan=validated_plan)

    # Run through the real chart service
    chart_spec = infer_chart_spec(result)

    return AnswerResponse(
        answer_text="Stub response (LLM not connected yet)",
        table=result,
        chart_spec=chart_spec,
        citations=[],
    )
