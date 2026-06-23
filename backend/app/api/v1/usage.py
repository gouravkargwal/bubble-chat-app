"""Usage tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import UsageResponse
from app.core.tier_config import TIER_CONFIG, BILLING_CREDITS
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
    """Get the user's current credits and usage stats."""
    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])

    credits_remaining = 0
    if user.google_provider_id:
        qm = QuotaManager(db)
        credits_remaining = await qm.get_credits_remaining(
            user.google_provider_id, effective_tier
        )

    # Period limit — free tier uses daily credits, paid tiers use period pool.
    credits_period_limit = BILLING_CREDITS.get(effective_tier, 0)
    if effective_tier == "free":
        credits_period_limit = tier_config["limits"].get("daily_credits", 2)

    # Billing period from active purchase.
    billing_period = "daily"
    if effective_tier != "free":
        purchase_result = await db.execute(
            select(Purchase)
            .where(Purchase.user_id == user.id, Purchase.status == "active")
            .order_by(Purchase.created_at.desc())
            .limit(1)
        )
        purchase = purchase_result.scalar_one_or_none()
        if purchase and purchase.product_id:
            pid = purchase.product_id.lower()
            if "crush" in pid or "weekly" in pid:
                billing_period = "weekly"
            elif "match" in pid or "rizz" in pid or "monthly" in pid:
                billing_period = "monthly"

    return UsageResponse(
        credits_remaining=credits_remaining,
        credits_period_limit=credits_period_limit,
        billing_period=billing_period,
        tier=effective_tier,
        is_premium=effective_tier != "free",
        tier_expires_at=(
            int(user.tier_expires_at.timestamp()) if user.tier_expires_at else None
        ),
        allowed_directions=tier_config["features"]["allowed_ui_directions"],
        max_screenshots=tier_config["limits"]["max_screenshots_per_request"],
        custom_hints=tier_config["features"]["custom_hints_enabled"],
        limits=tier_config["limits"],
        features=tier_config["features"],
    )
