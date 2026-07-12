"""Lead magnet service — rate limiting, image validation, lead CRUD, caching."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx
import structlog
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import LeadMagnetLead

logger = structlog.get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB
MAX_IMAGE_DIMENSION = 2048  # px on any side

# ── Data classes ───────────────────────────────────────────────────────────


class ActiveWindow:
    """Returned when an IP has an active rate limit window."""

    def __init__(
        self, *, is_blocked: bool, retry_after_seconds: float, status: str
    ) -> None:
        self.is_blocked = is_blocked
        self.retry_after_seconds = retry_after_seconds
        self.status = status


# ── Public helpers ─────────────────────────────────────────────────────────


def compute_rate_limit_reset(status: str) -> datetime:
    """Compute the rate_limit_reset_at timestamp based on lead status."""
    now = datetime.now(timezone.utc)
    if status == "failed":
        return now + timedelta(minutes=15)
    # success, pending, rate_limited — reset at next midnight UTC
    return datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )


def validate_and_hash_image(image_base64: str) -> tuple[str, str]:
    """Validate image and compute SHA-256 hash.

    Returns (validated_base64, sha256_hash).
    Raises HTTPException(422) on failure.
    """
    if not image_base64:
        raise HTTPException(422, "Image is required")

    try:
        image_bytes = base64.b64decode(image_base64)
    except Exception:
        raise HTTPException(422, "Invalid base64 encoding")

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            422,
            f"Image too large. Max 3 MB. Chat screenshots are typically under 2 MB.",
        )

    # Compute hash before dimension checks (hash of original)
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    # Validate dimensions via Pillow
    try:
        from io import BytesIO
        from PIL import Image as PilImage

        img = PilImage.open(BytesIO(image_bytes))
        if max(img.size) > MAX_IMAGE_DIMENSION:
            raise HTTPException(
                422,
                f"Image dimensions too large. Max {MAX_IMAGE_DIMENSION}px on any side.",
            )
    except ImportError:
        pass  # Pillow not installed — skip dimension check
    except Exception:
        pass  # Not a valid image — let Gemini handle it

    return image_base64, image_hash


# ── Rate limit queries ─────────────────────────────────────────────────────


async def get_active_rate_limit_window(
    ip_address: str,
    db: AsyncSession,
) -> ActiveWindow | None:
    """Check if *ip_address* has an active rate-limit window.

    Returns ``None`` if the caller may proceed.
    Returns an ``ActiveWindow`` describing the block otherwise.
    """
    now = datetime.now(timezone.utc)

    # 1. Check success / failed rows with active reset timestamp
    stmt = (
        select(LeadMagnetLead)
        .where(
            LeadMagnetLead.ip_address == ip_address,
            LeadMagnetLead.rate_limit_reset_at > now,
            LeadMagnetLead.status.in_(["success", "failed"]),
        )
        .order_by(LeadMagnetLead.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()
    if lead is not None:
        retry_after = (lead.rate_limit_reset_at - now).total_seconds()
        return ActiveWindow(
            is_blocked=True,
            retry_after_seconds=max(0.0, retry_after),
            status=lead.status,
        )

    # 2. Check for a *recent* pending row (< 30 min) — prevents double-fire
    stmt_pending = (
        select(LeadMagnetLead)
        .where(
            LeadMagnetLead.ip_address == ip_address,
            LeadMagnetLead.status == "pending",
            LeadMagnetLead.created_at > now - timedelta(minutes=30),
        )
        .limit(1)
    )
    result_pending = await db.execute(stmt_pending)
    if result_pending.scalar_one_or_none() is not None:
        return ActiveWindow(
            is_blocked=True, retry_after_seconds=300.0, status="pending"
        )

    return None  # Allowed


async def get_cached_replies(
    ip_address: str,
    image_hash: str,
    db: AsyncSession,
) -> list[dict[str, Any]] | None:
    """Return cached replies when the *same IP + same image* was previously successful."""
    stmt = (
        select(LeadMagnetLead)
        .where(
            LeadMagnetLead.ip_address == ip_address,
            LeadMagnetLead.image_hash == image_hash,
            LeadMagnetLead.status == "success",
            LeadMagnetLead.rate_limit_reset_at > datetime.now(timezone.utc),
        )
        .order_by(LeadMagnetLead.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()
    if lead is not None and lead.replies_json:
        try:
            return json.loads(lead.replies_json)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


# ── Lead CRUD ──────────────────────────────────────────────────────────────


async def insert_lead(
    db: AsyncSession,
    *,
    ip_address: str,
    email: str,
    direction: str,
    custom_hint: str | None,
    image_hash: str,
    status: str,
    rate_limit_reset_at: datetime,
) -> LeadMagnetLead:
    """Create a new lead row and flush (but do not commit)."""
    lead = LeadMagnetLead(
        ip_address=ip_address,
        direction=direction,
        custom_hint=custom_hint,
        image_hash=image_hash,
        email=email,
        status=status,
        rate_limit_reset_at=rate_limit_reset_at,
    )
    db.add(lead)
    await db.flush()
    return lead


async def update_lead_success(
    db: AsyncSession,
    lead_id: str,
    replies: list[dict[str, Any]],
) -> None:
    """Mark a lead as successful and store the JSON-serialised replies."""
    stmt = select(LeadMagnetLead).where(LeadMagnetLead.id == lead_id)
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()
    if lead is None:
        logger.warning("lead_not_found_for_update", lead_id=lead_id)
        return
    lead.status = "success"
    lead.replies_json = json.dumps(replies, ensure_ascii=False)
    lead.updated_at = datetime.now(timezone.utc)


async def update_lead_failed(
    db: AsyncSession,
    lead_id: str,
    error_message: str,
) -> None:
    """Mark a lead as failed."""
    stmt = select(LeadMagnetLead).where(LeadMagnetLead.id == lead_id)
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()
    if lead is None:
        logger.warning("lead_not_found_for_update", lead_id=lead_id)
        return
    lead.status = "failed"
    lead.error_message = error_message[:500]
    lead.updated_at = datetime.now(timezone.utc)


# ── Webhook (optional, best-effort) ────────────────────────────────────────


async def fire_lead_webhook(lead: LeadMagnetLead) -> None:
    """Fire-and-forget POST to the configured webhook URL.

    The webhook carries minimal lead info for CRM integration.
    """
    url = settings.lead_magnet_webhook_url
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                json={
                    "email": lead.email,
                    "direction": lead.direction,
                    "status": lead.status,
                    "ip_address": lead.ip_address,
                    "timestamp": lead.created_at.isoformat(),
                },
            )
    except Exception:
        logger.info("lead_webhook_failed", lead_id=lead.id, exc_info=True)
