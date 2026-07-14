"""
Shared google-genai SDK client and helpers.

Provides a cached GenAI client and convenience wrappers for structured output,
text generation, and embeddings. The client auto-selects the backend based on
settings.gemini_provider:

  "ai_studio"  → genai.Client(api_key=...)            (GOOGLE_GENAI_USE_ENTERPRISE not set)
  "vertex_ai"  → genai.Client(project=..., location=...) (uses ADC / service account)

Usage:

    from app.llm.genai import get_client, generate_structured, generate_content

    # Structured output (Pydantic schema)
    result, usage = generate_structured(
        model="gemini-3.1-flash-lite",
        system_prompt="...",
        user_content="...",
        schema=MyPydanticModel,
        temperature=0.0,
        phase="my_phase",
    )

    # Text output
    text, usage = generate_content(
        model="gemini-3.1-flash-lite",
        system_prompt="...",
        user_content="...",
        temperature=0.3,
        max_output_tokens=1024,
        phase="my_phase",
    )
"""

from __future__ import annotations

import base64
import json
import time
from functools import lru_cache
from typing import Any

import structlog
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.llm.gemini_pricing import usage_record

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Cached client
# ---------------------------------------------------------------------------


def _build_client() -> genai.Client:
    """Create a GenAI client targeting the configured provider (ai_studio | vertex_ai)."""
    if settings.gemini_provider == "vertex_ai":
        return genai.Client(
            project=settings.gemini_project_id,
            location=settings.gemini_region,
        )
    # AI Studio (default) — v1beta needed for systemInstruction field support.
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Return a cached GenAI client (reused across all LLM calls)."""
    return _build_client()


# ---------------------------------------------------------------------------
# Structured-output generation (replaces invoke_structured_gemini)
# ---------------------------------------------------------------------------


def generate_structured(
    *,
    model: str,
    temperature: float,
    schema: type[BaseModel],
    system_prompt: str,
    user_content: str | list[Any],
    phase: str,
) -> tuple[Any, dict]:
    """
    Single structured-output call via google-genai SDK.

    Returns (parsed_pydantic_instance, usage_row dict).
    The usage row has the same shape as gemini_pricing.usage_record().
    """
    client = get_client()
    t0 = time.monotonic()

    config = {
        "temperature": temperature,
        "response_mime_type": "application/json",
        "response_schema": schema,
        "system_instruction": system_prompt,
    }

    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=config,
    )

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # Parse structured output
    parsed = schema.model_validate_json(response.text)

    # Build usage row
    row = _usage_row_from_response(response, phase=phase, model=model)

    logger.info(
        "llm_lifecycle",
        stage="genai_structured_complete",
        phase=phase,
        model=model,
        temperature=temperature,
        elapsed_ms=elapsed_ms,
        prompt_tokens=row.get("prompt_tokens"),
        candidates_tokens=row.get("candidates_tokens"),
        total_tokens=row.get("total_tokens"),
        cost_usd=row.get("cost_usd"),
    )

    return parsed, row


# ---------------------------------------------------------------------------
# Text-only generation (replaces GeminiClient.generate_content)
# ---------------------------------------------------------------------------


def generate_content(
    *,
    model: str,
    temperature: float,
    system_prompt: str,
    user_content: str | list[Any],
    max_output_tokens: int = 1024,
    phase: str = "genai_generate_content",
) -> tuple[str, dict]:
    """Text-only generation call via google-genai SDK. Returns (text, usage_row)."""
    client = get_client()
    t0 = time.monotonic()

    config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "system_instruction": system_prompt,
    }

    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=config,
    )

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    text = response.text
    row = _usage_row_from_response(response, phase=phase, model=model)

    logger.info(
        "llm_lifecycle",
        stage="genai_content_complete",
        phase=phase,
        model=model,
        temperature=temperature,
        elapsed_ms=elapsed_ms,
        prompt_tokens=row.get("prompt_tokens"),
        candidates_tokens=row.get("candidates_tokens"),
        total_tokens=row.get("total_tokens"),
        cost_usd=row.get("cost_usd"),
    )

    return text, row


# ---------------------------------------------------------------------------
# Vision generation (replaces GeminiClient.vision_generate)
# ---------------------------------------------------------------------------


def generate_vision(
    *,
    model: str,
    temperature: float,
    system_prompt: str,
    user_prompt: str,
    base64_images: list[str],
    max_output_tokens: int = 2000,
    response_schema: dict | None = None,
    phase: str = "genai_vision_generate",
) -> tuple[str, dict]:
    """Vision (text + image) generation call via google-genai SDK. Returns (text, usage_row)."""
    client = get_client()
    t0 = time.monotonic()

    parts: list[Any] = [types.Part.from_text(text=user_prompt)]
    for img_b64 in base64_images:
        image_bytes = base64.b64decode(img_b64)
        parts.append(types.Part.from_bytes(mime_type="image/jpeg", data=image_bytes))

    config: dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "system_instruction": system_prompt,
    }
    if response_schema is not None:
        config["response_mime_type"] = "application/json"
        config["response_schema"] = response_schema

    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=config,
    )

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    text = response.text
    row = _usage_row_from_response(response, phase=phase, model=model)

    logger.info(
        "llm_lifecycle",
        stage="genai_vision_complete",
        phase=phase,
        model=model,
        temperature=temperature,
        elapsed_ms=elapsed_ms,
        prompt_tokens=row.get("prompt_tokens"),
        candidates_tokens=row.get("candidates_tokens"),
        total_tokens=row.get("total_tokens"),
        cost_usd=row.get("cost_usd"),
    )

    return text, row


# ---------------------------------------------------------------------------
# Embedding generation (replaces GoogleGenerativeAIEmbeddings)
# ---------------------------------------------------------------------------


def generate_embedding(
    text: str,
    model: str | None = None,
    dimensions: int | None = None,
) -> list[float] | None:
    """Generate an embedding vector via google-genai SDK. Returns list of floats or None."""
    client = get_client()
    embed_model = model or settings.gemini_embedding_model

    try:
        config: dict[str, Any] = {}
        if dimensions is not None:
            config["output_dimensionality"] = dimensions

        result = client.models.embed_content(
            model=embed_model,
            contents=[text],
            config=config,
        )
        embedding = result.embeddings[0].values
        if embedding is None:
            return None

        expected = dimensions or 768
        if len(embedding) != expected:
            logger.error(
                "embedding_dimension_mismatch",
                embedding_model=embed_model,
                expected_dim=expected,
                actual_dim=len(embedding),
            )
            return None

        return embedding

    except Exception as e:  # pragma: no cover
        logger.error(
            "embedding_api_failed",
            error=str(e),
            text_preview=text[:120] if text else "",
            embedding_model=embed_model,
        )
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _usage_row_from_response(
    response: Any,
    *,
    phase: str,
    model: str,
) -> dict:
    """Extract token usage from a GenAI SDK response and return a usage_record dict."""
    um = getattr(response, "usage_metadata", None)
    if um is None:
        return {
            "phase": phase,
            "model": model,
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "cost_inr": 0.0,
        }

    pt = int(getattr(um, "prompt_token_count", 0) or 0)
    ct = int(getattr(um, "candidates_token_count", 0) or 0)
    cached = int(getattr(um, "cached_content_token_count", 0) or 0)
    tt = pt + ct

    return usage_record(
        phase=phase,
        model=model,
        prompt_tokens=pt,
        candidates_tokens=ct,
        cached_tokens=cached,
        total_tokens=tt,
    )
