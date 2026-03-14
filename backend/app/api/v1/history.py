"""Interaction history endpoints — replaces client-side Room DB."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    HistoryItemResponse,
    HistoryListResponse,
    ReplyOptionPayload,
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
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HistoryListResponse:
    """Return user's recent interaction history with pagination."""
    # Get total count
    count_result = await db.execute(
        select(func.count(Interaction.id)).where(Interaction.user_id == user.id)
    )
    total_count = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(Interaction)
        .where(Interaction.user_id == user.id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    interactions = result.scalars().all()

    items: list[HistoryItemResponse] = []
    for i in interactions:
        raw_replies = [i.reply_0, i.reply_1, i.reply_2, i.reply_3]
        parsed_replies: list[ReplyOptionPayload] = []
        for raw in raw_replies:
            if not raw:
                continue
            try:
                import json

                data = json.loads(raw)
                parsed_replies.append(
                    ReplyOptionPayload(
                        text=str(data.get("text", "")).strip(),
                        strategy_label=str(data.get("strategy_label", "STANDARD")),
                        is_recommended=bool(data.get("is_recommended", False)),
                        coach_reasoning=str(data.get("coach_reasoning", "")),
                    )
                )
            except Exception:
                # Legacy plain-text fallback
                parsed_replies.append(
                    ReplyOptionPayload(
                        text=raw,
                        strategy_label="STANDARD",
                        is_recommended=False,
                        coach_reasoning="",
                    )
                )

        items.append(
            HistoryItemResponse(
                id=i.id,
                person_name=i.person_name,
                direction=i.direction,
                custom_hint=i.custom_hint,
                replies=parsed_replies,
                copied_index=i.copied_index,
                created_at=int(i.created_at.timestamp()),
                user_organic_text=i.user_organic_text,
            )
        )
    return HistoryListResponse(
        items=items, total_count=total_count, limit=limit, offset=offset
    )


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
    """Compute user's vibe preferences from server-side ratings (both positive and negative)."""
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

    # Count ALL ratings (positive and negative) grouped by reply index (vibe)
    all_ratings_result = await db.execute(
        select(
            Interaction.rating_index,
            Interaction.rating_positive,
            func.count(Interaction.id).label("cnt"),
        )
        .where(
            Interaction.user_id == user.id,
            Interaction.rating_index.is_not(None),
        )
        .group_by(Interaction.rating_index, Interaction.rating_positive)
    )
    all_ratings_rows = all_ratings_result.all()

    # Calculate net score for each vibe: (positive_count - negative_count)
    vibe_scores = {}  # {vibe_index: net_score}
    for row in all_ratings_rows:
        vibe_idx = row.rating_index
        count = row.cnt
        if vibe_idx not in vibe_scores:
            vibe_scores[vibe_idx] = 0
        if row.rating_positive:
            vibe_scores[vibe_idx] += count
        else:
            vibe_scores[vibe_idx] -= count

    # Filter out negative-net-score vibes and normalize to percentages
    positive_vibes = {k: v for k, v in vibe_scores.items() if v > 0}
    total_positive_score = sum(positive_vibes.values()) or 1

    vibe_breakdown = []
    for vibe_idx, score in positive_vibes.items():
        name = VIBE_NAMES[vibe_idx] if 0 <= vibe_idx < len(VIBE_NAMES) else "Unknown"
        vibe_breakdown.append(
            VibeBreakdownItem(
                name=name, percentage=round(score / total_positive_score, 2)
            )
        )

    # Sort by percentage descending
    vibe_breakdown.sort(key=lambda x: x.percentage, reverse=True)

    # Determine preferred length from positively-rated replies only
    # (negative ratings don't tell us much about length preference)
    rated_result = await db.execute(
        select(Interaction).where(
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
        reply_fields = [
            interaction.reply_0,
            interaction.reply_1,
            interaction.reply_2,
            interaction.reply_3,
        ]
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
