from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ask, datasets, documents, health
from app.core.config import settings
from app.core.errors import (
    generic_exception_handler,
    not_found_handler,
    plan_error_handler,
    query_validation_error_handler,
)
from app.services.query_planner import PlanError
from app.services.query_validator import QueryValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(title="DataQuery AI", version="0.1.0")

# --- CORS (never "*") ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception handlers ---
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(QueryValidationError, query_validation_error_handler)
app.add_exception_handler(PlanError, plan_error_handler)

# --- Routers ---
app.include_router(health.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
