"""FastAPI dependency injection."""

from datetime import date

from fastapi import Depends, Header, HTTPException
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.auth.jwt import decode_token, get_user_by_id
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Interaction, User


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract user from Bearer token.

    Works for both anonymous and Firebase-authenticated users — both flows
    issue the same HS256 JWT containing ``sub`` (user_id).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await get_user_by_id(user_id, db)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def count_today_interactions(user_id: str, db: AsyncSession) -> int:
    """Count how many interactions the user has made today."""
    today_start = date.today().isoformat()
    result = await db.execute(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user_id,
            func.date(Interaction.created_at) == today_start,
        )
    )
    return result.scalar_one()
