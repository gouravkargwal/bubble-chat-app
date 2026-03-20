"""
In-memory pending resolution store for the "Hybrid Stitch" flow.

When `POST /api/v1/vision/generate` detects ambiguity, it halts and returns
`REQUIRES_USER_CONFIRMATION`. The follow-up `POST /api/v1/conversations/resolve`
needs enough context (direction, screenshots, etc.) to re-run generation.

This store is intentionally lightweight and TTL-based. In production with
multiple workers, you'd likely move this to a shared datastore (Redis/DB).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class PendingHybridResolution:
    user_id: str
    suggested_conversation_id: str
    images: list[str]
    direction: str  # stored as `ConversationDirection.value`
    custom_hint: str | None
    extracted_person_name: str
    created_at_monotonic: float
    # Optional detailed conflict metadata for logging/display.
    conflict_reason: str | None = None
    conflict_detail: str | None = None


# Keyed by (user_id, suggested_conversation_id)
_PENDING: dict[tuple[str, str], PendingHybridResolution] = {}

# Default TTL: 10 minutes
_TTL_SECONDS = 10 * 60


def store_pending_hybrid_resolution(
    *,
    user_id: str,
    suggested_conversation_id: str,
    images: list[str],
    direction: str,
    custom_hint: str | None,
    extracted_person_name: str,
    conflict_reason: str | None = None,
    conflict_detail: str | None = None,
) -> None:
    """Store latest ambiguity context for this (user, conversation)."""
    key = (user_id, suggested_conversation_id)
    _PENDING[key] = PendingHybridResolution(
        user_id=user_id,
        suggested_conversation_id=suggested_conversation_id,
        images=images,
        direction=direction,
        custom_hint=custom_hint,
        extracted_person_name=extracted_person_name,
        created_at_monotonic=time.monotonic(),
        conflict_reason=conflict_reason,
        conflict_detail=conflict_detail,
    )

def peek_pending_hybrid_resolution(
    *, user_id: str, suggested_conversation_id: str
) -> PendingHybridResolution | None:
    """Return pending context without removing it (TTL-aware)."""
    key = (user_id, suggested_conversation_id)
    pending = _PENDING.get(key)
    if not pending:
        return None
    if time.monotonic() - pending.created_at_monotonic > _TTL_SECONDS:
        _PENDING.pop(key, None)  # evict expired entry to prevent unbounded growth
        return None
    return pending


def has_pending_hybrid_resolution(
    *, user_id: str, suggested_conversation_id: str
) -> bool:
    """True iff a non-expired pending resolution exists."""
    return (
        peek_pending_hybrid_resolution(
            user_id=user_id, suggested_conversation_id=suggested_conversation_id
        )
        is not None
    )


def pop_pending_hybrid_resolution(
    *, user_id: str, suggested_conversation_id: str
) -> PendingHybridResolution | None:
    """Return and remove pending context, if it hasn't expired."""
    key = (user_id, suggested_conversation_id)
    pending = _PENDING.get(key)
    if not pending:
        return None
    if time.monotonic() - pending.created_at_monotonic > _TTL_SECONDS:
        _PENDING.pop(key, None)
        return None
    return _PENDING.pop(key, None)

