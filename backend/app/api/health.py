from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint. Returns 200 with status ok."""
    return JSONResponse(content={"status": "ok"})
