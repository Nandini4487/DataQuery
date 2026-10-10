from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Upload limits
    max_upload_size_mb: int = 10

    # ChromaDB — Phase 3
    chroma_persist_directory: str = "./data/chroma"

    # Gemini — Phase 2 (optional here, required in Phase 2)
    gemini_api_key: str = ""
    gemini_model: str = ""

    # Database — Phase 2+ (optional for MVP)
    database_url: str = ""


settings = Settings()
