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
from app.infrastructure.database.models import User

TRIAL_DURATION_DAYS = 3
TRIAL_TIER = "pro"

logger = logging.getLogger(__name__)

router = APIRouter()


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
      5. Return our own JWT for subsequent API calls.
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
            # --- 3. Brand-new user with Pro trial ----------------------------
            is_new_user = True
            device_id = body.device_id or f"firebase:{firebase_uid}"
            trial_expires = datetime.now(timezone.utc) + timedelta(days=TRIAL_DURATION_DAYS)
            user = User(
                device_id=device_id,
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                daily_limit=settings.daily_free_limit,
                referral_code=generate_referral_code(),
                tier=TRIAL_TIER,
                tier_expires_at=trial_expires,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Created new Firebase user %s with %d-day %s trial", user.id, TRIAL_DURATION_DAYS, TRIAL_TIER)

    token, expires_at = create_token(user.id, user.device_id)

    return AuthResponse(
        token=token,
        user_id=user.id,
        expires_at=int(expires_at.timestamp()),
        email=user.email,
        display_name=user.display_name,
        is_new_user=is_new_user,
        trial_tier=TRIAL_TIER if is_new_user else None,
    )
