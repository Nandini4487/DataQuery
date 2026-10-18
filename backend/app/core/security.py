from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import Request, UploadFile
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.services.file_service import FileValidationError

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB


async def read_stream_limited(
    file: UploadFile,
    max_bytes: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bytes:
    """Read an UploadFile stream in chunks, aborting early if max_bytes is exceeded.

    This prevents reading multi-gigabyte or malicious payloads entirely into server memory.
    Raises FileValidationError with error_code 'file_too_large' immediately when exceeded.
    """
    total = 0
    chunks: list[bytes] = []

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            limit_mb = max_bytes // (1024 * 1024)
            raise FileValidationError(
                f"File size exceeds the maximum limit of {limit_mb} MB.",
                error_code="file_too_large",
            )
        chunks.append(chunk)

    return b"".join(chunks)


def get_client_ip(request: Request) -> str:
    """Extract client IP directly from socket without trusting X-Forwarded-For."""
    if not request.client or not request.client.host:
        return "127.0.0.1"
    return request.client.host


class DynamicLimiter(Limiter):
    """Limiter whose enabled state dynamically tracks settings.rate_limiting_enabled."""

    @property
    def enabled(self) -> bool:  # type: ignore[override]
        return bool(settings.rate_limiting_enabled)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        pass


limiter = DynamicLimiter(
    key_func=get_client_ip,
    headers_enabled=False,
)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Return standard error shape {"error", "message"} for 429 rate limit exceeded.

    Includes a Retry-After header calculated from rate limit window stats.
    """
    retry_after = "60"
    active_limiter = getattr(request.app.state, "limiter", None)
    view_rate_limit: Any = getattr(request.state, "view_rate_limit", None)

    if active_limiter and view_rate_limit:
        try:
            window_stats = active_limiter.limiter.get_window_stats(
                view_rate_limit[0], *view_rate_limit[1]
            )
            reset_in = 1 + window_stats[0]
            retry_after = str(max(1, int(reset_in - time.time())))
        except Exception:  # noqa: BLE001
            retry_after = "60"

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limited",
            "message": "Too many requests. Please try again later.",
        },
        headers={"Retry-After": retry_after},
    )
