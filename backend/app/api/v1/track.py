"""Tracking endpoints — copy and rating events."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import CopyTrackRequest, RatingTrackRequest
from app.domain.conversation import update_conversation_from_analysis
from app.domain.models import AnalysisResult
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Conversation, Interaction, User
from app.core.embeddings import embed_text

router = APIRouter()
logger = structlog.get_logger()


@router.post("/track/copy")
async def track_copy(
    request: CopyTrackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Track which reply the user copied.

    IMPORTANT: This endpoint must NOT update Voice DNA. Voice DNA is only updated
    from organic text extracted from screenshots (see vision endpoints).
    """
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

    # Update copied index and store embedding of the copied reply
    interaction.copied_index = request.reply_index

    # Determine which reply text was copied
    reply_attr = f"reply_{request.reply_index}"
    reply_text = getattr(interaction, reply_attr, None)

    if reply_text:
        # Try to generate an embedding for semantic memory, but never block the user on failures.
        try:
            interaction.embedding = await embed_text(reply_text)
        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(
                "semantic_memory_failed",
                error=str(e),
                reply_preview=reply_text[:120] if reply_text else "",
            )
            interaction.embedding = None

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
