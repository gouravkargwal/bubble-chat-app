"""
Integration tests for GeminiClient — hits the real Gemini API.

Uses settings loaded from .env.dev (default ENV_FILE).
Skipped automatically when GEMINI_API_KEY is missing from settings.

Run:
    pytest tests/test_gemini_client_integration.py -v -s
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.llm.gemini_client import GeminiClient

pytestmark = pytest.mark.skipif(
    not settings.gemini_api_key,
    reason="GEMINI_API_KEY not configured in settings — skipping live API tests",
)

PRIMARY_MODEL = settings.gemini_model
FALLBACK_MODEL = settings.gemini_fallback_model


@pytest.fixture
async def gemini_client():
    client = GeminiClient(api_key=settings.gemini_api_key, default_model=PRIMARY_MODEL)
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# generate_content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_content_primary_returns_text(gemini_client: GeminiClient):
    """Primary model responds with non-empty text."""
    result = await gemini_client.generate_content(
        system_prompt="You are a helpful assistant. Reply in one short sentence.",
        user_prompt="Say hello.",
        model=PRIMARY_MODEL,
        max_output_tokens=64,
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    print(f"\n[primary={PRIMARY_MODEL}] {result!r}")


@pytest.mark.asyncio
async def test_generate_content_fallback_model_returns_text(gemini_client: GeminiClient):
    """Fallback model responds when called directly."""
    result = await gemini_client.generate_content(
        system_prompt="You are a helpful assistant. Reply in one short sentence.",
        user_prompt="Say hello.",
        model=FALLBACK_MODEL,
        max_output_tokens=64,
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    print(f"\n[fallback={FALLBACK_MODEL}] {result!r}")


# ---------------------------------------------------------------------------
# vision_generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_generate_primary_returns_text(gemini_client: GeminiClient):
    """vision_generate with no images returns valid text from primary model."""
    result = await gemini_client.vision_generate(
        system_prompt='Reply with a valid JSON object: {"ok": true}',
        user_prompt="respond now",
        base64_images=[],
        temperature=0.0,
        model=PRIMARY_MODEL,
        max_output_tokens=64,
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    print(f"\n[vision primary={PRIMARY_MODEL}] {result!r}")


@pytest.mark.asyncio
async def test_vision_generate_fallback_model_returns_text(gemini_client: GeminiClient):
    """vision_generate works correctly when called with fallback model directly."""
    result = await gemini_client.vision_generate(
        system_prompt='Reply with a valid JSON object: {"ok": true}',
        user_prompt="respond now",
        base64_images=[],
        temperature=0.0,
        model=FALLBACK_MODEL,
        max_output_tokens=64,
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    print(f"\n[vision fallback={FALLBACK_MODEL}] {result!r}")
