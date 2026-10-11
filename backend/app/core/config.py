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
    upload_dir: str = "./uploads"

    # ChromaDB — Phase 3
    chroma_persist_directory: str = "./data/chroma"

    # Gemini — Phase 2
    gemini_api_key: str = ""
    gemini_model: str = ""
    llm_timeout_seconds: int = 20
    llm_max_output_tokens: int = 1024
    llm_max_retries: int = 1
    max_question_chars: int = 500

    # Database — Phase 2+ (optional for MVP)
    database_url: str = ""

    def require_gemini_model(self) -> str:
        """Validate that GEMINI_MODEL is configured when the LLM path is invoked."""
        model = (self.gemini_model or "").strip()
        if not model:
            raise ValueError(
                "GEMINI_MODEL is required for LLM operations but is not set. "
                "Please configure GEMINI_MODEL in your environment or .env file."
            )
        return model

    def require_gemini_api_key(self) -> str:
        """Validate that GEMINI_API_KEY is configured when the LLM path is invoked."""
        key = (self.gemini_api_key or "").strip()
        if not key:
            raise ValueError(
                "GEMINI_API_KEY is required for LLM operations but is not set. "
                "Please configure GEMINI_API_KEY in your environment or .env file."
            )
        return key


settings = Settings()
