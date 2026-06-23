"""Billing and subscription-related services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tier_config import BILLING_CREDITS, BILLING_PERIOD_DAYS
from app.infrastructure.database.models import User, UserQuota

logger = structlog.get_logger()


async def apply_plan_upgrade(
    db: AsyncSession,
    user_id: str,
    new_tier: str,
    billing_period: str,
    *,
    webhook_event_type: str | None = None,
) -> None:
    """Apply a subscription change and grant the correct credit pool."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        logger.error("apply_plan_upgrade_user_not_found", user_id=user_id)
        return

    now = datetime.now(timezone.utc)
    old_tier = user.tier or "free"

    # Update user tier.
    user.tier = new_tier
    user.tier_source = "purchase"
    user.plan_period_start = now

    # Set tier expiry — derive from tier, not fragile billing_period string.
    period_days = BILLING_PERIOD_DAYS.get(new_tier, 30)
    user.tier_expires_at = now + timedelta(days=period_days)

    # Grant credits for this billing period.
    credits = BILLING_CREDITS.get(new_tier, 0)

    if user.google_provider_id:
        quota_stmt = (
            select(UserQuota)
            .where(UserQuota.google_provider_id == user.google_provider_id)
            .with_for_update()
        )
        quota_result = await db.execute(quota_stmt)
        quota = quota_result.scalar_one_or_none()

        if quota is None:
            quota = UserQuota(
                google_provider_id=user.google_provider_id,
                credits_remaining=credits,
                credits_period_limit=credits,
                credits_reset_at=now + timedelta(days=period_days),
                signup_bonus_granted=True,
            )
            db.add(quota)
        else:
            if new_tier == old_tier:
                # Same plan renewal: stack new credits on top of remaining.
                quota.credits_remaining += credits
            else:
                # Plan change: clean start with new tier's credit pool.
                quota.credits_remaining = credits
            quota.credits_period_limit = credits
            quota.credits_reset_at = now + timedelta(days=period_days)

    await db.commit()

    log_payload: dict = {
        "user_id": user_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "billing_period": billing_period,
        "credits_granted": credits,
        "tier_expires_at": (
            user.tier_expires_at.isoformat() if user.tier_expires_at else None
        ),
    }
    if webhook_event_type:
        log_payload["webhook_event_type"] = webhook_event_type
    logger.info("apply_plan_upgrade_success", **log_payload)
