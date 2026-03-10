"""Usage tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from app.api.v1.schemas.schemas import UsageResponse
from app.domain.tiers import get_effective_tier, get_tier_config
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Interaction, User

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

    # Count total interactions created by this user
    total_generated_result = await db.execute(
        select(func.count(Interaction.id)).where(Interaction.user_id == user.id)
    )
    total_generated = total_generated_result.scalar() or 0

    # Count total interactions where user copied a reply (copied_index is not null)
    total_copied_result = await db.execute(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user.id, Interaction.copied_index.isnot(None)
        )
    )
    total_copied = total_copied_result.scalar() or 0

    return UsageResponse(
        daily_limit=effective_limit if tier_config.daily_limit > 0 else 0,
        daily_used=daily_used,
        is_premium=effective_tier != "free",
        tier=effective_tier,
        allowed_directions=tier_config.allowed_directions,
        max_screenshots=tier_config.max_screenshots,
        custom_hints=tier_config.custom_hints,
        tier_expires_at=(
            int(user.tier_expires_at.timestamp()) if user.tier_expires_at else None
        ),
        bonus_replies=user.bonus_replies,
        total_replies_generated=total_generated,
        total_replies_copied=total_copied,
    )
