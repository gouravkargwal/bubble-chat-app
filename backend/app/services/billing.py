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
) -> None:
    """Apply a subscription upgrade/renewal with a full quota reset.

    This implements the "Clean Slate" behavior:
    - Update User tier & plan window.
    - Reset all UserQuota counters to 0.
    - Realign all quota reset timestamps to start from `now`.

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

    # 3. Clean-slate quota reset (if we can key by google_provider_id)
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
            # Reset all counters to 0
            quota.daily_usage_count = 0
            quota.weekly_usage_count = 0
            quota.weekly_audits_count = 0
            quota.weekly_blueprints_count = 0

            # Realign reset timers from now
            quota.daily_reset_at = now + timedelta(days=1)
            quota.weekly_reset_at = now + timedelta(weeks=1)
            quota.weekly_audits_reset_at = now + timedelta(weeks=1)
            quota.weekly_blueprints_reset_at = now + timedelta(weeks=1)

    # 4. Commit changes
    await db.commit()

    logger.info(
        "apply_plan_upgrade_success",
        user_id=user_id,
        new_tier=new_tier,
        billing_period=billing_period,
        tier_expires_at=(
            user.tier_expires_at.isoformat() if user.tier_expires_at else None
        ),
    )
