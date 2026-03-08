"""Device-based anonymous JWT authentication."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import User


def create_token(user_id: str, device_id: str) -> tuple[str, datetime]:
    """Create a JWT token for a device."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "sub": user_id,
        "device_id": device_id,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expires_at


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


async def get_or_create_user(device_id: str, db: AsyncSession) -> User:
    """Find existing user by device_id or create a new one."""
    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(device_id=device_id, daily_limit=settings.daily_free_limit)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_user_by_id(user_id: str, db: AsyncSession) -> User | None:
    """Look up a user by their ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
