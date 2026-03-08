"""Usage tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from app.api.v1.schemas.schemas import UsageResponse
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get the user's daily usage stats."""
    daily_used = await count_today_interactions(user.id, db)
    return UsageResponse(
        daily_limit=user.daily_limit,
        daily_used=daily_used,
        is_premium=user.is_premium,
        premium_expires_at=int(user.premium_expires_at.timestamp()) if user.premium_expires_at else None,
    )
