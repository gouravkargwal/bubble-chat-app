"""
DB-backed pending resolution store for the "Hybrid Stitch" flow.

When `POST /api/v1/vision/generate_v2` detects ambiguity, it halts and returns
`REQUIRES_USER_CONFIRMATION`. The follow-up `POST /api/v1/conversations/resolve`
needs enough context (direction, screenshots, etc.) to re-run generation.

This store uses a `pending_resolutions` DB table instead of an in-memory dict,
so it works correctly across multiple Uvicorn workers and survives restarts.
Rows older than TTL_SECONDS are treated as expired and ignored.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import PendingResolution

# Default TTL: 10 minutes
_TTL_SECONDS = 10 * 60


def _is_expired(row: PendingResolution) -> bool:
    if row.created_at is None:
        return True
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=_TTL_SECONDS)
    return created < cutoff


async def store_pending_hybrid_resolution(
    *,
    db: AsyncSession,
    user_id: str,
    suggested_conversation_id: str,
    images: list[str],
    direction: str,
    custom_hint: str | None,
    extracted_person_name: str,
    conflict_reason: str | None = None,
    conflict_detail: str | None = None,
) -> PendingResolution:
    """Store (or overwrite) ambiguity context for this (user, conversation)."""
    # Upsert: expire any existing unresolved row for this key
    result = await db.execute(
        select(PendingResolution).where(
            PendingResolution.user_id == user_id,
            PendingResolution.suggested_conversation_id == suggested_conversation_id,
            PendingResolution.resolved_at.is_(None),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.resolved_at = datetime.now(timezone.utc)
        existing.outcome = "superseded"

    row = PendingResolution(
        user_id=user_id,
        suggested_conversation_id=suggested_conversation_id,
        images=json.dumps(images),
        direction=direction,
        custom_hint=custom_hint,
        extracted_person_name=extracted_person_name,
        conflict_reason=conflict_reason,
        conflict_detail=conflict_detail,
    )
    db.add(row)
    await db.commit()
    # Avoid refresh(): callers do not need server defaults on the instance, and a follow-up
    # SELECT can hit asyncpg "another operation is in progress" if a prior result was not
    # fully closed on this session (e.g. hybrid stitch embedding score path).
    return row


async def peek_pending_hybrid_resolution(
    *,
    db: AsyncSession,
    user_id: str,
    suggested_conversation_id: str,
) -> PendingResolution | None:
    """Return pending context without removing it (TTL-aware)."""
    result = await db.execute(
        select(PendingResolution).where(
            PendingResolution.user_id == user_id,
            PendingResolution.suggested_conversation_id == suggested_conversation_id,
            PendingResolution.resolved_at.is_(None),
        ).order_by(PendingResolution.created_at.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row or _is_expired(row):
        return None
    return row


async def has_pending_hybrid_resolution(
    *,
    db: AsyncSession,
    user_id: str,
    suggested_conversation_id: str,
) -> bool:
    """True iff a non-expired, unresolved pending resolution exists."""
    return (
        await peek_pending_hybrid_resolution(
            db=db,
            user_id=user_id,
            suggested_conversation_id=suggested_conversation_id,
        )
        is not None
    )


async def pop_pending_hybrid_resolution(
    *,
    db: AsyncSession,
    user_id: str,
    suggested_conversation_id: str,
) -> PendingResolution | None:
    """Return and mark as consumed the pending context, if it hasn't expired."""
    result = await db.execute(
        select(PendingResolution).where(
            PendingResolution.user_id == user_id,
            PendingResolution.suggested_conversation_id == suggested_conversation_id,
            PendingResolution.resolved_at.is_(None),
        ).with_for_update().order_by(PendingResolution.created_at.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row or _is_expired(row):
        return None
    # Mark as consumed atomically (SELECT ... FOR UPDATE prevents races)
    row.resolved_at = datetime.now(timezone.utc)
    row.outcome = "consumed"
    await db.commit()
    return row


def parse_pending_images(row: PendingResolution) -> list[str]:
    """Deserialize the images JSON from a PendingResolution row."""
    try:
        return json.loads(row.images)
    except (json.JSONDecodeError, TypeError):
        return []
