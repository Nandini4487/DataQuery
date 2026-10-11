from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMUnavailableError(Exception):
    """Raised when the LLM service is unavailable, unconfigured, or fails."""


def _sanitize(message: str) -> str:
    """Ensure the API key is never present in any error or string message."""
    if settings.gemini_api_key and settings.gemini_api_key in message:
        return message.replace(settings.gemini_api_key, "[REDACTED]")
    return message


def _to_llm_unavailable_error(exc: Exception) -> LLMUnavailableError:
    """Map provider / network exceptions to LLMUnavailableError with safe messages."""
    msg_lower = str(exc).lower()

    if isinstance(exc, (TimeoutError, httpx.TimeoutException)) or "timeout" in msg_lower or "timed out" in msg_lower:
        safe_msg = "LLM request timed out. Please try again later."
    elif "quota" in msg_lower or "429" in msg_lower or "resource_exhausted" in msg_lower:
        safe_msg = "LLM service quota exceeded or rate limited. Please try again later."
    elif (
        "401" in msg_lower
        or "403" in msg_lower
        or "authenticat" in msg_lower
        or "permission" in msg_lower
        or "api_key" in msg_lower
        or "api key" in msg_lower
    ):
        safe_msg = "LLM authentication failed. Please check your API key configuration."
    elif isinstance(exc, (httpx.NetworkError, ConnectionError)) or "connect" in msg_lower or "network" in msg_lower:
        safe_msg = "LLM network connection failed. Please try again later."
    else:
        safe_msg = "LLM service is currently unavailable. Please try again later."

    return LLMUnavailableError(_sanitize(safe_msg))


def _is_retryable(exc: Exception) -> bool:
    """Determine whether an error is transient and warrants a retry."""
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, httpx.NetworkError, ConnectionError)):
        return True
    msg_lower = str(exc).lower()
    return any(k in msg_lower for k in ["timeout", "timed out", "quota", "429", "503", "500", "unavailable"])


def get_client() -> genai.Client:
    """Return an authenticated genai Client using settings.

    Raises:
        LLMUnavailableError: If gemini_api_key or gemini_model is missing/empty.
    """
    try:
        api_key = settings.require_gemini_api_key()
    except ValueError as err:
        raise LLMUnavailableError(_sanitize(str(err))) from err

    timeout_ms = int(settings.llm_timeout_seconds * 1000)
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )


def generate_json(
    system_prompt: str,
    user_content: str,
    response_schema: Any = None,
) -> dict[str, Any]:
    """Generate a structured JSON response using Gemini.

    Args:
        system_prompt: System instructions for the model.
        user_content: Untrusted user input/context.
        response_schema: Optional Pydantic model class or JSON schema dict.

    Returns:
        Parsed dict representation of the model's response.

    Raises:
        LLMUnavailableError: On provider failure, timeout, auth error, or parse error.
    """
    try:
        model = settings.require_gemini_model()
        settings.require_gemini_api_key()
    except ValueError as err:
        raise LLMUnavailableError(_sanitize(str(err))) from err

    timeout_ms = int(settings.llm_timeout_seconds * 1000)
    config_kwargs: dict[str, Any] = {
        "system_instruction": system_prompt,
        "max_output_tokens": settings.llm_max_output_tokens,
        "response_mime_type": "application/json",
        "http_options": types.HttpOptions(timeout=timeout_ms),
    }
    if response_schema is not None:
        config_kwargs["response_schema"] = response_schema

    config = types.GenerateContentConfig(**config_kwargs)
    client = get_client()

    max_retries = max(0, settings.llm_max_retries)
    attempts = 1 + max_retries

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_content,
                config=config,
            )
            raw_text = (response.text or "").strip()
            if not raw_text:
                raise LLMUnavailableError("LLM returned an empty response.")

            # Strip markdown fences if present
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            raw_text = raw_text.removesuffix("```").strip()

            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError as json_err:
                raise LLMUnavailableError("Failed to parse LLM response as valid JSON.") from json_err

            if not isinstance(parsed, dict):
                raise LLMUnavailableError("LLM response was not a valid JSON object.")

            return parsed

        except LLMUnavailableError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1 and _is_retryable(exc):
                logger.warning("LLM call attempt %d failed; retrying...", attempt + 1)
                time.sleep(0.1)
                continue
            raise _to_llm_unavailable_error(exc) from exc

    if last_error:
        raise _to_llm_unavailable_error(last_error)
    raise LLMUnavailableError("LLM call failed.")


def generate_text(system_prompt: str, user_content: str) -> str:
    """Generate plain text from Gemini.

    Args:
        system_prompt: System instructions for the model.
        user_content: Untrusted user input/context.

    Returns:
        Generated text string.

    Raises:
        LLMUnavailableError: On provider failure, timeout, auth error, or empty response.
    """
    try:
        model = settings.require_gemini_model()
        settings.require_gemini_api_key()
    except ValueError as err:
        raise LLMUnavailableError(_sanitize(str(err))) from err

    timeout_ms = int(settings.llm_timeout_seconds * 1000)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=settings.llm_max_output_tokens,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    client = get_client()

    max_retries = max(0, settings.llm_max_retries)
    attempts = 1 + max_retries

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_content,
                config=config,
            )
            raw_text = (response.text or "").strip()
            return raw_text

        except LLMUnavailableError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1 and _is_retryable(exc):
                logger.warning("LLM call attempt %d failed; retrying...", attempt + 1)
                time.sleep(0.1)
                continue
            raise _to_llm_unavailable_error(exc) from exc

    if last_error:
        raise _to_llm_unavailable_error(last_error)
    raise LLMUnavailableError("LLM call failed.")
