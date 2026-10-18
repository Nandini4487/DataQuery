from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.query_validator import QueryValidationError

logger = logging.getLogger(__name__)


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return standard error shape for Pydantic request validation errors without leaking raw fields."""
    logger.warning("Request validation failed on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request parameters or payload.",
        },
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Return standard error shape for HTTP exceptions."""
    error_code = "not_found" if exc.status_code == 404 else "http_error"
    message = str(exc.detail) if exc.detail else "An HTTP error occurred."
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_code, "message": message},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler: log the real error, return a safe generic message."""
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return the standard error shape for 404s."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": f"The requested resource was not found: {request.url.path}",
        },
    )


async def query_validation_error_handler(
    request: Request,
    exc: QueryValidationError,
) -> JSONResponse:
    """Return the standard error shape for 422 query validation errors."""
    return JSONResponse(
        status_code=422,
        content={"error": exc.error_code, "message": exc.message},
    )


async def plan_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return the standard error shape for 422 plan errors."""
    error_code = getattr(exc, "error_code", "plan_error")
    message = getattr(exc, "message", str(exc))
    return JSONResponse(
        status_code=422,
        content={"error": error_code, "message": message},
    )
