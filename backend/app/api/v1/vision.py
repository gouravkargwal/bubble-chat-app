"""Main reply generation endpoint — the core product."""

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from app.api.v1.schemas.schemas import VisionRequest, VisionResponse
from app.config import settings
from app.domain.conversation import build_conversation_context, find_or_create_conversation
from app.domain.voice_dna import to_domain as voice_to_domain
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Interaction, User, UserVoiceDNA
from app.llm.gemini_client import GeminiClient
from app.llm.response_parser import parse_llm_response
from app.prompts.engine import prompt_engine

router = APIRouter()
logger = structlog.get_logger()

# Lazy-initialized client
_client: GeminiClient | None = None


def _get_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient(api_key=settings.gemini_api_key, default_model=settings.gemini_model)
    return _client


@router.post("/vision/generate", response_model=VisionResponse)
async def generate_replies(
    request: VisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisionResponse:
    """Analyze screenshot and generate 4 reply suggestions."""
    # 1. Check rate limits
    daily_used = await count_today_interactions(user.id, db)
    if not user.is_premium and daily_used >= user.daily_limit:
        raise HTTPException(
            status_code=429,
            detail="Daily limit reached. Upgrade to Premium for unlimited replies.",
        )

    # 2. Load Voice DNA
    voice_dna = None
    result = await db.execute(
        select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
    )
    voice_db = result.scalar_one_or_none()
    if voice_db and voice_db.sample_count >= 3:
        voice_dna = voice_to_domain(voice_db)

    # 3. Try to find active conversation (from most recent interaction's person_name)
    conversation_context = None
    last_interaction = await db.execute(
        select(Interaction)
        .where(Interaction.user_id == user.id)
        .order_by(Interaction.created_at.desc())
        .limit(1)
    )
    last = last_interaction.scalar_one_or_none()
    if last and last.conversation_id:
        from app.infrastructure.database.models import Conversation

        convo_result = await db.execute(
            select(Conversation).where(Conversation.id == last.conversation_id)
        )
        convo = convo_result.scalar_one_or_none()
        if convo and convo.is_active:
            conversation_context = await build_conversation_context(convo, db)

    # 4. Build prompt
    payload = prompt_engine.build(
        direction=request.direction,
        custom_hint=request.custom_hint,
        voice_dna=voice_dna,
        conversation_context=conversation_context,
        variant_id=user.prompt_variant or "default",
    )

    # 5. Call Gemini
    client = _get_client()
    start = time.monotonic()
    try:
        raw = await client.vision_generate(
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
            base64_image=request.image,
            temperature=payload.temperature,
            model=settings.gemini_model,
        )
    except ValueError as e:
        error_msg = str(e)
        if "Invalid" in error_msg and "key" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid API key")
        if "rate limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail="LLM rate limit. Try again in a minute.")
        raise HTTPException(status_code=502, detail=f"LLM error: {error_msg}")
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        raise HTTPException(status_code=502, detail="Failed to generate replies. Try again.")

    latency_ms = int((time.monotonic() - start) * 1000)

    # 6. Parse response
    try:
        parsed = parse_llm_response(raw)
    except ValueError as e:
        logger.error("parse_failed", error=str(e), raw=raw[:200])
        raise HTTPException(status_code=502, detail="Failed to parse AI response. Try again.")

    # 7. Find or create conversation from detected person
    convo = await find_or_create_conversation(
        user_id=user.id,
        person_name=parsed.analysis.person_name,
        db=db,
    )

    # 8. Save interaction
    replies = parsed.replies + [""] * (4 - len(parsed.replies))  # pad to 4
    interaction = Interaction(
        conversation_id=convo.id,
        user_id=user.id,
        direction=request.direction,
        custom_hint=request.custom_hint,
        their_last_message=parsed.analysis.their_last_message,
        their_tone=parsed.analysis.their_tone,
        their_effort=parsed.analysis.their_effort,
        conversation_temperature=parsed.analysis.conversation_temperature,
        detected_stage=parsed.analysis.stage,
        person_name=parsed.analysis.person_name,
        key_detail=parsed.analysis.key_detail,
        reply_0=replies[0],
        reply_1=replies[1],
        reply_2=replies[2],
        reply_3=replies[3],
        llm_model=settings.gemini_model,
        prompt_variant=user.prompt_variant,
        temperature_used=payload.temperature,
        latency_ms=latency_ms,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    logger.info(
        "reply_generated",
        user_id=user.id,
        person=parsed.analysis.person_name,
        stage=parsed.analysis.stage,
        direction=request.direction,
        latency_ms=latency_ms,
    )

    remaining = user.daily_limit - daily_used - 1 if not user.is_premium else 9999
    return VisionResponse(
        replies=parsed.replies[:4],
        person_name=parsed.analysis.person_name if parsed.analysis.person_name != "unknown" else None,
        stage=parsed.analysis.stage,
        interaction_id=interaction.id,
        usage_remaining=max(0, remaining),
    )
