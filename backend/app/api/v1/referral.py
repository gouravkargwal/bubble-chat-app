"""Referral system endpoints."""

import secrets
import string

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    ApplyReferralRequest,
    ApplyReferralResponse,
    ReferralInfoResponse,
)
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Referral, User

router = APIRouter()
logger = structlog.get_logger()

MAX_REFERRALS = 10
BONUS_PER_REFERRAL = 5


def generate_referral_code(length: int = 8) -> str:
    """Generate a random alphanumeric referral code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("/referral/me", response_model=ReferralInfoResponse)
async def get_my_referral(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReferralInfoResponse:
    """Get the current user's referral code and stats."""
    # Generate code if user doesn't have one yet
    if not user.referral_code:
        for _ in range(10):  # retry on collision
            code = generate_referral_code()
            existing = await db.execute(select(User).where(User.referral_code == code))
            if existing.scalar_one_or_none() is None:
                user.referral_code = code
                try:
                    await db.commit()
                    await db.refresh(user)
                except IntegrityError:
                    await db.rollback()
                    continue
                break

    # Count total referrals
    result = await db.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == user.id)
    )
    total_referrals = result.scalar_one()

    return ReferralInfoResponse(
        referral_code=user.referral_code or "",
        total_referrals=total_referrals,
        bonus_replies_earned=user.bonus_replies,
        max_referrals=MAX_REFERRALS,
    )


@router.post("/referral/apply", response_model=ApplyReferralResponse)
async def apply_referral(
    body: ApplyReferralRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplyReferralResponse:
    """Apply a referral code. Both referrer and referee get a 24-hour premium tier (God Mode)."""
    code = body.code.upper().strip()

    # 1. Can't use own code
    if user.referral_code and user.referral_code == code:
        raise HTTPException(
            status_code=400, detail="You cannot use your own referral code."
        )

    # 2. Already been referred
    if user.referred_by:
        raise HTTPException(
            status_code=400, detail="You have already used a referral code."
        )

    # 3. Find referrer with row-level lock to prevent race conditions
    result = await db.execute(
        select(User).where(User.referral_code == code).with_for_update()
    )
    referrer = result.scalar_one_or_none()
    if referrer is None:
        raise HTTPException(status_code=404, detail="Invalid referral code.")

    # 4. Check referrer cap (safe under FOR UPDATE lock)
    referral_count = await db.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == referrer.id)
    )
    if referral_count.scalar_one() >= MAX_REFERRALS:
        raise HTTPException(
            status_code=400, detail="This referral code has reached its maximum uses."
        )

    # 5. Anti-fraud guardrail: Check if device_id has been used before (silent fail)
    should_grant_reward = True
    if body.device_id:
        existing_device_user = await db.execute(
            select(User).where(User.android_device_id == body.device_id)
        )
        if existing_device_user.scalar_one_or_none() is not None:
            # Device ID already exists - silently fail (don't grant reward to referrer)
            should_grant_reward = False
            logger.warning(
                "referral_fraud_detected",
                device_id=body.device_id,
                user_id=user.id,
                referrer_id=referrer.id,
                code=code,
            )
        else:
            # Store device_id for future checks
            user.android_device_id = body.device_id

    # 6. Grant 24 hours of premium ("God Mode") to both - stack time if already active
    from datetime import datetime, timedelta, timezone

    user.referred_by = referrer.id
    now = datetime.now(timezone.utc)

    # Stack time for referee (user applying the code)
    if user.god_mode_expires_at and user.god_mode_expires_at > now:
        user.god_mode_expires_at = user.god_mode_expires_at + timedelta(hours=24)
    else:
        user.god_mode_expires_at = now + timedelta(hours=24)

    # Stack time for referrer (user who owns the code) - only if not fraud
    if should_grant_reward:
        if referrer.god_mode_expires_at and referrer.god_mode_expires_at > now:
            referrer.god_mode_expires_at = referrer.god_mode_expires_at + timedelta(
                hours=24
            )
        else:
            referrer.god_mode_expires_at = now + timedelta(hours=24)

        referral = Referral(
            referrer_id=referrer.id,
            referee_id=user.id,
            bonus_granted=BONUS_PER_REFERRAL,
        )
        db.add(referral)
    else:
        # Still create referral record but without granting reward to referrer
        referral = Referral(
            referrer_id=referrer.id,
            referee_id=user.id,
            bonus_granted=0,  # No bonus granted due to fraud detection
        )
        db.add(referral)

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail="You have already used a referral code."
        )

    logger.info(
        "referral_applied",
        referee_id=user.id,
        referrer_id=referrer.id,
        referee_god_mode_expires_at=(
            int(user.god_mode_expires_at.timestamp())
            if user.god_mode_expires_at
            else None
        ),
        referrer_god_mode_expires_at=(
            int(referrer.god_mode_expires_at.timestamp())
            if referrer.god_mode_expires_at
            else None
        ),
        duration_hours=24,
        fraud_detected=not should_grant_reward,
        device_id=body.device_id,
    )

    return ApplyReferralResponse(
        tier_granted="premium",
        duration_hours=24,
        expires_at=(
            int(user.god_mode_expires_at.timestamp())
            if user.god_mode_expires_at
            else None
        ),
    )
