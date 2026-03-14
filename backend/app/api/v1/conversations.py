"""Conversation management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import ConversationItem, ConversationListResponse
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Conversation, User

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """List active conversations for the user with pagination."""
    # Get total count
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.user_id == user.id,
            Conversation.is_active == True,  # noqa: E712
        )
    )
    total_count = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user.id, Conversation.is_active == True
        )  # noqa: E712
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    convos = result.scalars().all()

    return ConversationListResponse(
        items=[
            ConversationItem(
                id=c.id,
                person_name=c.person_name,
                stage=c.stage,
                tone_trend=c.tone_trend,
                interaction_count=c.interaction_count,
            )
            for c in convos
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete a conversation (forget a person)."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    convo.is_active = False
    await db.commit()
    return {"status": "ok"}
