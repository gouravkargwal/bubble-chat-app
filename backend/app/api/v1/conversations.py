"""Conversation management endpoints."""

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    ConversationItem,
    ConversationListResponse,
    ResolveConversationRequest,
    VisionRequest,
)
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Conversation, User
from app.models.enums import ConversationDirection
from app.services.hybrid_stitch_pending import pop_pending_hybrid_resolution

from app.api.v1.vision import generate_replies as vision_generate_replies

router = APIRouter()
logger = structlog.get_logger()


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


@router.post("/conversations/resolve")
async def resolve_conversation(
    request: ResolveConversationRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resolve Hybrid Stitch after user confirmation.

    The initial ambiguity detection occurs in `POST /api/v1/vision/generate`.
    Here we:
    - pick the conversation_id (existing vs newly created),
    - re-run the generation pipeline using the cached screenshots/context.
    """

    if request.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    pending = pop_pending_hybrid_resolution(
        user_id=user.id,
        suggested_conversation_id=request.suggested_conversation_id,
    )
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="No pending merge confirmation found (expired or invalid).",
        )

    effective_conversation_id: str
    if request.is_match:
        # Link to the suggested existing conversation.
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.suggested_conversation_id,
                Conversation.user_id == user.id,
                Conversation.is_active == True,  # noqa: E712
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        effective_conversation_id = convo.id
    else:
        # Create a fresh conversation for the newly-detected person/platform.
        # Only deactivate the suggested conversation that the user rejected, not all
        # active conversations — the user may have other ongoing chats with different people.
        await db.execute(
            text(
                "UPDATE conversations SET is_active = false "
                "WHERE id = :conv_id AND user_id = :user_id"
            ),
            {"conv_id": request.suggested_conversation_id, "user_id": user.id},
        )
        convo = Conversation(
            user_id=user.id,
            person_name=pending.extracted_person_name,
            is_active=True,
        )
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        effective_conversation_id = convo.id

    vision_request = VisionRequest(
        images=pending.images,
        direction=ConversationDirection(pending.direction),
        custom_hint=pending.custom_hint,
        conversation_id=effective_conversation_id,
    )

    # Conflict logging: show exactly what forced the frontend into a 409 flow.
    logger.warning(
        "[CONFLICT] Resolving hybrid stitch pending resolution",
        user_id=user.id,
        suggested_conversation_id=request.suggested_conversation_id,
        conflict_reason=getattr(pending, "conflict_reason", None),
        conflict_detail=getattr(pending, "conflict_detail", None),
    )

    vision_response = await vision_generate_replies(
        request=vision_request,
        background_tasks=background_tasks,
        user=user,
        db=db,
    )
    # FastAPI expects a plain JSON-serializable dict for the declared return type.
    # `vision_response` is a Pydantic model (VisionResponse), so return its dump.
    if hasattr(vision_response, "model_dump"):
        return vision_response.model_dump()
    return vision_response.dict()
