"""Interaction history endpoints — replaces client-side Room DB."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    HistoryItemResponse,
    HistoryListResponse,
    UserPreferencesResponse,
    VibeBreakdownItem,
)
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Interaction, User

router = APIRouter()
logger = structlog.get_logger()

VIBE_NAMES = ["Flirty", "Witty", "Smooth", "Bold"]


@router.get("/history", response_model=HistoryListResponse)
async def get_history(
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HistoryListResponse:
    """Return user's recent interaction history."""
    result = await db.execute(
        select(Interaction)
        .where(Interaction.user_id == user.id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    interactions = result.scalars().all()

    items = [
        HistoryItemResponse(
            id=i.id,
            person_name=i.person_name,
            direction=i.direction,
            custom_hint=i.custom_hint,
            replies=[i.reply_0, i.reply_1, i.reply_2, i.reply_3],
            copied_index=i.copied_index,
            created_at=int(i.created_at.timestamp()),
        )
        for i in interactions
    ]
    return HistoryListResponse(items=items)


@router.delete("/history/{interaction_id}")
async def delete_history_item(
    interaction_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a single interaction from history."""
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == interaction_id,
            Interaction.user_id == user.id,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Interaction not found")

    await db.delete(interaction)
    await db.commit()
    return {"deleted": True}


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Compute user's vibe preferences from server-side ratings."""
    # Count total rated interactions
    total_result = await db.execute(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user.id,
            Interaction.rating_index.is_not(None),
        )
    )
    total_ratings = total_result.scalar_one()

    if total_ratings < 20:
        return UserPreferencesResponse(
            total_ratings=total_ratings,
            has_enough_data=False,
            vibe_breakdown=[],
            preferred_length="medium",
        )

    # Count positive ratings grouped by reply index (vibe)
    positive_result = await db.execute(
        select(
            Interaction.rating_index,
            func.count(Interaction.id).label("cnt"),
        )
        .where(
            Interaction.user_id == user.id,
            Interaction.rating_positive == True,
            Interaction.rating_index.is_not(None),
        )
        .group_by(Interaction.rating_index)
    )
    positive_rows = positive_result.all()
    total_positive = sum(row.cnt for row in positive_rows) or 1

    vibe_breakdown = []
    for row in positive_rows:
        name = VIBE_NAMES[row.rating_index] if 0 <= row.rating_index < len(VIBE_NAMES) else "Unknown"
        vibe_breakdown.append(
            VibeBreakdownItem(name=name, percentage=round(row.cnt / total_positive, 2))
        )

    # Determine preferred length from positively-rated replies
    # Get the actual reply text for positively-rated interactions
    rated_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == user.id,
            Interaction.rating_positive == True,
            Interaction.rating_index.is_not(None),
        )
    )
    rated_interactions = rated_result.scalars().all()

    short_count = 0
    medium_count = 0
    long_count = 0
    for interaction in rated_interactions:
        reply_fields = [interaction.reply_0, interaction.reply_1, interaction.reply_2, interaction.reply_3]
        idx = interaction.rating_index
        if 0 <= idx < len(reply_fields):
            length = len(reply_fields[idx])
            if length < 50:
                short_count += 1
            elif length < 120:
                medium_count += 1
            else:
                long_count += 1

    if short_count >= medium_count and short_count >= long_count:
        preferred_length = "short"
    elif long_count >= medium_count and long_count >= short_count:
        preferred_length = "long"
    else:
        preferred_length = "medium"

    return UserPreferencesResponse(
        total_ratings=total_ratings,
        has_enough_data=True,
        vibe_breakdown=vibe_breakdown,
        preferred_length=preferred_length,
    )
