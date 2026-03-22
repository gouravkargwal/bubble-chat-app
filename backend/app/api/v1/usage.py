"""Usage tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from datetime import datetime, timedelta, timezone
from app.api.v1.schemas.schemas import UsageResponse
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Purchase, User
from app.services.quota_manager import QuotaManager

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get the user's daily usage stats."""
    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])

    daily_limit = tier_config["limits"]["chat_generations_per_day"]
    effective_limit = daily_limit + user.bonus_replies

    # 1. Read ALL usage from quota table when we have a stable Google ID.
    if user.google_provider_id:
        qm = QuotaManager(db)
        (
            daily_used,
            weekly_used,
            weekly_audits_used,
            weekly_blueprints_used,
        ) = await qm.get_usage(user.google_provider_id)
    else:
        daily_used = 0
        weekly_used = 0
        weekly_audits_used = 0
        weekly_blueprints_used = 0

    # With quota-backed tracking, we no longer derive usage stats from history tables.
    monthly_used = 0
    total_generated = 0
    total_copied = 0

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
        weekly_blueprints_used=weekly_blueprints_used,
        is_premium=effective_tier != "free",
        tier=effective_tier,
        allowed_directions=tier_config["features"]["allowed_ui_directions"],
        max_screenshots=tier_config["limits"]["max_screenshots_per_request"],
        custom_hints=tier_config["features"]["custom_hints_enabled"],
        tier_expires_at=(
            int(user.tier_expires_at.timestamp()) if user.tier_expires_at else None
        ),
        god_mode_expires_at=(
            int(user.god_mode_expires_at.timestamp())
            if user.god_mode_expires_at
            else None
        ),
        bonus_replies=user.bonus_replies,
        total_replies_generated=total_generated,
        total_replies_copied=total_copied,
        limits=tier_config["limits"],
        features=tier_config["features"],
        billing_period=billing_period,
    )
