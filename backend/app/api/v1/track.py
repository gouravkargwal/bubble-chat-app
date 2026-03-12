"""Tracking endpoints — copy and rating events."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import CopyTrackRequest, RatingTrackRequest
from app.domain.conversation import update_conversation_from_analysis
from app.domain.models import AnalysisResult
from app.domain.voice_dna import update_voice_dna_stats
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import (
    Conversation,
    Interaction,
    User,
    UserVoiceDNA,
)

router = APIRouter()
logger = structlog.get_logger()


@router.post("/track/copy")
async def track_copy(
    request: CopyTrackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Track which reply the user copied. Updates Voice DNA."""
    # Find interaction
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == request.interaction_id,
            Interaction.user_id == user.id,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    # Update copied index
    interaction.copied_index = request.reply_index
    await db.commit()

    # Get the copied reply text
    copied_text = getattr(interaction, f"reply_{request.reply_index}", None)
    if not copied_text:
        return {"status": "ok"}

    # Update Voice DNA (using copied reply as a proxy for their style, when no organic text yet)
    voice_result = await db.execute(
        select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
    )
    voice = voice_result.scalar_one_or_none()
    if voice is None:
        voice = UserVoiceDNA(user_id=user.id)
        db.add(voice)

    update_voice_dna_stats(voice, copied_text)
    await db.commit()

    # Update conversation context (mark topic as "worked")
    if interaction.conversation_id:
        convo_result = await db.execute(
            select(Conversation).where(Conversation.id == interaction.conversation_id)
        )
        convo = convo_result.scalar_one_or_none()
        if convo:
            analysis = AnalysisResult(
                stage=interaction.detected_stage or "early_talking",
                person_name=interaction.person_name or "unknown",
                key_detail=interaction.key_detail or "",
                conversation_temperature=interaction.conversation_temperature or "warm",
            )
            await update_conversation_from_analysis(
                convo, analysis, request.reply_index, db
            )

    logger.info("copy_tracked", user_id=user.id, reply_index=request.reply_index)
    return {"status": "ok"}


@router.post("/track/rating")
async def track_rating(
    request: RatingTrackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Track thumbs up/down rating on a reply."""
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == request.interaction_id,
            Interaction.user_id == user.id,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction.rating_index = request.reply_index
    interaction.rating_positive = request.is_positive
    await db.commit()

    logger.info(
        "rating_tracked",
        user_id=user.id,
        reply_index=request.reply_index,
        positive=request.is_positive,
    )
    return {"status": "ok"}
