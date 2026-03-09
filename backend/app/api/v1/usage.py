"""Usage tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from app.api.v1.schemas.schemas import UsageResponse
from app.domain.tiers import get_effective_tier, get_tier_config
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get the user's daily usage stats."""
    effective_tier = get_effective_tier(user)
    tier_config = get_tier_config(effective_tier)

    daily_used = await count_today_interactions(user.id, db)
    effective_limit = tier_config.daily_limit + user.bonus_replies

    return UsageResponse(
        daily_limit=effective_limit if tier_config.daily_limit > 0 else 0,
        daily_used=daily_used,
        is_premium=effective_tier != "free",
        tier=effective_tier,
        allowed_directions=tier_config.allowed_directions,
        max_screenshots=tier_config.max_screenshots,
        premium_expires_at=int(user.premium_expires_at.timestamp()) if user.premium_expires_at else None,
        bonus_replies=user.bonus_replies,
    )
