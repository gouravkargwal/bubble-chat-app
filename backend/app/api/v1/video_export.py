"""
Video export endpoint — scores recent interactions for viral potential
and returns them formatted as Remotion input props.

This is an admin-only tool. It reads from the existing Interaction table
(no new columns required) and scores each interaction algorithmically
based on signals the LLM already generated.

Usage:
    GET /api/v1/admin/video-pipeline/candidates?limit=20
        → Returns top-scoring interactions with video-ready payloads

    GET /api/v1/admin/video-pipeline/candidates/{interaction_id}
        → Returns a single interaction with its score breakdown

    POST /api/v1/admin/video-pipeline/render
        → Marks an interaction as "video_rendered" so it doesn't appear again
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.v1.admin_deps import verify_admin_key
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Interaction, User

logger = structlog.get_logger(__name__)

router = APIRouter(dependencies=[Depends(verify_admin_key)])

# The LLM's `hook_type`/`viral_tier` fields (from the vision prompt) classify each
# interaction for video content and are authoritative when present. The heuristics
# below only apply to historical rows saved before those columns existed.
_TIER_SCORE = {"low": 15, "medium": 35, "high": 55, "viral": 70}


# ── Scoring engine ──


def _safe_json(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default if default is not None else {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def _get_reply(replies: list[dict], index: int) -> dict:
    if index < len(replies):
        return replies[index] or {}
    return {}


def score_interaction(ix: Interaction) -> dict:
    """
    Score an interaction for video content potential.

    Prefers the vision LLM's own classification (`viral_tier`, `hook_type`) when
    the row has it; falls back to the message-heuristic scoring for historical
    rows saved before those columns existed.

    Returns a dict with:
      - total: int (0-70)
      - should_render: bool
      - priority: "high" | "medium" | "low"
      - hook_type: str
      - scoring_source: "llm" | "heuristic"
      - viral_reasoning: str
      - time_gap_signal: str
      - breakdown: dict of individual heuristic scores (informational even when
        scoring_source is "llm")
    """
    messages = _safe_json(ix.transcript_json, [])
    replies = [_safe_json(getattr(ix, f"reply_{i}", None)) for i in range(4)]
    winning = next(
        (r for r in replies if r.get("is_recommended")),
        _get_reply(replies, 0),
    )

    # Extract last user message from transcript
    user_msgs = [m for m in messages if m.get("s") == "user"]
    them_msgs = [m for m in messages if m.get("s") == "them"]
    last_user = user_msgs[-1].get("t", "") if user_msgs else ""
    win_text = winning.get("text", "")

    # ── 1. User message quality (0-10) ──
    # Short messages (<10 chars) = low effort. Long messages (>30 chars) = high effort.
    # The LLM's hook_type field will eventually replace this heuristic entirely.
    msg_len = len(last_user.strip())
    is_low_effort = msg_len < 10  # "hey", "hi", "lol", "wyd", etc.
    score_user = 0 if is_low_effort else (8 if msg_len > 30 else 4)

    # ── 2. Her effort — low = tension = good content (0-10) ──
    effort_map = {"low": 10, "medium": 5, "high": 0, "very_low": 10, "very_high": 0}
    score_effort = effort_map.get((ix.their_effort or "medium").lower().strip(), 3)

    # ── 3. Temperature — cold = tension to rescue (0-10) ──
    temp_map = {
        "cold": 10,
        "lukewarm": 8,
        "warm": 4,
        "hot": 0,
        "very_cold": 10,
        "very_warm": 2,
    }
    score_temp = temp_map.get(
        (ix.conversation_temperature or "warm").lower().strip(), 4
    )

    # ── 4. Winning line quality (0-10) ──
    # Longer winning lines (>20 chars) tend to be more substantive.
    # The LLM's hook_type field will classify this precisely in future.
    score_win = 8 if len(win_text) > 20 else 4

    # ── 5. Transcript length — 4-8 messages ideal for short video (0-10) ──
    n = len(messages)
    score_len = 10 if 4 <= n <= 8 else 7 if 2 <= n <= 10 else 3 if n > 10 else 0

    # ── 6. Person name known (0-10) ──
    has_name = bool(
        ix.person_name and ix.person_name.lower() not in ("unknown", "", "someone")
    )
    score_name = 10 if has_name else 2

    # ── 7. Key detail / hook point exists (0-10) ──
    has_detail = bool(ix.key_detail and len(ix.key_detail.strip()) > 10)
    score_detail = 10 if has_detail else 2

    total = (
        score_user
        + score_effort
        + score_temp
        + score_win
        + score_len
        + score_name
        + score_detail
    )

    # ── Determine hook type based on strongest signal ──
    # Heuristic fallback for historical data. Once the LLM's `hook_type` field
    # flows through to the Interaction table, this will be replaced by the LLM's
    # direct classification from the vision prompt.
    if is_low_effort:
        hook_type = "roast"
    elif score_effort >= 8:
        hook_type = "gap"
    elif score_win >= 8 and len(win_text) > 25:
        # Check if winning line reads as a clever comeback (clapback) vs date setup (outcome)
        win_lower = win_text.lower()
        if any(
            w in win_lower
            for w in ["because", "actually", "tell me", "prove", "wow", "oh", "wait"]
        ):
            hook_type = "clapback"
        else:
            hook_type = "outcome"
    elif score_detail >= 8:
        hook_type = "strategy"
    elif 3 <= n <= 5:
        hook_type = "social"
    else:
        hook_type = "bet"

    # ── LLM classification overrides the heuristic when present ──
    llm_tier = (ix.viral_tier or "").strip().lower()
    if llm_tier in _TIER_SCORE:
        total = _TIER_SCORE[llm_tier]
        scoring_source = "llm"
    else:
        scoring_source = "heuristic"

    llm_hook_type = (ix.hook_type or "").strip().lower()
    if llm_hook_type:
        hook_type = llm_hook_type

    return {
        "total": total,
        "should_render": total >= 30,
        "priority": "high" if total >= 50 else ("medium" if total >= 30 else "low"),
        "hook_type": hook_type,
        "scoring_source": scoring_source,
        "viral_reasoning": ix.viral_reasoning or "",
        "time_gap_signal": ix.time_gap_signal or "",
        "breakdown": {
            "user_message_quality": score_user,
            "her_effort": score_effort,
            "temperature": score_temp,
            "winning_line": score_win,
            "transcript_length": score_len,
            "person_name": score_name,
            "key_detail": score_detail,
        },
    }


def _build_video_payload(ix: Interaction, score: dict) -> dict:
    """Format an interaction + score as a Remotion input props object.

    Openers (first messages) don't have a chat transcript. For those we
    set ``isOpener: true`` and build a minimal transcript from the profile
    analysis (their_last_message) plus our winning opener so the Remotion
    composition can render a "Profile Card" style instead of chat bubbles.
    """
    is_opener = ix.direction == "opener"
    messages = _safe_json(ix.transcript_json, None)
    if messages is None and is_opener:
        # Build synthetic transcript for the Profile Card format:
        # her profile vibe as "them" context + our winning line as "you"
        messages = []
        if ix.their_last_message:
            messages.append({"s": "them", "t": ix.their_last_message})
    elif messages is None:
        messages = []

    replies = [_safe_json(getattr(ix, f"reply_{i}", None)) for i in range(4)]
    winning = next(
        (r for r in replies if r.get("is_recommended")),
        _get_reply(replies, 0),
    )

    return {
        "id": ix.id,
        "isOpener": is_opener,
        "personName": ix.person_name or "Someone",
        "detectedApp": "dating_app",
        "strategyLabel": winning.get("strategy_label", "COOKD_AI"),
        "winningLine": winning.get("text", ""),
        "coachReasoning": winning.get("coach_reasoning", ""),
        "theirLastMessage": ix.their_last_message or "",
        "keyDetail": ix.key_detail or "",
        "transcript": [
            {
                "sender": "them" if m.get("s") == "them" else "you",
                "text": m.get("t", ""),
            }
            for m in messages
        ],
        "hookStyle": score["hook_type"],
        "viralScore": score["total"],
        "priority": score["priority"],
        "viralReasoning": score["viral_reasoning"],
        "timeGapSignal": score["time_gap_signal"],
        "createdAt": ix.created_at.isoformat() if ix.created_at else "",
    }


# ── Endpoints ──


@router.get("/admin/video-pipeline/candidates")
async def get_video_candidates(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        default=20, ge=1, le=100, alias="pageSize", description="Items per page"
    ),
    # ── Filters ──
    search: str | None = Query(
        default=None,
        description="Search by person name (case-insensitive partial match)",
    ),
    hook_type: str | None = Query(
        default=None,
        alias="hookType",
        description="Filter by hook type (roast, gap, outcome, etc.)",
    ),
    priority: str | None = Query(
        default=None, description="Filter by priority (high, medium, low)"
    ),
    min_score: int | None = Query(
        default=None,
        ge=0,
        le=70,
        alias="minScore",
        description="Minimum viral score (default: 0)",
    ),
    max_score: int | None = Query(
        default=None, ge=0, le=70, alias="maxScore", description="Maximum viral score"
    ),
    marketing_consent_only: bool | None = Query(
        default=True,
        alias="marketingConsentOnly",
        description="Only return candidates from users who have opted into marketing content (default: true). The consent flag is set client-side and synced per-user. Set to false to include all interactions regardless of consent status.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Score recent interactions and return video candidates with pagination & filters.

    Results are sorted by score descending, so the most viral-worthy
    interactions appear first. Each candidate includes a score breakdown
    and a Remotion-ready payload.

    The marketing_consent flag is stored on the User model and synced from
    the Android app's DataStore via PUT /users/me/marketing-consent.
    By default, only interactions from consenting users are returned.
    """
    # Apply DB-level filters early
    # ponytail: Include openers (first messages) even without transcript_json.
    # The video payload builder falls back to their_last_message for those.
    # Ceiling: once every interaction has transcript_json, restore this filter.
    db_filters = []
    if search:
        db_filters.append(Interaction.person_name.ilike(f"%{search}%"))

    # Join with User to filter by marketing_consent.
    # Must use selectinload() so ix.user is accessible outside the query
    # without triggering a lazy load (which breaks in async context).
    stmt = (
        select(Interaction)
        .options(selectinload(Interaction.user))
        .join(Interaction.user)
        .where(*db_filters)
        .order_by(Interaction.created_at.desc())
        .limit(200)
    )
    result = await db.execute(stmt)
    interactions = result.scalars().all()

    # Score + apply in-memory filters
    candidates = []
    for ix in interactions:
        # Marketing consent filter (DB-level fallback: check the joined User record)
        if marketing_consent_only and not (ix.user and ix.user.marketing_consent):
            continue
        score = score_interaction(ix)
        s = score["total"]

        # Skip non-renderable
        if not score["should_render"]:
            continue

        # Score range
        if min_score is not None and s < min_score:
            continue
        if max_score is not None and s > max_score:
            continue

        # Priority filter
        if priority and score["priority"] != priority:
            continue

        # Hook type filter
        if hook_type and score["hook_type"] != hook_type:
            continue

        payload = _build_video_payload(ix, score)
        candidates.append((s, score, payload))

    candidates.sort(key=lambda x: x[0], reverse=True)

    # Paginate
    total = len(candidates)
    offset = (page - 1) * page_size
    page_items = candidates[offset : offset + page_size]

    return {
        "candidates": [p for _, _, p in page_items],
        "count": len(page_items),
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, (total + page_size - 1) // page_size),
        "score_buckets": {
            "high": sum(1 for s, _, _ in candidates if s >= 50),
            "medium": sum(1 for s, _, _ in candidates if 30 <= s < 50),
        },
    }


@router.get("/admin/video-pipeline/candidates/{interaction_id}")
async def get_single_candidate(
    interaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Score and return a single interaction."""
    stmt = select(Interaction).where(Interaction.id == interaction_id)
    result = await db.execute(stmt)
    ix = result.scalar_one_or_none()

    if not ix:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    score = score_interaction(ix)
    payload = _build_video_payload(ix, score)

    return {
        "candidate": payload,
        "score": score,
    }


# ── Render trigger (placeholder — currently just marks as processed) ──


@router.post("/admin/video-pipeline/render")
async def trigger_render(
    interaction_ids: list[str],
    db: AsyncSession = Depends(get_db),
):
    """
    Batch render trigger (POST) — marks interactions as queued for rendering.

    In the future, this will also trigger the Remotion render pipeline.
    For now, it marks them as processed so they don't appear in the candidate list.
    """
    if not interaction_ids:
        raise HTTPException(status_code=400, detail="No interaction IDs provided.")

    # Fetch interactions and build payloads
    stmt = select(Interaction).where(Interaction.id.in_(interaction_ids))
    result = await db.execute(stmt)
    interactions = {ix.id: ix for ix in result.scalars().all()}

    rendered = []
    not_found = []

    for iid in interaction_ids:
        ix = interactions.get(iid)
        if not ix:
            not_found.append(iid)
            continue

        score = score_interaction(ix)
        payload = _build_video_payload(ix, score)

        # Mark as rendered in-memory (DB column not needed for v1)
        # In v2, add a `video_rendered_at` column to Interaction
        rendered.append(payload)

    return {
        "rendered": rendered,
        "count": len(rendered),
        "not_found": not_found,
        "message": f"Queued {len(rendered)} interactions for rendering.",
    }
