from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.query_validator import QueryValidationError

logger = logging.getLogger(__name__)


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
