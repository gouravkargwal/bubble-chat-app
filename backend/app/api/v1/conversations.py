"""Conversation management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import ConversationItem, ConversationListResponse
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Conversation, User

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """List all active conversations for the user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.is_active == True)  # noqa: E712
        .order_by(Conversation.last_interaction_at.desc())
    )
    convos = result.scalars().all()

    return ConversationListResponse(
        conversations=[
            ConversationItem(
                id=c.id,
                person_name=c.person_name,
                stage=c.stage,
                tone_trend=c.tone_trend,
                interaction_count=c.interaction_count,
            )
            for c in convos
        ]
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
