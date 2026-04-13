"""
Tests for GeminiClient fallback logic.

Verifies that on 429/503 the client retries with the fallback model URL,
and that on other errors or when the fallback also fails it raises correctly.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.llm.gemini_client import GeminiClient

PRIMARY = "gemini-2.5-flash"
FALLBACK = "gemini-2.5-flash-lite"
API_KEY = "test-key"

_SUCCESS_BODY = {
    "candidates": [
        {"content": {"parts": [{"text": "hello"}]}}
    ],
    "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 5,
        "totalTokenCount": 15,
    },
}


_DUMMY_REQUEST = httpx.Request("POST", "https://generativelanguage.googleapis.com/")


def _make_response(status: int, body: dict | None = None) -> httpx.Response:
    """Build a minimal httpx.Response for mocking (request required by raise_for_status)."""
    content = json.dumps(body or {}).encode()
    return httpx.Response(status_code=status, content=content, request=_DUMMY_REQUEST)


def _primary_url(model: str = PRIMARY, key: str = API_KEY) -> str:
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={key}"
    )


# ---------------------------------------------------------------------------
# vision_generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_generate_uses_primary_url_on_success():
    """Happy path: primary model URL called and text returned."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)
    mock_post = AsyncMock(return_value=_make_response(200, _SUCCESS_BODY))

    with patch.object(client._client, "post", mock_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            result = await client.vision_generate(
                system_prompt="sys",
                user_prompt="user",
                base64_images=[],
                temperature=0.5,
            )

    assert result == "hello"
    called_url = mock_post.call_args[0][0]
    assert PRIMARY in called_url
    assert f"key={API_KEY}" in called_url


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger_status", [429, 503])
async def test_vision_generate_falls_back_on_capacity_error(trigger_status: int):
    """429 or 503 on primary triggers retry with fallback model URL."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    primary_resp = _make_response(trigger_status, {"error": "overloaded"})
    fallback_resp = _make_response(200, _SUCCESS_BODY)

    call_count = 0

    async def mock_post(url: str, **kwargs):
        nonlocal call_count
        call_count += 1
        if PRIMARY in url:
            resp = primary_resp
            resp.raise_for_status()  # raises HTTPStatusError
        return fallback_resp

    # Use httpx.HTTPStatusError-aware mock
    primary_error = httpx.HTTPStatusError(
        message=f"HTTP {trigger_status}",
        request=httpx.Request("POST", _primary_url(PRIMARY)),
        response=primary_resp,
    )

    call_urls: list[str] = []

    async def tracked_post(url: str, **kwargs):
        call_urls.append(url)
        if f"/models/{PRIMARY}:" in url:
            raise primary_error
        return fallback_resp

    with patch.object(client._client, "post", tracked_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            result = await client.vision_generate(
                system_prompt="sys",
                user_prompt="user",
                base64_images=[],
                temperature=0.5,
            )

    assert result == "hello"
    assert len(call_urls) == 2
    assert f"/models/{PRIMARY}:" in call_urls[0], "First call must use primary model URL"
    assert f"/models/{FALLBACK}:" in call_urls[1], "Second call must use fallback model URL"
    assert f"key={API_KEY}" in call_urls[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger_status", [429, 503])
async def test_vision_generate_raises_when_fallback_also_fails(trigger_status: int):
    """Raises ValueError when both primary and fallback return 429/503."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    def _capacity_error(model: str) -> httpx.HTTPStatusError:
        resp = _make_response(trigger_status, {"error": "overloaded"})
        return httpx.HTTPStatusError(
            message=f"HTTP {trigger_status}",
            request=httpx.Request("POST", _primary_url(model)),
            response=resp,
        )

    async def tracked_post(url: str, **kwargs):
        if f"/models/{PRIMARY}:" in url:
            raise _capacity_error(PRIMARY)
        raise _capacity_error(FALLBACK)

    with patch.object(client._client, "post", tracked_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            with pytest.raises(ValueError, match="capacity error"):
                await client.vision_generate(
                    system_prompt="sys",
                    user_prompt="user",
                    base64_images=[],
                    temperature=0.5,
                )


@pytest.mark.asyncio
async def test_vision_generate_no_fallback_on_401():
    """401 raises immediately — no fallback attempt."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)
    resp_401 = _make_response(401, {"error": "unauthorized"})
    error_401 = httpx.HTTPStatusError(
        message="HTTP 401",
        request=httpx.Request("POST", _primary_url()),
        response=resp_401,
    )

    call_urls: list[str] = []

    async def tracked_post(url: str, **kwargs):  # noqa: RUF029
        call_urls.append(url)
        raise error_401

    with patch.object(client._client, "post", tracked_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            with pytest.raises(ValueError, match="Invalid Gemini API key"):
                await client.vision_generate(
                    system_prompt="sys",
                    user_prompt="user",
                    base64_images=[],
                    temperature=0.5,
                )

    assert len(call_urls) == 1, "Must not attempt fallback on 401"


# ---------------------------------------------------------------------------
# generate_content
# ---------------------------------------------------------------------------

_TEXT_SUCCESS_BODY = {
    "candidates": [
        {"content": {"parts": [{"text": "response text"}]}}
    ],
    "usageMetadata": {
        "promptTokenCount": 8,
        "candidatesTokenCount": 4,
        "totalTokenCount": 12,
    },
}


@pytest.mark.asyncio
async def test_generate_content_uses_primary_url_on_success():
    """Happy path: primary model URL used and text returned."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)
    mock_post = AsyncMock(return_value=_make_response(200, _TEXT_SUCCESS_BODY))

    with patch.object(client._client, "post", mock_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            result = await client.generate_content(
                system_prompt="sys",
                user_prompt="user",
            )

    assert result == "response text"
    called_url = mock_post.call_args[0][0]
    assert PRIMARY in called_url
    assert f"key={API_KEY}" in called_url


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger_status", [429, 503])
async def test_generate_content_falls_back_on_capacity_error(trigger_status: int):
    """429 or 503 on primary triggers retry with fallback model URL."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)
    primary_resp = _make_response(trigger_status, {"error": "overloaded"})
    primary_error = httpx.HTTPStatusError(
        message=f"HTTP {trigger_status}",
        request=httpx.Request("POST", _primary_url(PRIMARY)),
        response=primary_resp,
    )

    call_urls: list[str] = []

    async def tracked_post(url: str, **kwargs):
        call_urls.append(url)
        if f"/models/{PRIMARY}:" in url:
            raise primary_error
        return _make_response(200, _TEXT_SUCCESS_BODY)

    with patch.object(client._client, "post", tracked_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            result = await client.generate_content(
                system_prompt="sys",
                user_prompt="user",
            )

    assert result == "response text"
    assert len(call_urls) == 2
    assert f"/models/{PRIMARY}:" in call_urls[0], "First call must use primary model URL"
    assert f"/models/{FALLBACK}:" in call_urls[1], "Second call must use fallback model URL"
    assert f"key={API_KEY}" in call_urls[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger_status", [429, 503])
async def test_generate_content_raises_when_fallback_also_fails(trigger_status: int):
    """Raises when both primary and fallback return 429/503."""
    client = GeminiClient(api_key=API_KEY, default_model=PRIMARY)

    def _err(model: str) -> httpx.HTTPStatusError:
        resp = _make_response(trigger_status, {"error": "overloaded"})
        return httpx.HTTPStatusError(
            message=f"HTTP {trigger_status}",
            request=httpx.Request("POST", _primary_url(model)),
            response=resp,
        )

    async def tracked_post(url: str, **kwargs):
        if f"/models/{PRIMARY}:" in url:
            raise _err(PRIMARY)
        raise _err(FALLBACK)

    with patch.object(client._client, "post", tracked_post):
        with patch("app.llm.gemini_client.settings") as mock_settings:
            mock_settings.gemini_fallback_model = FALLBACK
            with pytest.raises(httpx.HTTPStatusError):
                await client.generate_content(
                    system_prompt="sys",
                    user_prompt="user",
                )
