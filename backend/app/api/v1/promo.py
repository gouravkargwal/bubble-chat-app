"""Promo code endpoints — trial/promotional tier access."""

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import ApplyPromoRequest, ApplyPromoResponse
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Promo, PromoRedemption, User

router = APIRouter()
logger = structlog.get_logger()


@router.post("/promo/apply", response_model=ApplyPromoResponse)
async def apply_promo(
    body: ApplyPromoRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplyPromoResponse:
    """Apply a promo code to get trial access to a tier."""
    code = body.code.strip().upper()

    # Find promo with row-level lock to prevent race conditions
    result = await db.execute(
        select(Promo)
        .where(Promo.code == code, Promo.is_active == True)
        .with_for_update()
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Invalid or expired promo code.")

    # Check expiry
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if promo.expires_at and promo.expires_at < now:
        raise HTTPException(status_code=410, detail="This promo code has expired.")

    # Check max uses (safe under FOR UPDATE lock)
    if promo.current_uses >= promo.max_uses:
        raise HTTPException(status_code=410, detail="This promo code has reached its limit.")

    # Check new_users_only
    if promo.new_users_only:
        from sqlalchemy import func
        from app.infrastructure.database.models import Interaction

        total_result = await db.execute(
            select(func.count(Interaction.id)).where(Interaction.user_id == user.id)
        )
        total_interactions = total_result.scalar_one()
        if total_interactions > 0:
            raise HTTPException(status_code=403, detail="This promo is for new users only.")

    # Check if already redeemed
    existing = await db.execute(
        select(PromoRedemption).where(
            PromoRedemption.user_id == user.id,
            PromoRedemption.promo_id == promo.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You've already used this promo code.")

    # Apply promo
    expires_at = now + timedelta(days=promo.duration_days)

    user.tier = promo.tier_grant
    user.tier_expires_at = expires_at
    user.tier_source = "promo"

    promo.current_uses += 1

    redemption = PromoRedemption(
        promo_id=promo.id,
        user_id=user.id,
    )
    db.add(redemption)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="You've already used this promo code.")

    logger.info(
        "promo_applied",
        user_id=user.id,
        code=code,
        tier=promo.tier_grant,
        duration_days=promo.duration_days,
    )

    return ApplyPromoResponse(
        tier_granted=promo.tier_grant,
        duration_days=promo.duration_days,
        expires_at=int(expires_at.timestamp()),
    )
