from __future__ import annotations

from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


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

    # Document RAG limits — Phase 3
    max_document_size_mb: int = 10
    max_pdf_pages: int = 100
    max_chunks_per_document: int = 500
    max_extracted_chars: int = 500000

    # RAG Chunking and Retrieval — Phase 3
    chunk_size_words: int = 450
    chunk_overlap_words: int = 80
    rag_top_k: int = 5

    # ChromaDB — Phase 3
    chroma_persist_directory: str = "./data/chroma"

    @model_validator(mode="after")
    def validate_chunking_parameters(self) -> Settings:
        if self.chunk_size_words <= 0:
            raise ValueError("chunk_size_words must be greater than 0.")
        if self.chunk_overlap_words < 0:
            raise ValueError("chunk_overlap_words must be non-negative.")
        if self.chunk_overlap_words >= self.chunk_size_words:
            raise ValueError(
                f"chunk_overlap_words ({self.chunk_overlap_words}) must be strictly less than "
                f"chunk_size_words ({self.chunk_size_words})."
            )
        return self

    @field_validator("chroma_persist_directory", mode="after")
    @classmethod
    def resolve_chroma_path(cls, v: str) -> str:
        """Resolve a relative chroma_persist_directory against backend/, not CWD."""
        p = Path(v)
        if not p.is_absolute():
            return str((BACKEND_DIR / p).resolve())
        return str(p.resolve())

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
