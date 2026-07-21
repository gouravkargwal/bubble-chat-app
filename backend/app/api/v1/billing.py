"""Billing endpoints — subscription status (RevenueCat only, LTD removed)."""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import BillingStatusResponse
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Purchase, User

router = APIRouter()
logger = structlog.get_logger()


# ── RevenueCat-powered billing status (subscriptions only) ──


@router.get("/billing/status", response_model=BillingStatusResponse)
async def billing_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    """Get the user's current subscription status from RevenueCat/Google Play."""
    effective_tier = get_effective_tier(user)

    result = await db.execute(
        select(Purchase)
        .where(Purchase.user_id == user.id, Purchase.status == "active")
        .order_by(Purchase.created_at.desc())
        .limit(1)
    )
    purchase = result.scalar_one_or_none()

    return BillingStatusResponse(
        is_premium=effective_tier != "free",
        tier=effective_tier,
        product_id=purchase.product_id if purchase else None,
        expires_at=(
            int(purchase.expires_at.timestamp())
            if purchase and purchase.expires_at
            else None
        ),
        auto_renewing=purchase.auto_renewing if purchase else False,
    )
