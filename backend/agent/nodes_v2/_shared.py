"""
Shared constants, helpers, and utilities for V2 agent nodes.
"""

from typing import Any, Literal, cast
import asyncio
import base64
import hashlib

import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import settings
from app.services.memory_service import get_match_context
from app.infrastructure.database.engine import librarian_async_session
from agent.state import AgentState, AnalystOutput

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LLM_TIMEOUT_SECONDS = 120.0
LLM_MAX_RETRIES = 2
REQUIRED_REPLY_COUNT = 4
MAX_REWRITES = 1  # Max rewrite attempts before shipping as-is

# Single source of truth for what each strategy_label MEANS. Injected into BOTH
# the generator (so it labels consistently) and the auditor (so it can catch
# mismatches). Consistency matters more than philosophical purity: Phase 5 learns
# "what works" keyed on strategy_label, so the SAME tactic must always get the
# SAME label or the learning signal is corrupted.
STRATEGY_LABEL_GLOSSARY = """STRATEGY LABEL DEFINITIONS (label each reply by what it ACTUALLY does — pick the dominant tactic):
* PUSH-PULL — gives and takes in one line: a compliment/acknowledgment immediately undercut by a tease or challenge. Litmus: it BOTH warms AND pokes. ("you seem fun but i bet you're trouble")
* FRAME CONTROL — you set or flip the frame: reinterpret her statement, define the terms, or assign roles. ALL "would you rather / A or B" hypotheticals go here (YOU set the choice). Litmus: you control the narrative or the choice, not her.
* VALUE ANCHOR — anchors on a specific real detail to build genuine connection; shows you actually noticed something concrete. Litmus: grounds in a real detail to CONNECT, not to tease.
* PATTERN INTERRUPT — an unexpected angle that breaks the predictable opener script. Litmus: she would NOT see it coming.
* HONEST FRAME — sincere and direct, no game: states something genuine or names something plainly. Litmus: earnest, zero tease, no tactic underneath.
* SOFT CLOSE — gently nudges momentum toward a next step (keep talking / meet) without a hard ask. Litmus: moves the interaction forward.
The strategy_label MUST match the litmus for the reply text. A question that makes her pick between two options = FRAME CONTROL, NOT HONEST FRAME. Pure validation/agreement is NOT a tactic — if a reply only validates, it is HONEST FRAME."""

# The illustrative example phrases baked into the prompts TEACH a technique —
# they are NOT lines to send. The generator has been observed copying them
# verbatim (e.g. "hits snooze 6 times"), producing generic replies ungrounded in
# HER profile. Treat these as banned strings in both the generator self-check and
# the auditor, the same way last_ai_replies_shown is treated for freshness.
BANNED_EXAMPLE_PHRASES = """BANNED EXAMPLE LINES (these phrases appear in your instructions only to ILLUSTRATE a technique — they are NOT content to send). NEVER reproduce any of them verbatim or near-verbatim; build the SAME technique from HER actual profile instead. A reply reusing one = automatic rewrite:
* "hits snooze 6 times" / "snooze 6 times" / "shows up with iced coffee"
* "i was going to say hi but then i saw your taste in music"
* "rot on the couch"
* "half marathon is just a biryani excuse"
* "goa as their answer to everything"
These are full canned SENTENCES. A single common word from one of them (biryani, goa, coffee, hiking, marathon, chai) is NOT banned on its own — only the specific sentence/construction is. e.g. "har weekend biryani khaogi?" is FINE; "the half marathon is just a biryani excuse" is NOT.
EXCEPTION: if HER profile genuinely contains the topic (she really mentions a half marathon, goa, etc.), you may reference the real detail — but never paste the canned phrasing."""

# Single source of truth for the AI-SMELL scaffold rule, shared by the generator
# (don't WRITE these) and the auditor (don't FAIL the allowed forms). Keeping it in
# one place stops the two from drifting — that drift is what made the auditor reject
# the generator's own allowed "are you the type who" jab. KEY: a scaffold is a SOFT
# OBSERVATIONAL OPENER; judge the OPENING WORDS, never the mere presence of "type who".
SCAFFOLD_RULE = """A SCAFFOLD is a SOFT OBSERVATIONAL OPENER — judge ONLY the reply's opening words. Banned openers: "you strike me as", any "you seem ..." ("you seem like the type", "you seem the type to", "you seem efficient"), "you look like ...", "i get the sense", "i suspect", "i need to know if", "there's something about you that", "i feel like you're the kind of person who", and balanced "either you X or you Y". The mere presence of "the type who/to" is NEVER itself a scaffold — the DIRECT forms are GOOD and wanted: "are you the type who [behavior]", "bet you [behavior]", a short "type who [behavior]" jab. Flip a soft opener to a direct jab ("you seem the type to over-plan" -> "bet you over-plan everything"). Do NOT generalize the ban beyond the openers listed (e.g. "you clearly", "i can tell", "sounds like you" are NOT scaffolds)."""

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

# Substrings that suggest bio/chat text worth prioritizing over pure visual openers.
_OPENER_TEXT_SIGNALS: tuple[str, ...] = (
    "trust",
    "anxiety",
    "honest",
    "hurt",
    "scared",
    "therapy",
    "mental",
    "depress",
    "anxious",
    "issue",
    "feel ",
    "vulnerab",
    "opinion",
    "believe",
    "politic",
    "controvers",
)


def opener_hook_priority(
    analysis: AnalystOutput, transcript_text: str
) -> Literal["text_first", "visual_first", "either"]:
    """
    For opener direction: prefer reacting to substantive profile/bio text vs visual_hooks.
    Keeps generator and auditor aligned so text-led openers are not failed for skipping glasses/color.
    """
    t = (transcript_text or "").strip().lower()
    hooks = [h for h in (getattr(analysis, "visual_hooks", None) or []) if str(h).strip()]
    text_signals = any(s in t for s in _OPENER_TEXT_SIGNALS)
    substantive = len(t) >= 40
    # A bare structured-field label (e.g. "relationship goals: long-term relationship")
    # trips the length check but is NOT rich text — anchoring all 4 replies on it
    # produces monotony (4 variations of "long-term"). If that's essentially all the
    # text there is and photos exist, spread across the visual hooks instead.
    bare_label = (
        ("relationship goal" in t or "long-term" in t or "long term" in t)
        and len(t) <= 70
    )
    if bare_label and len(hooks) >= 1 and not text_signals:
        return "either"
    if (text_signals or substantive) and len(t) >= 8:
        return "text_first"
    if len(hooks) >= 2:
        return "visual_first"
    return "either"


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


def downscale_image_b64(b64: str, max_edge: int = 768, jpeg_quality: int = 82) -> str:
    """Resize a base64 image so its longest edge is <= max_edge, re-encoded as JPEG.

    Gemini bills images by 768px tiles, so a tall phone screenshot (e.g. 1080x2400)
    costs several tiles. Capping the long edge at ~768 collapses it to ~one tile —
    cutting vision token cost sharply with no OCR-legibility loss. Best-effort:
    returns the input UNCHANGED on any failure (incl. Pillow not installed), so the
    vision call is never blocked. Accepts a raw base64 string or a data: URL; returns
    raw base64 (the caller's encoder re-adds the MIME prefix).
    """
    try:
        if not b64 or not isinstance(b64, str):
            return b64
        payload = b64.split(",", 1)[1] if b64.startswith("data:") else b64

        import io

        from PIL import Image

        raw = base64.b64decode(payload)
        img = Image.open(io.BytesIO(raw))
        if max(img.size) <= max_edge:
            return b64  # already small — leave untouched (preserve original)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        scale = max_edge / float(max(w, h))
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=jpeg_quality, optimize=True)
        return base64.b64encode(out.getvalue()).decode("utf-8")
    except Exception:
        return b64


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
    Verbatim text the user is replying to.

    If the match sent multiple consecutive messages at the tail (double/triple text),
    all of them are joined so the generator sees the full context of what she said,
    not just her last bubble.
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

    # Collect all consecutive "them" messages at the tail of the transcript.
    tail_them: list[str] = []
    for bubble in reversed(visual_transcript):
        sender = _sender(bubble)
        if sender == "them":
            text = _actual(bubble)
            if text:
                tail_them.append(text)
        elif sender == "user":
            break  # hit a user bubble — stop collecting

    if tail_them:
        # Reverse so messages appear in chronological order when joined.
        return " | ".join(reversed(tail_them))

    # Fallback: return any non-empty message text from the tail.
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
        google_api_key=settings.gemini_api_key,
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


def sanitize_llm_messages_for_logging(
    messages: list[Any], collapse_system: bool = True
) -> list[dict[str, Any]]:
    """
    Convert LangChain message objects into JSON-serializable logs.

    Important: we intentionally omit/replace base64 image URLs because they are
    extremely large and not useful for debugging text behavior.

    collapse_system (default True): the SystemMessage is a large STATIC prompt
    that is identical across calls — re-logging it every request bloats the logs
    and truncates downstream analysis. We replace its content with a sha8 + length
    so the prompt version is still identifiable, while the dynamic HumanMessage
    (the actual per-request payload) is kept in full.
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
        if collapse_system and role == "SystemMessage" and isinstance(content, str):
            digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
            sanitized.append(
                {
                    "role": role,
                    "system_prompt_sha8": digest,
                    "system_prompt_chars": len(content),
                }
            )
            continue
        sanitized.append(
            {
                "role": role,
                "content": _sanitize_content(content),
            }
        )
    return sanitized
