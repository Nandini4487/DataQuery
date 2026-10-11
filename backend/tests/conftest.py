from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous TestClient for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def sample_csv_text() -> str:
    """Sample acceptance dataset from SPEC section 7.6."""
    return (
        "product,city,revenue\n"
        "Laptop,Delhi,80000\n"
        "Phone,Mumbai,50000\n"
        "Laptop,Mumbai,70000\n"
        "Phone,Delhi,40000\n"
    )


@pytest.fixture()
def sample_csv_bytes(sample_csv_text: str) -> bytes:
    """Sample acceptance dataset bytes encoded in UTF-8."""
    return sample_csv_text.encode("utf-8")


@pytest.fixture()
def tmp_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temporary upload directory fixture isolated per test."""
    upload_path = tmp_path / "uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "upload_dir", str(upload_path))
    return upload_path
