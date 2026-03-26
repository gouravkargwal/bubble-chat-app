"""
Shared constants, helpers, and utilities for V2 agent nodes.
"""

from typing import cast, Any
import asyncio
import base64

import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import settings
from app.services.memory_service import get_match_context
from app.infrastructure.database.engine import librarian_async_session
from agent.state import AgentState

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LLM_TIMEOUT_SECONDS = 30
LLM_MAX_RETRIES = 2
REQUIRED_REPLY_COUNT = 4
MAX_REWRITES = 1  # Max rewrite attempts before shipping as-is

# Same model id as `settings.gemini_model` / `GEMINI_MODEL` in `.env` — one knob for
# vision + generator + auditor (LangChain). Hybrid OCR and GeminiClient paths also use
# settings.gemini_model via callers.
_AGENT_MODEL = settings.gemini_model
VISION_MODEL = _AGENT_MODEL
GENERATOR_MODEL = _AGENT_MODEL
AUDITOR_MODEL = _AGENT_MODEL

# MIME magic bytes for common image formats
_MIME_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # WebP starts with RIFF
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def truncate(val: Any, max_len: int = 220) -> Any:
    """Truncate noisy strings/lists for logs (never touch base64/image)."""
    if isinstance(val, str):
        return val if len(val) <= max_len else val[: max_len - 3] + "..."
    if isinstance(val, list):
        return [truncate(v, max_len=max_len) for v in val[:10]]
    if isinstance(val, dict):
        return {k: truncate(v, max_len=max_len) for k, v in list(val.items())[:30]}
    return val


def _detect_mime_type(data: str | bytes) -> str:
    """Detect image MIME type from base64 string or raw bytes. Falls back to JPEG."""
    raw: bytes
    if isinstance(data, str):
        # Strip data URI prefix if present
        if data.startswith("data:image"):
            return data  # Already has MIME type embedded
        try:
            raw = base64.b64decode(data[:32])  # Only need first few bytes
        except Exception:
            return f"data:image/jpeg;base64,{data}"
    elif isinstance(data, (bytes, bytearray)):
        raw = bytes(data[:16])
    else:
        return f"data:image/jpeg;base64,{data}"

    for signature, mime in _MIME_SIGNATURES:
        if raw[: len(signature)] == signature:
            if isinstance(data, str):
                return f"data:{mime};base64,{data}"
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"

    # Default to JPEG
    if isinstance(data, str):
        return f"data:image/jpeg;base64,{data}"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def encode_image_from_state(state: AgentState) -> str:
    """Encode image from state with correct MIME type detection."""
    img = state.get("image_bytes")
    if img is None:
        raise ValueError("vision_node requires 'image_bytes' in state.")
    if isinstance(img, str) and img.startswith("data:image"):
        return img
    return _detect_mime_type(img)


def normalize_raw_ocr_text(raw_ocr_text: Any) -> list[dict[str, Any]]:
    """Convert raw_ocr_text into plain JSON-serializable dicts."""
    if raw_ocr_text is None:
        return []
    if isinstance(raw_ocr_text, str):
        return [
            {
                "sender": "them",
                "actual_new_message": raw_ocr_text,
                "quoted_context": None,
                "is_reply": False,
            }
        ]
    if isinstance(raw_ocr_text, list):
        normalized: list[dict[str, Any]] = []
        for item in raw_ocr_text:
            if hasattr(item, "model_dump"):
                normalized.append(cast(dict[str, Any], item.model_dump()))
            elif isinstance(item, dict):
                normalized.append(item)
        return normalized
    return []


def transcript_text_from_analysis(analysis: Any) -> str:
    """
    Verbatim text the user is replying to: latest left-aligned ("them") bubble's
    actual_new_message only (ignores quoted_context). Matches generator_node logic.
    """
    visual_transcript = getattr(analysis, "visual_transcript", None) or []
    if not isinstance(visual_transcript, list):
        return ""

    def _sender(bubble: Any) -> str:
        if isinstance(bubble, dict):
            return str(bubble.get("sender") or "")
        return str(getattr(bubble, "sender", "") or "")

    def _actual(bubble: Any) -> str:
        if isinstance(bubble, dict):
            return str(bubble.get("actual_new_message") or "")
        return str(getattr(bubble, "actual_new_message", "") or "")

    transcript_text = ""
    for bubble in reversed(visual_transcript):
        if _sender(bubble) == "them":
            transcript_text = _actual(bubble)
            break

    if transcript_text:
        return transcript_text

    for bubble in reversed(visual_transcript):
        text = _actual(bubble)
        if text:
            return text

    return ""


def has_forbidden_punctuation(text: str) -> bool:
    """Check if text contains any forbidden punctuation characters."""
    forbidden = ["'", '"', ",", ".", "!", "?", ";"]
    return any(ch in text for ch in forbidden)


def build_llm(
    *,
    model: str,
    temperature: float,
    structured_output: type[BaseModel] | None = None,
) -> Any:
    """Build a Gemini LLM client with timeout, retry, and optional structured output."""
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )
    if structured_output:
        return llm.with_structured_output(structured_output)
    return llm


# ---------------------------------------------------------------------------
# Librarian: shared DB engine (no per-call connection pool creation)
# ---------------------------------------------------------------------------


def fetch_librarian_context(
    user_id: str,
    conversation_id: str,
    current_text: str,
) -> dict[str, str]:
    """Sync wrapper for thread contexts that cannot `await` directly."""

    async def _fetch() -> dict[str, str]:
        return await fetch_librarian_context_async(
            user_id=user_id,
            conversation_id=conversation_id,
            current_text=current_text,
        )

    # LangGraph nodes run in threads via asyncio.to_thread, so we need a new loop
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_fetch())
    finally:
        loop.close()


async def fetch_librarian_context_async(
    user_id: str,
    conversation_id: str,
    current_text: str,
) -> dict[str, str]:
    """Async-native librarian fetch for async endpoints/tasks."""
    async with librarian_async_session() as local_db:
        return await get_match_context(
            local_db,
            user_id=user_id,
            conversation_id=conversation_id,
            current_text=current_text,
        )


def sanitize_llm_messages_for_logging(messages: list[Any]) -> list[dict[str, Any]]:
    """
    Convert LangChain message objects into JSON-serializable logs.

    Important: we intentionally omit/replace base64 image URLs because they are
    extremely large and not useful for debugging text behavior.
    """

    def _sanitize_content(content: Any) -> Any:
        # HumanMessage content can be either a string or a list of parts
        # (e.g. [{type: "text", text: ...}, {type: "image_url", image_url: {url: ...}}]).
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            sanitized_parts: list[Any] = []
            for part in content:
                if isinstance(part, dict):
                    part_type = part.get("type")
                    if part_type == "image_url":
                        url = (
                            (part.get("image_url") or {}).get("url")
                            if isinstance(part.get("image_url"), dict)
                            else None
                        )
                        url_str = str(url or "")
                        sanitized_parts.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "<omitted_image_base64>",
                                    "url_length": len(url_str),
                                },
                            }
                        )
                        continue
                    sanitized_parts.append(part)
                else:
                    sanitized_parts.append(part)
            return sanitized_parts

        # Fallback: keep it as-is (must remain JSON-serializable at callsite)
        return content

    sanitized: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.__class__.__name__
        content = getattr(msg, "content", None)
        sanitized.append(
            {
                "role": role,
                "content": _sanitize_content(content),
            }
        )
    return sanitized
