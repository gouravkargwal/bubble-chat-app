"""
Tests for GeminiClient using google-genai SDK.

The SDK handles retries and errors internally, so these tests verify
that the GeminiClient wrapper correctly delegates to the SDK and
propagates errors.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.gemini_client import GeminiClient
from google.genai import types

PRIMARY = "gemini-3.1-flash-lite"
API_KEY = "test-key"


def _mock_sdk_response(text: str = "hello") -> MagicMock:
    """Build a mock GenAI SDK response with usage metadata."""
    resp = MagicMock()
    resp.text = text
    resp.candidates = [MagicMock()]
    resp.candidates[0].content = types.Content(
        parts=[types.Part(text=text)], role="model"
    )
    um = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=10,
        candidates_token_count=5,
        total_token_count=15,
        cached_content_token_count=0,
    )
    resp.usage_metadata = um
    return resp


def _mock_empty_response() -> MagicMock:
    """Build a mock response with no text (triggers ValueError)."""
    resp = MagicMock()
    resp.text = ""
    resp.candidates = []
    resp.usage_metadata = None
    return resp


# ---------------------------------------------------------------------------
# vision_generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_generate_uses_sdk_on_success():
    """Happy path: SDK client called and text returned."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    mock_sdk = MagicMock()
    mock_sdk.models.generate_content.return_value = _mock_sdk_response()
    mock_get_client = MagicMock(return_value=mock_sdk)

    with patch("app.llm.gemini_client.get_client", mock_get_client):
        result = await client.vision_generate(
            system_prompt="sys",
            user_prompt="user",
            base64_images=[],
            temperature=0.5,
        )

    assert result == "hello"
    mock_sdk.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_vision_generate_raises_on_empty_response():
    """Empty response raises ValueError."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    mock_sdk = MagicMock()
    mock_sdk.models.generate_content.return_value = _mock_empty_response()
    mock_get_client = MagicMock(return_value=mock_sdk)

    with patch("app.llm.gemini_client.get_client", mock_get_client):
        with pytest.raises(ValueError, match="Empty text"):
            await client.vision_generate(
                system_prompt="sys",
                user_prompt="user",
                base64_images=[],
                temperature=0.5,
            )


@pytest.mark.asyncio
async def test_vision_generate_sdk_error_propagates():
    """SDK errors propagate through the wrapper."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    mock_sdk = MagicMock()
    mock_sdk.models.generate_content.side_effect = RuntimeError("SDK failure")
    mock_get_client = MagicMock(return_value=mock_sdk)

    with patch("app.llm.gemini_client.get_client", mock_get_client):
        with pytest.raises(RuntimeError, match="SDK failure"):
            await client.vision_generate(
                system_prompt="sys",
                user_prompt="user",
                base64_images=[],
                temperature=0.5,
            )


# ---------------------------------------------------------------------------
# generate_content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_content_uses_sdk_on_success():
    """Happy path: SDK client called and text returned."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    mock_sdk = MagicMock()
    mock_sdk.models.generate_content.return_value = _mock_sdk_response("response text")
    mock_get_client = MagicMock(return_value=mock_sdk)

    with patch("app.llm.gemini_client.get_client", mock_get_client):
        result = await client.generate_content(
            system_prompt="sys",
            user_prompt="user",
        )

    assert result == "response text"


@pytest.mark.asyncio
async def test_generate_content_sdk_error_propagates():
    """SDK errors propagate through the wrapper."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    mock_sdk = MagicMock()
    mock_sdk.models.generate_content.side_effect = RuntimeError("SDK failure")
    mock_get_client = MagicMock(return_value=mock_sdk)

    with patch("app.llm.gemini_client.get_client", mock_get_client):
        with pytest.raises(RuntimeError, match="SDK failure"):
            await client.generate_content(
                system_prompt="sys",
                user_prompt="user",
            )
