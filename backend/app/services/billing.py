"""Billing and subscription-related services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    """Apply a subscription change (INITIAL / RENEWAL / PRODUCT_CHANGE) and adjust quotas.

    Tier-transition behavior:
    - Plan change (new tier != old tier):
        • Reset all usage counts to 0 so the user starts fresh on the new tier.
        • Realign daily/weekly reset timestamps so the new window starts from `now`.
    - Same-tier renewal:
        • Keep existing usage counts (no history wipe).
        • Realign daily/weekly reset timestamps so the new window starts from `now`.

    WARNING: This function calls ``await db.commit()``. Any SQLAlchemy objects
    attached to the same ``AsyncSession`` (for example, a ``User`` instance in
    the caller) will be expired after this commit and must not be accessed
    without an explicit refresh.
    """
    # 1. Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.error("apply_plan_upgrade_user_not_found", user_id=user_id)
        return

    now = datetime.now(timezone.utc)

    # Capture previous tier before we change it so we can classify the transition.
    old_tier = user.tier or "free"

    # 2. Update user tier and plan window
    user.tier = new_tier
    user.tier_source = "purchase"
    user.plan_period_start = now

    # Tier expiry based on billing period
    expires_at: datetime | None
    if billing_period == "weekly":
        expires_at = now + timedelta(days=7)
    elif billing_period == "monthly":
        expires_at = now + timedelta(days=30)
    elif billing_period == "yearly":
        expires_at = now + timedelta(days=365)
    else:
        # Unknown/one-off period – leave expiry unset and log for visibility.
        expires_at = None
        logger.warning(
            "apply_plan_upgrade_unknown_billing_period",
            user_id=user_id,
            billing_period=billing_period,
        )

    user.tier_expires_at = expires_at

    # 3. Tier-transition-aware quota adjustment (if we can key by google_provider_id)
    if user.google_provider_id:
        quota_stmt = (
            select(UserQuota)
            .where(UserQuota.google_provider_id == user.google_provider_id)
            .with_for_update()
        )
        quota_result = await db.execute(quota_stmt)
        quota = quota_result.scalar_one_or_none()

        if quota is None:
            # If no quota row exists yet, create one in a fully-reset state.
            quota = UserQuota(
                google_provider_id=user.google_provider_id,
                daily_usage_count=0,
                weekly_usage_count=0,
                weekly_audits_count=0,
                weekly_blueprints_count=0,
                daily_reset_at=now + timedelta(days=1),
                weekly_reset_at=now + timedelta(weeks=1),
                weekly_audits_reset_at=now + timedelta(weeks=1),
                weekly_blueprints_reset_at=now + timedelta(weeks=1),
            )
            db.add(quota)
        else:
            # Realign reset timers from now so the new window starts immediately.
            quota.daily_reset_at = now + timedelta(days=1)
            quota.weekly_reset_at = now + timedelta(weeks=1)
            quota.weekly_audits_reset_at = now + timedelta(weeks=1)
            quota.weekly_blueprints_reset_at = now + timedelta(weeks=1)

            if new_tier != old_tier:
                # Plan changed: reset all usage counts so the user starts fresh
                # on the new tier without carrying over old-tier usage.
                quota.daily_usage_count = 0
                quota.weekly_usage_count = 0
                quota.weekly_audits_count = 0
                quota.weekly_blueprints_count = 0
            # Same-tier renewal: keep usage history; reset windows already updated above.

    # 4. Commit changes
    await db.commit()

    log_payload: dict = {
        "user_id": user_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "billing_period": billing_period,
        "tier_expires_at": (
            user.tier_expires_at.isoformat() if user.tier_expires_at else None
        ),
    }
    if webhook_event_type:
        log_payload["webhook_event_type"] = webhook_event_type
    logger.info("apply_plan_upgrade_success", **log_payload)
