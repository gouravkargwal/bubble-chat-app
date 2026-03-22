"""
Shared utilities for vision generation endpoints (v1 and v2).

Hybrid Stitch uses an industry-standard composite scoring approach:
  1. Alias lookup (instant match from confirmed identities)
  2. Composite score = weighted(name_similarity, embedding_similarity, time_recency)
  3. Three-outcome model: auto_stitch / new_match / requires_user_confirmation
  4. Feedback loop: confirmed matches are persisted as aliases for future lookups
"""

from __future__ import annotations

import difflib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.schemas import ReplyOptionPayload, VisionResponse
from app.config import settings
from app.core.embeddings import embed_text
from app.domain.conversation import find_or_create_conversation
from app.domain.models import ParsedLlmResponse
from app.domain.voice_dna import is_echo_text, update_voice_dna_stats
from app.infrastructure.database.models import (
    Conversation,
    Interaction,
    PersonAlias,
    User,
    UserVoiceDNA,
)
from app.services.quota_manager import QuotaManager
from app.services.voice_dna import generate_semantic_profile_background

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Hybrid stitch constants
# ---------------------------------------------------------------------------

# Composite score thresholds (0-1 scale)
_AUTO_STITCH_THRESHOLD = 0.75       # High confidence → auto-link
_CONFIRMATION_THRESHOLD = 0.40      # Medium confidence → ask user
# Below _CONFIRMATION_THRESHOLD → new_match

# Composite score weights (must sum to 1.0)
_W_NAME = 0.30
_W_CONTENT = 0.50
_W_RECENCY = 0.20

# Time recency: interactions within this window get full recency score
_RECENCY_HALF_LIFE_HOURS = 48.0  # score halves every 48 hours

# Name similarity floor for a candidate to be considered at all
_NAME_FLOOR = 0.40

# Max candidates to evaluate (performance guard)
_MAX_CANDIDATE_CONVOS = 30

_NON_WORD_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Text / name utilities
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    name = (name or "").strip().lower()
    name = _NON_WORD_RE.sub("", name)
    return _WS_RE.sub(" ", name).strip()


def name_similarity(a: str, b: str) -> float:
    a_n, b_n = normalize_name(a), normalize_name(b)
    if not a_n or not b_n:
        return 0.0
    if a_n == b_n:
        return 1.0
    # Guard: single-char names get penalized to avoid spurious matches
    if len(a_n) <= 1 or len(b_n) <= 1:
        return 0.0

    seq_ratio = difflib.SequenceMatcher(None, a_n, b_n).ratio()

    def trigrams(s: str) -> set[str]:
        return {s[i: i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else set()

    ta, tb = trigrams(a_n), trigrams(b_n)
    jacc = (len(ta & tb) / len(ta | tb)) if ta and tb else 0.0
    return max(seq_ratio, jacc)


def normalize_text_for_overlap(text: str) -> str:
    text = (text or "").strip().lower()
    text = _NON_WORD_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()


def text_overlap(a: str, b: str) -> bool:
    """Character-level overlap check (kept for backward compat and quick pre-filter)."""
    a_n, b_n = normalize_text_for_overlap(a), normalize_text_for_overlap(b)
    if not a_n or not b_n:
        return False
    if a_n == b_n:
        return True
    # Substring check: both sides must be at least 6 chars to avoid "hello" matching everything
    if len(a_n) >= 6 and len(b_n) >= 6 and (a_n in b_n or b_n in a_n):
        return True
    return difflib.SequenceMatcher(None, a_n, b_n).ratio() >= 0.86


def format_relative_time(dt: datetime | None) -> str:
    if not dt:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes == 1:
        return "1 minute ago"
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours == 1:
        return "1 hour ago"
    if hours < 48:
        return f"{hours} hours ago"
    days = hours // 24
    if days == 1:
        return "1 day ago"
    return f"{days} days ago"


# ---------------------------------------------------------------------------
# Composite scoring helpers
# ---------------------------------------------------------------------------

def _recency_score(last_interaction_at: datetime | None) -> float:
    """Exponential decay: 1.0 for just now, 0.5 at half-life, approaches 0."""
    if not last_interaction_at:
        return 0.0
    if last_interaction_at.tzinfo is None:
        last_interaction_at = last_interaction_at.replace(tzinfo=timezone.utc)
    hours_ago = max(0, (datetime.now(timezone.utc) - last_interaction_at).total_seconds() / 3600)
    return math.exp(-0.693 * hours_ago / _RECENCY_HALF_LIFE_HOURS)  # ln(2) ≈ 0.693


async def _embedding_content_score(
    extracted_texts: list[str],
    conversation_id: str,
    user_id: str,
    db: AsyncSession,
) -> float:
    """
    Compute content similarity using embeddings (semantic) + character overlap (lexical).
    Returns a score in [0, 1].
    """
    if not extracted_texts:
        return 0.0

    # --- Lexical overlap (fast, no API call) ---
    recent_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == user_id,
            Interaction.conversation_id == conversation_id,
        )
        .order_by(Interaction.created_at.desc())
        .limit(8)
    )
    recent_interactions = recent_result.scalars().all()

    if not recent_interactions:
        return 0.0

    stored_texts: list[str] = []
    for it in recent_interactions:
        if it.their_last_message:
            stored_texts.append(it.their_last_message)
        if it.user_organic_text:
            stored_texts.append(it.user_organic_text)
        if it.copied_index is not None:
            reply_val = getattr(it, f"reply_{it.copied_index}", None)
            if isinstance(reply_val, str) and reply_val.strip():
                try:
                    loaded = json.loads(reply_val)
                    if isinstance(loaded, dict) and "text" in loaded:
                        stored_texts.append(str(loaded["text"]))
                    else:
                        stored_texts.append(reply_val)
                except (json.JSONDecodeError, TypeError):
                    stored_texts.append(reply_val)

    # Quick lexical check: if any OCR text overlaps stored text, high confidence
    has_lexical_overlap = any(
        text_overlap(ext, stored)
        for ext in extracted_texts
        for stored in stored_texts
    )
    if has_lexical_overlap:
        return 1.0  # Direct text match = strongest possible content signal

    # --- Semantic similarity via embeddings (if available) ---
    # Combine extracted texts into a single query string for embedding
    combined_text = " ".join(extracted_texts[-3:])  # last 3 bubbles
    if len(combined_text.strip()) < 10:
        return 0.0

    try:
        query_embedding = await embed_text(combined_text)
        if not query_embedding:
            return 0.0

        # Use pgvector cosine distance against this conversation's interactions
        vector_sql = text(
            """
            SELECT MIN(i.embedding <=> :query_embedding) AS best_distance
            FROM interactions AS i
            WHERE i.user_id = :user_id
              AND i.conversation_id = :conversation_id
              AND i.embedding IS NOT NULL
            """
        )
        # asyncpg requires pgvector params as a string "[x, y, ...]", not a Python list
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
        result = await db.execute(
            vector_sql,
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "query_embedding": embedding_str,
            },
        )
        row = result.mappings().first()
        if not row or row["best_distance"] is None:
            return 0.0

        # Convert cosine distance (0=identical, 2=opposite) to similarity score (0-1)
        cosine_distance = float(row["best_distance"])
        similarity = max(0.0, 1.0 - cosine_distance)
        return similarity

    except Exception as e:
        logger.warning("stitch_embedding_score_failed", error=str(e))
        return 0.0


# ---------------------------------------------------------------------------
# Alias management
# ---------------------------------------------------------------------------

async def lookup_alias(
    *, db: AsyncSession, user_id: str, ocr_name: str
) -> str | None:
    """Check if this OCR name has been previously confirmed as an alias for a conversation."""
    normalized = normalize_name(ocr_name)
    if not normalized or normalized == "unknown":
        return None
    result = await db.execute(
        select(PersonAlias.conversation_id).where(
            PersonAlias.user_id == user_id,
            PersonAlias.alias_name == normalized,
        )
    )
    row = result.scalar_one_or_none()
    return row


async def save_alias(
    *,
    db: AsyncSession,
    user_id: str,
    alias_name: str,
    conversation_id: str,
    source: str = "auto_stitch",
) -> None:
    """Persist an alias mapping. Upserts: if alias exists, update the conversation_id."""
    normalized = normalize_name(alias_name)
    if not normalized or normalized == "unknown":
        return
    result = await db.execute(
        select(PersonAlias).where(
            PersonAlias.user_id == user_id,
            PersonAlias.alias_name == normalized,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.conversation_id = conversation_id
        existing.source = source
    else:
        db.add(PersonAlias(
            user_id=user_id,
            alias_name=normalized,
            conversation_id=conversation_id,
            source=source,
        ))
    await db.commit()


# ---------------------------------------------------------------------------
# Main stitch resolution — composite scoring engine
# ---------------------------------------------------------------------------

async def resolve_hybrid_stitch_conversation_id(
    *,
    user_id: str,
    ocr_person_name: str,
    extracted_texts: list[str],
    db: AsyncSession,
) -> tuple[str, str | None, dict | None]:
    """
    Industry-grade conversation stitching with composite scoring.

    Returns (outcome, conversation_id, payload).
    outcome: "new_match" | "auto_stitch" | "requires_user_confirmation"

    Resolution priority:
      1. Alias lookup — instant, deterministic (from prior confirmations)
      2. Composite scoring — weighted(name + content/embeddings + recency)
      3. Three-outcome thresholds on composite score
    """
    # ---------------------------------------------------------------
    # Step 1: Alias lookup (instant match from prior confirmations)
    # ---------------------------------------------------------------
    alias_convo_id = await lookup_alias(db=db, user_id=user_id, ocr_name=ocr_person_name)
    if alias_convo_id:
        # Verify the conversation still exists
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == alias_convo_id,
                Conversation.user_id == user_id,
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo:
            logger.info(
                "stitch_alias_hit",
                user_id=user_id,
                alias_name=normalize_name(ocr_person_name),
                conversation_id=alias_convo_id,
            )
            # Reactivate if needed
            if not convo.is_active:
                convo.is_active = True
                await db.commit()
            return "auto_stitch", alias_convo_id, None

    # ---------------------------------------------------------------
    # Step 2: Fetch candidate conversations (bounded, most recent first)
    # ---------------------------------------------------------------
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.last_interaction_at.desc().nullslast())
        .limit(_MAX_CANDIDATE_CONVOS)
    )
    convos = result.scalars().all()
    if not convos:
        return "new_match", None, None

    # ---------------------------------------------------------------
    # Step 3: Score each candidate with composite scoring
    # ---------------------------------------------------------------
    best_convo: Conversation | None = None
    best_composite: float = 0.0
    best_name_score: float = 0.0

    for convo in convos:
        ns = name_similarity(ocr_person_name, convo.person_name)
        if ns < _NAME_FLOOR:
            continue  # Not even close — skip entirely

        # Content score (embedding + lexical) — most expensive, only for name candidates
        cs = await _embedding_content_score(
            extracted_texts, convo.id, user_id, db
        )

        # Recency score
        rs = _recency_score(convo.last_interaction_at)

        composite = (_W_NAME * ns) + (_W_CONTENT * cs) + (_W_RECENCY * rs)

        logger.debug(
            "stitch_candidate_score",
            user_id=user_id,
            conversation_id=convo.id,
            person_name=convo.person_name,
            name_score=round(ns, 3),
            content_score=round(cs, 3),
            recency_score=round(rs, 3),
            composite=round(composite, 3),
        )

        if composite > best_composite:
            best_composite = composite
            best_convo = convo
            best_name_score = ns

    # ---------------------------------------------------------------
    # Step 4: Apply thresholds
    # ---------------------------------------------------------------
    if not best_convo or best_composite < _CONFIRMATION_THRESHOLD:
        return "new_match", None, None

    if best_composite >= _AUTO_STITCH_THRESHOLD:
        # Save the alias for future instant lookups
        await save_alias(
            db=db,
            user_id=user_id,
            alias_name=ocr_person_name,
            conversation_id=best_convo.id,
            source="auto_stitch",
        )
        # Reactivate if needed
        if not best_convo.is_active:
            best_convo.is_active = True
            await db.commit()
        logger.info(
            "stitch_auto_stitch",
            user_id=user_id,
            conversation_id=best_convo.id,
            composite_score=round(best_composite, 3),
        )
        return "auto_stitch", best_convo.id, None

    # ---------------------------------------------------------------
    # Step 5: Ambiguity — build 409 payload for user confirmation
    # ---------------------------------------------------------------
    recent_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == user_id,
            Interaction.conversation_id == best_convo.id,
        )
        .order_by(Interaction.created_at.desc())
        .limit(5)
    )
    recent_interactions = recent_result.scalars().all()

    her_last_message = your_last_reply = ai_memory_note = ""
    for it in recent_interactions:
        if not her_last_message and it.their_last_message:
            her_last_message = it.their_last_message
        if not your_last_reply and it.copied_index is not None:
            reply_val = getattr(it, f"reply_{it.copied_index}", None)
            if isinstance(reply_val, str) and reply_val.strip():
                try:
                    loaded = json.loads(reply_val)
                    your_last_reply = str(loaded["text"]) if isinstance(loaded, dict) and "text" in loaded else reply_val
                except (json.JSONDecodeError, TypeError):
                    your_last_reply = reply_val
        if not ai_memory_note and it.key_detail:
            ai_memory_note = it.key_detail
        if her_last_message and your_last_reply and ai_memory_note:
            break

    last_active_dt = (
        recent_interactions[0].created_at if recent_interactions else best_convo.created_at
    )

    payload = {
        "status": "REQUIRES_USER_CONFIRMATION",
        "suggested_match": {
            "person_name": best_convo.person_name,
            "conversation_id": best_convo.id,
            "last_active": format_relative_time(last_active_dt),
            "context_preview": {
                "her_last_message": her_last_message,
                "your_last_reply": your_last_reply,
                "ai_memory_note": ai_memory_note,
            },
        },
        "match_confidence": round(best_composite, 2),
    }

    logger.info(
        "stitch_requires_confirmation",
        user_id=user_id,
        conversation_id=best_convo.id,
        composite_score=round(best_composite, 3),
        name_score=round(best_name_score, 3),
    )

    return "requires_user_confirmation", best_convo.id, payload


# ---------------------------------------------------------------------------
# Interaction persistence
# ---------------------------------------------------------------------------

def dump_reply_option(opt: Any) -> str:
    if opt is None:
        return ""
    try:
        return json.dumps(
            {
                "text": opt.text,
                "strategy_label": opt.strategy_label,
                "is_recommended": opt.is_recommended,
                "coach_reasoning": opt.coach_reasoning,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.warning("reply_option_serialize_failed", error=str(e))
        # Wrap in JSON so downstream json.loads() doesn't break
        return json.dumps({"text": str(opt.text), "strategy_label": "", "is_recommended": False, "coach_reasoning": ""})


def clamp_str(value: str | None, max_len: int = 255, label: str = "") -> str | None:
    if value and len(value) > max_len:
        logger.warning(f"{label}_truncated", original_length=len(value))
        return value[:max_len]
    return value


async def persist_interaction(
    *,
    db: AsyncSession,
    parsed: ParsedLlmResponse,
    user: User,
    effective_conversation_id: str | None,
    direction: str,
    custom_hint: str | None,
    user_organic_text: str | None,
    llm_model: str,
    llm_temperature: float,
    latency_ms: int,
    screenshot_count: int,
    prompt_variant: str = "default",
) -> tuple[Conversation, Interaction]:
    """
    Resolve or create the conversation, self-heal person_name, and save the Interaction row.
    Returns (convo, interaction).
    """
    if effective_conversation_id:
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == effective_conversation_id,
                Conversation.user_id == user.id,
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        # Self-heal unknown person name
        if (
            convo.person_name
            and convo.person_name.lower() == "unknown"
            and parsed.analysis.person_name
            and parsed.analysis.person_name.lower() != "unknown"
        ):
            convo.person_name = parsed.analysis.person_name
    else:
        convo = await find_or_create_conversation(
            user_id=user.id,
            person_name=parsed.analysis.person_name,
            db=db,
        )

    reply_options = list(parsed.replies[:4]) + [None] * (4 - len(parsed.replies[:4]))

    interaction = Interaction(
        conversation_id=convo.id,
        user_id=user.id,
        direction=direction,
        custom_hint=custom_hint,
        their_last_message=parsed.analysis.their_last_message,
        their_tone=clamp_str(parsed.analysis.their_tone, label="analysis_tone"),
        their_effort=clamp_str(parsed.analysis.their_effort, label="analysis_effort"),
        conversation_temperature=clamp_str(parsed.analysis.conversation_temperature, label="analysis_temperature"),
        detected_stage=clamp_str(parsed.analysis.stage, label="analysis_stage"),
        person_name=parsed.analysis.person_name,
        key_detail=parsed.analysis.key_detail,
        user_organic_text=user_organic_text,
        reply_0=dump_reply_option(reply_options[0]),
        reply_1=dump_reply_option(reply_options[1]),
        reply_2=dump_reply_option(reply_options[2]),
        reply_3=dump_reply_option(reply_options[3]),
        llm_model=llm_model,
        prompt_variant=prompt_variant,
        temperature_used=llm_temperature,
        screenshot_count=screenshot_count,
        latency_ms=latency_ms,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return convo, interaction


# ---------------------------------------------------------------------------
# Voice DNA: echo filter + organic text update
# ---------------------------------------------------------------------------

async def extract_organic_text(
    *,
    db: AsyncSession,
    user: User,
    parsed: ParsedLlmResponse,
    conversation_id: str | None = None,
) -> str | None:
    """
    Find the user's last sent message from the transcript.
    Run the echo filter scoped to the SAME conversation (not cross-conversation).
    Returns the organic text string, or None if it was an echo.
    """
    user_organic_text: str | None = None
    if parsed.visual_transcript:
        for msg in reversed(parsed.visual_transcript):
            if getattr(msg, "side", "").lower() == "right" or getattr(msg, "sender", "").lower() == "user":
                user_organic_text = msg.actual_new_message
                break

    if not user_organic_text or len(user_organic_text) <= 3:
        return None

    clean_text = user_organic_text.lower().strip()

    # Scope echo detection to the same conversation to avoid cross-conversation false positives
    query = select(Interaction).where(Interaction.user_id == user.id)
    if conversation_id:
        query = query.where(Interaction.conversation_id == conversation_id)
    query = query.order_by(Interaction.created_at.desc()).limit(10)

    recent_result = await db.execute(query)
    recent_interactions = recent_result.scalars().all()

    for past_int in recent_interactions:
        past_replies: list[str] = []
        for idx in range(4):
            raw = getattr(past_int, f"reply_{idx}", "") or ""
            if not raw:
                continue
            # Handle both JSON and plain text reply formats
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, dict) and "text" in loaded:
                    past_replies.append(str(loaded["text"]).lower().strip())
                else:
                    past_replies.append(raw.lower().strip())
            except (json.JSONDecodeError, TypeError):
                past_replies.append(raw.lower().strip())
        if is_echo_text(clean_text, past_replies):
            logger.info("voice_dna_echo_detected", user_id=user.id, text=clean_text)
            return None

    logger.info("voice_dna_organic_text_found", user_id=user.id, text=clean_text)
    return user_organic_text


async def update_voice_dna(
    *,
    db: AsyncSession,
    user: User,
    organic_text: str,
    effective_tier: str,
    background_tasks: BackgroundTasks,
) -> None:
    """Update Voice DNA stats and optionally trigger semantic profile refresh."""
    voice_result = await db.execute(
        select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id).with_for_update()
    )
    voice_db = voice_result.scalar_one_or_none()
    if voice_db is None:
        voice_db = UserVoiceDNA(user_id=user.id)
        db.add(voice_db)

    updated_dna = update_voice_dna_stats(voice_db, organic_text.lower().strip())
    await db.commit()

    # Trigger semantic profile background refresh for premium users
    try:
        messages_list = (
            json.loads(updated_dna.recent_organic_messages)
            if getattr(updated_dna, "recent_organic_messages", None)
            else []
        )
    except (json.JSONDecodeError, TypeError):
        messages_list = []

    should_refresh = (
        not getattr(updated_dna, "semantic_profile", None)
        or (updated_dna.sample_count % 25 == 0 and updated_dna.sample_count > 0)
    )
    if (
        effective_tier in ["premium", "pro"]
        and len(messages_list) >= 5
        and should_refresh
    ):
        background_tasks.add_task(
            generate_semantic_profile_background,
            user_id=user.id,
            db=db,
            messages=messages_list,
        )


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def build_vision_response(
    *,
    parsed: ParsedLlmResponse,
    interaction: Interaction,
    convo: Conversation,
    daily_limit: int,
    effective_limit: int,
    daily_used: int,
) -> VisionResponse:
    reply_payloads = [
        ReplyOptionPayload(
            text=r.text,
            strategy_label=r.strategy_label,
            is_recommended=r.is_recommended,
            coach_reasoning=r.coach_reasoning,
        )
        for r in parsed.replies[:4]
    ]

    remaining = max(0, effective_limit - daily_used) if daily_limit > 0 else 9999

    return VisionResponse(
        replies=reply_payloads,
        person_name=(
            parsed.analysis.person_name
            if parsed.analysis.person_name != "unknown"
            else None
        ),
        stage=parsed.analysis.stage,
        interaction_id=interaction.id,
        usage_remaining=remaining,
        conversation_id=convo.id,
    )
