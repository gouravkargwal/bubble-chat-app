"""Authentication endpoints — Firebase Google Sign-In."""

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.referral import generate_referral_code
from app.api.v1.schemas.schemas import AuthResponse, FirebaseAuthRequest
from app.config import settings
from app.infrastructure.auth.jwt import create_token
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User, UserQuota

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/auth/firebase", response_model=AuthResponse)
async def firebase_auth(
    body: FirebaseAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with a Firebase ID token.

    Flow:
      1. Verify the Firebase token via Admin SDK.
      2. If a stable ``google_provider_id`` is provided, look up user by that
         first (this is the canonical cross-device identifier).
      3. If not found, fall back to existing ``firebase_uid`` lookup.
      4. If still not found but ``device_id`` was provided, try to migrate the
         anonymous user (link their data to the Firebase account).
      5. Otherwise create a brand-new user.
      6. Ensure a UserQuota row exists for this google_provider_id so the rest
         of the app can assume quotas are initialized.
      7. Return our own JWT for subsequent API calls.
    """
    from app.infrastructure.auth.firebase import verify_firebase_token

    try:
        decoded = verify_firebase_token(body.firebase_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    firebase_uid: str = decoded["uid"]
    email: str | None = decoded.get("email")
    display_name: str | None = decoded.get("name")
    google_provider_id: str | None = body.google_provider_id

    is_new_user = False

    user: User | None = None

    # --- 1. Prefer lookup by stable google_provider_id -----------------------
    if google_provider_id:
        result = await db.execute(
            select(User).where(User.google_provider_id == google_provider_id)
        )
        user = result.scalar_one_or_none()

    # --- 2. Fallback to existing Firebase user by uid -----------------------
    if user is None:
        result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
        user = result.scalar_one_or_none()

    if user is not None:
        # Existing account — update profile fields and keep device linkage.
        user.email = email
        user.display_name = display_name
        if google_provider_id:
            user.google_provider_id = google_provider_id
        user.firebase_uid = firebase_uid
        await db.commit()
        await db.refresh(user)
    else:
        # --- 3. Try migrating an anonymous user by device_id ----------------
        if body.device_id:
            result = await db.execute(
                select(User).where(User.device_id == body.device_id)
            )
            user = result.scalar_one_or_none()

        if user is not None:
            # Link the anonymous account to Firebase + stable Google ID
            user.firebase_uid = firebase_uid
            user.email = email
            user.display_name = display_name
            if google_provider_id:
                user.google_provider_id = google_provider_id
            await db.commit()
            await db.refresh(user)
        else:
            # --- 4. Brand-new user ------------------------------------------
            is_new_user = True
            device_id = body.device_id or f"firebase:{firebase_uid}"
            user = User(
                device_id=device_id,
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                referral_code=generate_referral_code(),
                google_provider_id=google_provider_id,
            )
            db.add(user)
            await db.flush()  # get user.id

            await db.commit()
            await db.refresh(user)

    # --- 5. Ensure UserQuota row exists for this google_provider_id ----------
    if google_provider_id:
        quota_result = await db.execute(
            select(UserQuota).where(UserQuota.google_provider_id == google_provider_id)
        )
        quota = quota_result.scalar_one_or_none()
        if quota is None:
            db.add(UserQuota(google_provider_id=google_provider_id))
            await db.commit()

    token, expires_at = create_token(user.id, user.device_id)

    return AuthResponse(
        token=token,
        user_id=user.id,
        expires_at=int(expires_at.timestamp()),
        email=user.email,
        display_name=user.display_name,
        is_new_user=is_new_user,
    )
