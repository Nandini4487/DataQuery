from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.answer import AnswerResponse
from app.schemas.query import AskRequest
from app.services.ask_service import (
    InvalidPlanError,
    ProviderUnavailableError,
    QuestionValidationError,
    UnsupportedQuestionError,
    process_ask,
)
from app.services.file_service import FileValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["ask"])


@router.post(
    "/{id}/ask",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question against a dataset",
)
async def ask_question(id: str, request: AskRequest) -> Any:
    """Ask a question against an uploaded dataset.

    Flow: validate -> route -> plan -> execute -> chart -> explain -> AnswerResponse.
    """
    try:
        return process_ask(dataset_id=id, question=request.question)
    except FileValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.error_code, "message": exc.message},
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": f"Dataset '{id}' not found."},
        )
    except QuestionValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": exc.error_code, "message": exc.message},
        )
    except UnsupportedQuestionError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": "unsupported_question", "message": exc.message},
        )
    except InvalidPlanError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": "invalid_plan", "message": exc.message},
        )
    except ProviderUnavailableError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "provider_unavailable", "message": exc.message},
        )
    except Exception:
        logger.exception("Unexpected error in /ask")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again.",
            },
        )
