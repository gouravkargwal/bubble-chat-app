"""Billing endpoints — Google Play subscription verification."""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    BillingStatusResponse,
    VerifyPurchaseRequest,
    VerifyPurchaseResponse,
)
from app.domain.tiers import PRODUCT_TIER_MAP, get_effective_tier
from app.infrastructure.billing.google_play import get_play_client
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Purchase, User

router = APIRouter()
logger = structlog.get_logger()

# Maps Google Play product IDs to premium tier
PREMIUM_PRODUCTS = {
    "cookd_premium_weekly",
    "cookd_premium_monthly",
    "cookd_pro_weekly",
    "cookd_pro_monthly",
}


@router.post("/billing/verify", response_model=VerifyPurchaseResponse)
async def verify_purchase(
    body: VerifyPurchaseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerifyPurchaseResponse:
    """Verify a Google Play purchase and activate premium."""
    if body.product_id not in PREMIUM_PRODUCTS:
        raise HTTPException(status_code=400, detail="Unknown product ID.")

    # Check if already verified
    existing = await db.execute(
        select(Purchase).where(Purchase.purchase_token == body.purchase_token)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Purchase already verified.")

    # Verify with Google Play
    client = get_play_client()
    try:
        result = await client.verify_subscription(body.product_id, body.purchase_token)
    except ValueError as e:
        logger.error("play_verify_config_error", error=str(e))
        raise HTTPException(status_code=503, detail="Billing service not configured.")

    if result is None:
        return VerifyPurchaseResponse(is_valid=False)

    # Parse subscription state
    sub_state = result.get("subscriptionState", "")
    # SUBSCRIPTION_STATE_ACTIVE or SUBSCRIPTION_STATE_IN_GRACE_PERIOD
    is_active = sub_state in (
        "SUBSCRIPTION_STATE_ACTIVE",
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
    )

    if not is_active:
        return VerifyPurchaseResponse(is_valid=False)

    # Parse expiry from lineItems
    expires_at = None
    line_items = result.get("lineItems", [])
    if line_items:
        expiry_str = line_items[0].get("expiryTime")
        if expiry_str:
            expires_at = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))

    auto_renewing = line_items[0].get("autoRenewingPlan", {}).get(
        "autoRenewEnabled", False
    ) if line_items else False

    # Save purchase record
    purchase = Purchase(
        user_id=user.id,
        product_id=body.product_id,
        purchase_token=body.purchase_token,
        order_id=body.order_id,
        status="active",
        expires_at=expires_at,
        auto_renewing=auto_renewing,
    )
    db.add(purchase)

    # Activate premium + set tier
    tier = PRODUCT_TIER_MAP.get(body.product_id, "premium")
    user.is_premium = True
    user.tier = tier
    user.premium_expires_at = expires_at
    user.tier_expires_at = expires_at
    await db.commit()

    # Acknowledge the purchase — retry once on failure
    for attempt in range(2):
        try:
            await client.acknowledge_subscription(body.product_id, body.purchase_token)
            break
        except Exception as e:
            logger.warning(
                "play_acknowledge_failed",
                user_id=user.id,
                attempt=attempt + 1,
                error=str(e),
            )
            if attempt == 0:
                import asyncio
                await asyncio.sleep(1)

    logger.info(
        "premium_activated",
        user_id=user.id,
        product_id=body.product_id,
        expires_at=str(expires_at),
    )

    return VerifyPurchaseResponse(
        is_valid=True,
        premium_until=int(expires_at.timestamp()) if expires_at else None,
    )


@router.get("/billing/status", response_model=BillingStatusResponse)
async def billing_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    """Get the user's current subscription status."""
    # Check for expired premium
    if user.is_premium and user.premium_expires_at:
        if user.premium_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            user.is_premium = False
            user.premium_expires_at = None
            await db.commit()

    # Find active purchase
    result = await db.execute(
        select(Purchase)
        .where(Purchase.user_id == user.id, Purchase.status == "active")
        .order_by(Purchase.created_at.desc())
        .limit(1)
    )
    purchase = result.scalar_one_or_none()

    return BillingStatusResponse(
        is_premium=user.is_premium,
        tier=get_effective_tier(user),
        product_id=purchase.product_id if purchase else None,
        expires_at=int(purchase.expires_at.timestamp()) if purchase and purchase.expires_at else None,
        auto_renewing=purchase.auto_renewing if purchase else False,
    )
