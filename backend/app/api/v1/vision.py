"""Main reply generation endpoint — the core product."""

import json
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


GEMINI_RESPONSE_SCHEMA: dict = {
    "type": "OBJECT",
    "properties": {
        "spatial_audit": {
            "type": "OBJECT",
            "properties": {
                "right_side_user_facts": {
                    "type": "STRING",
                    "description": (
                        "Bullet points only. Max 20 words total. "
                        "Key on-screen facts about the user/right side only."
                    ),
                },
                "left_side_them_facts": {
                    "type": "STRING",
                    "description": (
                        "Bullet points only. Max 20 words total. "
                        "Key on-screen facts about them/left side only."
                    ),
                },
            },
        },
        "analysis": {
            "type": "OBJECT",
            "properties": {
                "detected_language_and_vibe": {
                    "type": "STRING",
                    "description": (
                        "Under 2 short sentences. Detect chat language and high-level vibe only."
                    ),
                },
                "their_last_message": {
                    "type": "STRING",
                    "description": (
                        "Very short paraphrase of their last message. Max 25 words. No emojis."
                    ),
                },
                "who_texted_last": {
                    "type": "STRING",
                    "description": (
                        "Exactly one of: 'user', 'them', or 'unknown'. No extra words."
                    ),
                },
                "their_tone": {
                    "type": "STRING",
                    "description": (
                        "Single short phrase summarizing their tone, e.g. 'playful but cautious'. "
                        "Max 8 words."
                    ),
                },
                "their_effort": {
                    "type": "STRING",
                    "description": (
                        "Single short phrase for effort level, e.g. 'low effort, one-word replies'. "
                        "Max 8 words."
                    ),
                },
                "conversation_temperature": {
                    "type": "STRING",
                    "description": (
                        "Single short phrase (e.g. 'cold', 'warming up', 'very warm'). Max 5 words."
                    ),
                },
                "stage": {
                    "type": "STRING",
                    "description": (
                        "Single short phrase for relationship stage, e.g. 'early texting', "
                        "'planning first date'. Max 8 words."
                    ),
                },
                "person_name": {
                    "type": "STRING",
                    "description": (
                        "Their first name only if clearly visible. Otherwise 'unknown'."
                    ),
                },
                "key_detail": {
                    "type": "STRING",
                    "description": (
                        "One critical contextual detail you must remember. "
                        "Max 20 words. No lists."
                    ),
                },
                "what_they_want": {
                    "type": "STRING",
                    "description": (
                        "Best guess of what they want from the convo right now. "
                        "Max 20 words. Single sentence."
                    ),
                },
            },
            "required": ["detected_language_and_vibe"],
        },
        "strategy": {
            "type": "OBJECT",
            "properties": {
                "wrong_moves": {"type": "ARRAY", "items": {"type": "STRING"}},
                "right_energy": {"type": "STRING"},
                "hook_point": {"type": "STRING"},
            },
        },
        "replies": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Exactly 4 distinct string replies.",
        },
    },
    "required": ["spatial_audit", "analysis", "strategy", "replies"],
}


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
            voice_dna = await voice_to_domain(voice_db, db)

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

    # 10. Dynamic temperature routing + call Gemini with retry on JSON truncation
    client = _get_client()
    start = time.monotonic()

    # Dynamic Temperature Routing:
    # Different directions and custom hints need different creativity levels.
    direction_key = (request.direction or "").lower()
    if custom_hint:
        # User provided a specific angle → medium-high creativity.
        llm_temperature = 0.7
    elif direction_key == "opener":
        # Cold read → max creativity.
        llm_temperature = 0.8
    elif direction_key in ("change_topic", "tease"):
        # Needs high creativity to pivot/joke.
        llm_temperature = 0.75
    elif direction_key == "revive_chat":
        llm_temperature = 0.6
    elif direction_key in ("get_number", "ask_out"):
        # Goal-oriented → lower creativity, more precision.
        llm_temperature = 0.5
    else:
        # quick_reply and anything else → strict context matching.
        llm_temperature = 0.4

    # Dynamic token routing: base 1500 tokens + 500 per image.
    max_tokens = 1500 + 500 * len(images)

    raw = ""
    parsed = None

    for attempt in range(1, 3):
        try:
            raw = await client.vision_generate(
                system_prompt=payload.system_prompt,
                user_prompt=payload.user_prompt,
                base64_images=images,
                temperature=llm_temperature,
                model=settings.gemini_model,
                max_output_tokens=int(max_tokens),
                response_schema=GEMINI_RESPONSE_SCHEMA,
            )
            parsed = parse_llm_response(raw)
            logger.info(
                "replies_generated",
                attempt=attempt,
                replies_count=len(parsed.replies),
                reply_lengths=[len(r) for r in parsed.replies],
                reply_previews=[r[:50] for r in parsed.replies],
            )
            break
        except json.JSONDecodeError as e:
            # Handle Gemini sometimes truncating JSON strings.
            if attempt == 1 and "Unterminated string" in str(e):
                logger.warning(
                    "llm_json_unterminated_retry",
                    attempt=attempt,
                    error=str(e),
                    old_max_tokens=max_tokens,
                )
                max_tokens *= 1.5
                continue
            logger.error(
                "llm_json_decode_error",
                attempt=attempt,
                error=str(e),
                raw_preview=raw[:200],
            )
            raise HTTPException(
                status_code=502, detail="Failed to parse AI JSON response. Try again."
            )
        except ValueError as e:
            # parse_llm_response or client-level validation error
            logger.error(
                "llm_value_error",
                attempt=attempt,
                error=str(e),
                raw_preview=raw[:200],
            )
            raise HTTPException(
                status_code=502, detail="Failed to generate replies. Try again."
            )
        except Exception as e:
            logger.error(
                "llm_call_failed",
                attempt=attempt,
                error=str(e),
            )
            raise HTTPException(
                status_code=502, detail="Failed to generate replies. Try again."
            )

    if parsed is None:
        logger.error("llm_no_successful_attempts")
        raise HTTPException(
            status_code=502, detail="Failed to generate replies. Try again."
        )

    latency_ms = int((time.monotonic() - start) * 1000)

    # 11. Find or create conversation from detected person
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
        temperature_used=llm_temperature,
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
