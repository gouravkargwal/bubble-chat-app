"""Authentication endpoints — Firebase Google Sign-In."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.referral import generate_referral_code
from app.api.v1.schemas.schemas import AuthResponse, FirebaseAuthRequest
from app.config import settings
from app.infrastructure.auth.jwt import create_token
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Promo, PromoRedemption, User

logger = logging.getLogger(__name__)

router = APIRouter()


async def _apply_signup_promo(user: User, db: AsyncSession) -> str | None:
    """Auto-apply the signup promo code to a new user. Returns tier granted or None."""
    if not settings.signup_promo_code:
        return None

    result = await db.execute(
        select(Promo).where(
            Promo.code == settings.signup_promo_code,
            Promo.is_active == True,
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        logger.warning("Signup promo code '%s' not found or inactive", settings.signup_promo_code)
        return None

    # Check max uses (0 = unlimited)
    if promo.max_uses > 0 and promo.current_uses >= promo.max_uses:
        logger.warning("Signup promo code '%s' has reached max uses", settings.signup_promo_code)
        return None

    # Apply tier from promo
    now = datetime.utcnow()
    user.tier = promo.tier_grant
    user.tier_expires_at = now + timedelta(days=promo.duration_days)
    user.tier_source = "promo"

    promo.current_uses += 1

    db.add(PromoRedemption(promo_id=promo.id, user_id=user.id))

    logger.info(
        "Applied signup promo '%s' to user %s: %s for %d days",
        promo.code, user.id, promo.tier_grant, promo.duration_days,
    )
    return promo.tier_grant


@router.post("/auth/firebase", response_model=AuthResponse)
async def firebase_auth(
    body: FirebaseAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with a Firebase ID token.

    Flow:
      1. Verify the Firebase token via Admin SDK.
      2. Look up an existing user by ``firebase_uid``.
      3. If not found but ``device_id`` was provided, try to migrate the
         anonymous user (link their data to the Firebase account).
      4. Otherwise create a brand-new user.
      5. Auto-apply signup promo if configured.
      6. Return our own JWT for subsequent API calls.
    """
    from app.infrastructure.auth.firebase import verify_firebase_token

    try:
        decoded = verify_firebase_token(body.firebase_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    firebase_uid: str = decoded["uid"]
    email: str | None = decoded.get("email")
    display_name: str | None = decoded.get("name")

    is_new_user = False
    trial_tier: str | None = None

    # --- 1. Existing Firebase user? -----------------------------------------
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_uid)
    )
    user = result.scalar_one_or_none()

    if user is not None:
        # Update profile fields in case they changed on the Firebase side
        user.email = email
        user.display_name = display_name
        await db.commit()
        await db.refresh(user)
    else:
        # --- 2. Try migrating an anonymous user by device_id ----------------
        if body.device_id:
            result = await db.execute(
                select(User).where(User.device_id == body.device_id)
            )
            user = result.scalar_one_or_none()

        if user is not None:
            # Link the anonymous account to Firebase
            user.firebase_uid = firebase_uid
            user.email = email
            user.display_name = display_name
            await db.commit()
            await db.refresh(user)
            logger.info(
                "Migrated anonymous user %s to Firebase uid %s",
                user.id,
                firebase_uid,
            )
        else:
            # --- 3. Brand-new user ------------------------------------------
            is_new_user = True
            device_id = body.device_id or f"firebase:{firebase_uid}"
            user = User(
                device_id=device_id,
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                referral_code=generate_referral_code(),
            )
            db.add(user)
            await db.flush()  # get user.id before applying promo

            # --- 4. Auto-apply signup promo ---------------------------------
            trial_tier = await _apply_signup_promo(user, db)

            await db.commit()
            await db.refresh(user)
            logger.info("Created new Firebase user %s (trial_tier=%s)", user.id, trial_tier)

    token, expires_at = create_token(user.id, user.device_id)

    return AuthResponse(
        token=token,
        user_id=user.id,
        expires_at=int(expires_at.timestamp()),
        email=user.email,
        display_name=user.display_name,
        is_new_user=is_new_user,
        trial_tier=trial_tier,
    )
