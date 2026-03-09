"""Main reply generation endpoint — the core product."""

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from app.api.v1.schemas.schemas import VisionRequest, VisionResponse
from app.config import settings
from app.domain.conversation import (
    build_conversation_context,
    find_or_create_conversation,
)
from app.domain.tiers import get_effective_tier, get_tier_config
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
        _client = GeminiClient(
            api_key=settings.gemini_api_key, default_model=settings.gemini_model
        )
    return _client


@router.post("/vision/generate", response_model=VisionResponse)
async def generate_replies(
    request: VisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisionResponse:
    """Analyze screenshot and generate 4 reply suggestions."""
    # 1. Resolve tier and feature config
    effective_tier = get_effective_tier(user)
    tier_config = get_tier_config(effective_tier)

    # 2. Check daily rate limit (0 = unlimited)
    daily_used = await count_today_interactions(user.id, db)
    effective_limit = tier_config.daily_limit + user.bonus_replies
    if tier_config.daily_limit > 0 and daily_used >= effective_limit:
        raise HTTPException(
            status_code=429,
            detail="Daily limit reached. Upgrade to Premium for more replies.",
        )

    # 3. Resolve images (support both `image` and `images` fields)
    images: list[str] = []
    if request.images:
        images = request.images
    elif request.image:
        images = [request.image]
    if not images:
        raise HTTPException(
            status_code=400, detail="At least one screenshot is required."
        )

    # 4. Enforce max screenshots per tier
    if len(images) > tier_config.max_screenshots:
        images = images[-tier_config.max_screenshots :]  # keep most recent

    # 5. Validate direction against tier's allowed directions
    if request.direction not in tier_config.allowed_directions:
        raise HTTPException(
            status_code=403,
            detail=f"Direction '{request.direction}' requires a higher tier.",
        )

    # 6. Strip custom hint if tier doesn't support it
    custom_hint = request.custom_hint if tier_config.custom_hints else None

    # 7. Load Voice DNA only if tier supports it
    voice_dna = None
    if tier_config.voice_dna:
        result = await db.execute(
            select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
        )
        voice_db = result.scalar_one_or_none()
        if voice_db and voice_db.sample_count >= 3:
            voice_dna = voice_to_domain(voice_db)

    # 8. Load conversation context only if tier supports memory
    conversation_context = None
    if tier_config.conversation_memory:
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

    # 9. Build prompt using tier's variant
    payload = prompt_engine.build(
        direction=request.direction,
        custom_hint=custom_hint,
        voice_dna=voice_dna,
        conversation_context=conversation_context,
        variant_id=tier_config.prompt_variant,
    )

    # 10. Call Gemini
    client = _get_client()
    start = time.monotonic()
    try:
        raw = await client.vision_generate(
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
            base64_images=images,
            temperature=payload.temperature,
            model=settings.gemini_model,
            max_output_tokens=tier_config.max_output_tokens,
        )
    except ValueError as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=429, detail="LLM rate limit. Try again in a minute."
            )
        logger.error("llm_value_error", error=error_msg)
        raise HTTPException(
            status_code=502, detail="Failed to generate replies. Try again."
        )
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        raise HTTPException(
            status_code=502, detail="Failed to generate replies. Try again."
        )

    latency_ms = int((time.monotonic() - start) * 1000)

    # 11. Parse response
    try:
        parsed = parse_llm_response(raw)
        logger.info(
            "replies_generated",
            replies_count=len(parsed.replies),
            reply_lengths=[len(r) for r in parsed.replies],
            reply_previews=[r[:50] for r in parsed.replies],
        )
    except ValueError as e:
        logger.error("parse_failed", error=str(e), raw=raw[:200])
        raise HTTPException(
            status_code=502, detail="Failed to parse AI response. Try again."
        )

    # 12. Find or create conversation from detected person
    convo = await find_or_create_conversation(
        user_id=user.id,
        person_name=parsed.analysis.person_name,
        db=db,
    )

    # 13. Save interaction
    replies = parsed.replies + [""] * (4 - len(parsed.replies))  # pad to 4

    # Defensive: clamp analysis strings to DB limits (String(255))
    their_tone = parsed.analysis.their_tone
    if their_tone and len(their_tone) > 255:
        logger.warning(
            "analysis_tone_truncated",
            original_length=len(their_tone),
        )
        their_tone = their_tone[:255]

    their_effort = parsed.analysis.their_effort
    if their_effort and len(their_effort) > 255:
        logger.warning(
            "analysis_effort_truncated",
            original_length=len(their_effort),
        )
        their_effort = their_effort[:255]

    conversation_temperature = parsed.analysis.conversation_temperature
    if conversation_temperature and len(conversation_temperature) > 255:
        logger.warning(
            "analysis_temperature_truncated",
            original_length=len(conversation_temperature),
        )
        conversation_temperature = conversation_temperature[:255]

    detected_stage = parsed.analysis.stage
    if detected_stage and len(detected_stage) > 255:
        logger.warning(
            "analysis_stage_truncated",
            original_length=len(detected_stage),
        )
        detected_stage = detected_stage[:255]

    interaction = Interaction(
        conversation_id=convo.id,
        user_id=user.id,
        direction=request.direction,
        custom_hint=custom_hint,
        their_last_message=parsed.analysis.their_last_message,
        their_tone=their_tone,
        their_effort=their_effort,
        conversation_temperature=conversation_temperature,
        detected_stage=detected_stage,
        person_name=parsed.analysis.person_name,
        key_detail=parsed.analysis.key_detail,
        reply_0=replies[0],
        reply_1=replies[1],
        reply_2=replies[2],
        reply_3=replies[3],
        llm_model=settings.gemini_model,
        prompt_variant=tier_config.prompt_variant,
        temperature_used=payload.temperature,
        screenshot_count=len(images),
        latency_ms=latency_ms,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    logger.info(
        "reply_generated",
        user_id=user.id,
        tier=effective_tier,
        person=parsed.analysis.person_name,
        stage=parsed.analysis.stage,
        direction=request.direction,
        screenshot_count=len(images),
        latency_ms=latency_ms,
    )

    if tier_config.daily_limit > 0:
        remaining = effective_limit - daily_used - 1
    else:
        remaining = 9999
    return VisionResponse(
        replies=parsed.replies[:4],
        person_name=(
            parsed.analysis.person_name
            if parsed.analysis.person_name != "unknown"
            else None
        ),
        stage=parsed.analysis.stage,
        interaction_id=interaction.id,
        usage_remaining=max(0, remaining),
    )
