"""Usage tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from datetime import datetime, timedelta, timezone
from app.api.v1.schemas.schemas import UsageResponse
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, Interaction, Purchase, User

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get the user's daily usage stats."""
    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])

    daily_used = await count_today_interactions(user.id, db)
    daily_limit = tier_config["limits"]["chat_generations_per_day"]
    effective_limit = daily_limit + user.bonus_replies

    # Calculate weekly and monthly usage for period-based plans
    now = datetime.now(timezone.utc)
    # Week starts on Monday (weekday() returns 0 for Monday)
    week_start = (now - timedelta(days=now.weekday())).replace(tzinfo=None)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    weekly_used_result = await db.execute(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user.id, Interaction.created_at >= week_start
        )
    )
    weekly_used = weekly_used_result.scalar() or 0

    monthly_used_result = await db.execute(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user.id, Interaction.created_at >= month_start
        )
    )
    monthly_used = monthly_used_result.scalar() or 0

    # Count weekly profile audits (distinct audit sessions this week)
    # We count unique dates when audits were created this week
    weekly_audits_result = await db.execute(
        select(func.count(func.distinct(cast(AuditedPhoto.created_at, Date)))).where(
            AuditedPhoto.user_id == user.id, AuditedPhoto.created_at >= week_start
        )
    )
    weekly_audits_used = weekly_audits_result.scalar() or 0

    # Count total interactions created by this user
    total_generated_result = await db.execute(
        select(func.count(Interaction.id)).where(Interaction.user_id == user.id)
    )
    total_generated = total_generated_result.scalar() or 0

    # Count total interactions where user copied a reply (copied_index is not null)
    total_copied_result = await db.execute(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user.id, Interaction.copied_index.isnot(None)
        )
    )
    total_copied = total_copied_result.scalar() or 0

    # Get billing period from active purchase product_id
    billing_period = "daily"  # default
    if effective_tier != "free":
        purchase_result = await db.execute(
            select(Purchase)
            .where(Purchase.user_id == user.id, Purchase.status == "active")
            .order_by(Purchase.created_at.desc())
            .limit(1)
        )
        purchase = purchase_result.scalar_one_or_none()
        if purchase and purchase.product_id:
            product_id = purchase.product_id.lower()
            if "weekly" in product_id:
                billing_period = "weekly"
            elif "monthly" in product_id:
                billing_period = "monthly"

    return UsageResponse(
        daily_limit=effective_limit if daily_limit > 0 else 0,
        daily_used=daily_used,
        weekly_used=weekly_used,
        monthly_used=monthly_used,
        weekly_audits_used=weekly_audits_used,
        is_premium=effective_tier != "free",
        tier=effective_tier,
        allowed_directions=tier_config["features"]["allowed_ui_directions"],
        max_screenshots=tier_config["limits"]["max_screenshots_per_request"],
        custom_hints=tier_config["features"]["custom_hints_enabled"],
        tier_expires_at=(
            int(user.tier_expires_at.timestamp()) if user.tier_expires_at else None
        ),
        god_mode_expires_at=(
            int(user.god_mode_expires_at.timestamp()) if user.god_mode_expires_at else None
        ),
        bonus_replies=user.bonus_replies,
        total_replies_generated=total_generated,
        total_replies_copied=total_copied,
        limits=tier_config["limits"],
        features=tier_config["features"],
        billing_period=billing_period,
    )
