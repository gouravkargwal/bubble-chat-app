"""Conversation management endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    ConversationItem,
    ConversationListResponse,
    ResolveConversationRequest,
    VisionRequest,
)
from app.api.v1.vision_shared import save_alias
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Conversation, User
from app.models.enums import ConversationDirection
from app.services.hybrid_stitch_pending import (
    pop_pending_hybrid_resolution,
    parse_pending_images,
    store_pending_hybrid_resolution,
)

from app.api.v1.vision_v2 import generate_replies_v2 as vision_generate_replies

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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resolve Hybrid Stitch after user confirmation.

    The initial ambiguity detection occurs in `POST /api/v1/vision/generate_v2`.
    Here we:
    - pick the conversation_id (existing vs newly created),
    - persist the alias for future instant lookups (feedback loop),
    - re-run the generation pipeline using the cached screenshots/context.
    """

    if request.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    pending = await pop_pending_hybrid_resolution(
        db=db,
        user_id=user.id,
        suggested_conversation_id=request.suggested_conversation_id,
    )
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="No pending merge confirmation found (expired or invalid).",
        )

    effective_conversation_id: str
    # Track if we created a placeholder conversation in the "No, New Person"
    # branch. If the re-run gets bounced by the vision bouncer (400), we
    # deactivate that placeholder so it won't be matched later.
    placeholder_conversation_id: str | None = None
    if request.is_match:
        # User confirmed: link to the suggested existing conversation.
        # Don't gate on is_active — the stitch engine may have matched an inactive convo.
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.suggested_conversation_id,
                Conversation.user_id == user.id,
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        # Reactivate if it was soft-deleted
        if not convo.is_active:
            convo.is_active = True
            await db.commit()
        effective_conversation_id = convo.id

        # Feedback loop: save the OCR name as an alias for this conversation
        await save_alias(
            db=db,
            user_id=user.id,
            alias_name=pending.extracted_person_name,
            conversation_id=convo.id,
            source="user_confirmed",
        )
    else:
        # User rejected: create a fresh conversation for the newly-detected person.
        # Only deactivate the suggested conversation that the user rejected, not all
        # active conversations — the user may have other ongoing chats.
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.suggested_conversation_id,
                Conversation.user_id == user.id,
            )
        )
        suggested_convo = convo_result.scalar_one_or_none()
        if suggested_convo:
            suggested_convo.is_active = False
            await db.commit()

        convo = Conversation(
            user_id=user.id,
            person_name=pending.extracted_person_name,
            is_active=True,
        )
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        effective_conversation_id = convo.id
        placeholder_conversation_id = convo.id

        # Save alias for the NEW conversation so future OCR of this name resolves correctly
        await save_alias(
            db=db,
            user_id=user.id,
            alias_name=pending.extracted_person_name,
            conversation_id=convo.id,
            source="user_confirmed",
        )

    images = parse_pending_images(pending)

    vision_request = VisionRequest(
        images=images,
        direction=ConversationDirection(pending.direction),
        custom_hint=pending.custom_hint,
        conversation_id=effective_conversation_id,
    )

    # Conflict logging: show exactly what forced the frontend into a 409 flow.
    logger.warning(
        "[CONFLICT] Resolving hybrid stitch pending resolution",
        user_id=user.id,
        suggested_conversation_id=request.suggested_conversation_id,
        conflict_reason=pending.conflict_reason,
        conflict_detail=pending.conflict_detail,
        is_match=request.is_match,
    )

    try:
        vision_response = await vision_generate_replies(
            request=vision_request,
            user=user,
            db=db,
        )
    except HTTPException as e:
        if (
            placeholder_conversation_id
            and getattr(e, "status_code", None) == 400
        ):
            try:
                placeholder_convo_result = await db.execute(
                    select(Conversation).where(
                        Conversation.id == placeholder_conversation_id,
                        Conversation.user_id == user.id,
                    )
                )
                placeholder_convo = placeholder_convo_result.scalar_one_or_none()
                if placeholder_convo and placeholder_convo.is_active:
                    placeholder_convo.is_active = False
                    await db.commit()
            except Exception:
                # Best-effort cleanup only; never mask the original error.
                logger.warning(
                    "resolve_placeholder_convo_rollback_failed",
                    user_id=user.id,
                    placeholder_conversation_id=placeholder_conversation_id,
                    exc_info=True,
                )

        # `pop_pending_hybrid_resolution` consumes the pending row. If generation fails
        # (e.g. transient 429/5xx or validation 400), restore pending context so the
        # user can retry `/conversations/resolve` instead of hitting a confusing 404.
        await store_pending_hybrid_resolution(
            db=db,
            user_id=user.id,
            suggested_conversation_id=request.suggested_conversation_id,
            images=images,
            direction=pending.direction,
            custom_hint=pending.custom_hint,
            extracted_person_name=pending.extracted_person_name,
            conflict_reason=pending.conflict_reason,
            conflict_detail=pending.conflict_detail,
        )
        raise

    # FastAPI expects a plain JSON-serializable dict for the declared return type.
    # `vision_response` is a Pydantic model (VisionResponse), so return its dump.
    if hasattr(vision_response, "model_dump"):
        return vision_response.model_dump()
    return vision_response.dict()
