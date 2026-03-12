"""Main reply generation endpoint — the core product."""

import json
import time

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import count_today_interactions, get_current_user
from app.api.v1.schemas.schemas import (
    CalibrationRequest,
    CalibrationResponse,
    VisionRequest,
    VisionResponse,
)
from app.config import settings
from app.domain.conversation import (
    build_conversation_context,
    find_or_create_conversation,
)
from app.domain.tiers import get_effective_tier, get_tier_config
from app.domain.voice_dna import to_domain as voice_to_domain
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import (
    Conversation,
    Interaction,
    User,
    UserVoiceDNA,
)
from app.domain.voice_dna import update_voice_dna_stats
from app.services.voice_dna import generate_semantic_profile_background
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
        "visual_transcript": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "side": {
                        "type": "STRING",
                        "description": "Exactly 'left' or 'right'",
                    },
                    "sender": {
                        "type": "STRING",
                        "description": "'user' if right, 'them' if left",
                    },
                    "message_text": {
                        "type": "STRING",
                        "description": "Max 15 words of the bubble's text.",
                    },
                },
                "required": ["side", "sender", "message_text"],
            },
            "description": "Chronological transcript of the last 3-4 visible chat bubbles.",
        },
        "analysis": {
            "type": "OBJECT",
            "properties": {
                "detected_language_and_vibe": {
                    "type": "STRING",
                    "description": "Max 5 words.",
                },
                "their_last_message": {
                    "type": "STRING",
                    "description": "Max 8 words. Paraphrase.",
                },
                "who_texted_last": {
                    "type": "STRING",
                    "description": "Exactly 'user', 'them', or 'unclear'.",
                },
                "their_tone": {
                    "type": "STRING",
                    "description": "Max 3 words.",
                },
                "their_effort": {
                    "type": "STRING",
                    "description": "Max 3 words.",
                },
                "conversation_temperature": {
                    "type": "STRING",
                    "description": "Max 2 words.",
                },
                "stage": {
                    "type": "STRING",
                    "description": "Max 3 words.",
                },
                "person_name": {
                    "type": "STRING",
                    "description": "First name or 'unknown'.",
                },
                "key_detail": {
                    "type": "STRING",
                    "description": "Max 8 words. Telegraphic.",
                },
                "what_they_want": {
                    "type": "STRING",
                    "description": "Max 8 words.",
                },
                "notable_observations": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING",
                    },
                    "description": (
                        "List exactly 4 completely different details about this person. "
                        "Include at least 1 text bio detail, 1 background/photo detail, "
                        "and 1 style/vibe detail. DO NOT repeat topics."
                    ),
                },
            },
            "required": [
                "detected_language_and_vibe",
                "their_last_message",
                "who_texted_last",
                "their_tone",
                "their_effort",
                "conversation_temperature",
                "stage",
                "person_name",
                "key_detail",
                "what_they_want",
                "notable_observations",
            ],
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
    "required": ["visual_transcript", "analysis", "strategy", "replies"],
}


def _get_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient(
            api_key=settings.gemini_api_key, default_model=settings.gemini_model
        )
    return _client


@router.post("/vision/calibrate", response_model=CalibrationResponse)
async def calibrate_voice_dna(
    request: CalibrationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalibrationResponse:
    """Extracts organic text from screenshots purely to build Voice DNA. Does not generate replies."""
    if not request.images:
        raise HTTPException(status_code=400, detail="Images required.")

    CALIBRATION_SCHEMA: dict = {
        "type": "OBJECT",
        "properties": {
            "user_messages": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": (
                    "Extract ONLY the text from the bubbles sent by the user "
                    "(usually on the right side in blue or green). Ignore the other person's text."
                ),
            }
        },
        "required": ["user_messages"],
    }

    client = _get_client()
    system_prompt = (
        "You are a data extractor. Read the screenshot and extract the exact text of "
        "the messages sent by the user."
    )

    try:
        raw = await client.vision_generate(
            system_prompt=system_prompt,
            user_prompt="Extract my messages.",
            base64_images=request.images,
            temperature=0.1,
            model=settings.gemini_model,
            max_output_tokens=500,
            response_schema=CALIBRATION_SCHEMA,
        )
        parsed = json.loads(raw)
        extracted_texts = parsed.get("user_messages", [])
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error("calibration_extraction_failed", error=str(e))
        raise HTTPException(status_code=502, detail="Failed to read screenshots.")

    if not extracted_texts:
        return CalibrationResponse(messages_extracted=0, success=True)

    # Update the Voice DNA database with organic texts only
    voice_result = await db.execute(
        select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
    )
    voice_db = voice_result.scalar_one_or_none()
    if voice_db is None:
        voice_db = UserVoiceDNA(user_id=user.id)
        db.add(voice_db)

    count = 0
    for text in extracted_texts:
        if text and len(text) > 3:  # Ignore tiny things like "hi" or "ok"
            update_voice_dna_stats(voice_db, text)
            count += 1

    await db.commit()

    return CalibrationResponse(messages_extracted=count, success=True)


@router.post("/vision/generate", response_model=VisionResponse)
async def generate_replies(
    request: VisionRequest,
    background_tasks: BackgroundTasks,
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

    # 8. Load conversation context only if tier supports memory and a conversation_id is provided
    conversation_context = None
    if tier_config.conversation_memory and request.conversation_id:
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user.id,
            )
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
    t1 = t2 = t3 = start

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

    # Dynamic token routing: Give a massive ceiling for the model's 'thought' process
    max_tokens = 8000 + (1000 * len(images))

    raw = ""
    parsed = None

    # Phase 1: setup completed (everything before the first LLM call)
    t1 = time.monotonic()
    logger.info(
        "vision_timing_phase_1_setup",
        timing_phase_1_setup_ms=int((t1 - start) * 1000),
    )

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

            # Phase 2: LLM call latency
            t2 = time.monotonic()
            logger.info(
                "vision_timing_phase_2_llm",
                timing_phase_2_llm_ms=int((t2 - t1) * 1000),
            )

            parsed = parse_llm_response(raw)

            # ---------------------------------------------------------
            # VOICE DNA: THE ECHO FILTER & EXTRACTION
            # ---------------------------------------------------------
            user_organic_text = None

            # 1. Extract the last thing the user actually sent (the right-side bubble)
            if parsed and parsed.visual_transcript:
                for msg in reversed(parsed.visual_transcript):
                    if msg.side.lower() == "right" or msg.sender.lower() == "user":
                        user_organic_text = msg.message_text
                        break

            # 2. The Echo Filter: Check if they copied an AI suggestion
            if user_organic_text and len(user_organic_text) > 3:
                clean_text = user_organic_text.lower().strip()

                # Pull the last 10 interactions to cross-reference
                recent_interactions_query = await db.execute(
                    select(Interaction)
                    .where(Interaction.user_id == user.id)
                    .order_by(Interaction.created_at.desc())
                    .limit(10)
                )
                recent_interactions = recent_interactions_query.scalars().all()

                is_echo = False
                for past_int in recent_interactions:
                    past_replies = [
                        (past_int.reply_0 or "").lower().strip(),
                        (past_int.reply_1 or "").lower().strip(),
                        (past_int.reply_2 or "").lower().strip(),
                        (past_int.reply_3 or "").lower().strip(),
                    ]

                    # If the text is a 90% match to an AI suggestion, it's an Echo.
                    if any(
                        pr in clean_text or clean_text in pr
                        for pr in past_replies
                        if len(pr) > 5
                    ):
                        is_echo = True
                        logger.info(
                            "voice_dna_echo_detected", user_id=user.id, text=clean_text
                        )
                        user_organic_text = None  # Discard it
                        break

                if not is_echo:
                    # The user typed this themselves! It is organic data.
                    logger.info(
                        "voice_dna_organic_text_found",
                        user_id=user.id,
                        text=clean_text,
                    )

                    # Update Voice DNA stats and recent organic messages
                    voice_result = await db.execute(
                        select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
                    )
                    voice_db = voice_result.scalar_one_or_none()
                    if voice_db is None:
                        voice_db = UserVoiceDNA(user_id=user.id)
                        db.add(voice_db)

                    updated_dna = update_voice_dna_stats(voice_db, clean_text)
                    await db.commit()

                    # Trigger Semantic Profiling for Premium users if they have enough data
                    try:
                        messages_list = (
                            json.loads(updated_dna.recent_organic_messages)
                            if getattr(updated_dna, "recent_organic_messages", None)
                            else []
                        )
                    except (json.JSONDecodeError, TypeError):
                        messages_list = []

                    if (
                        effective_tier in ["premium", "pro"]
                        and len(messages_list) >= 5
                        and not getattr(updated_dna, "semantic_profile", None)
                    ):
                        background_tasks.add_task(
                            generate_semantic_profile_background,
                            user_id=user.id,
                            db=db,
                            messages=messages_list,
                        )

            # Phase 3: parsing latency
            t3 = time.monotonic()
            logger.info(
                "vision_timing_phase_3_parse",
                timing_phase_3_parse_ms=int((t3 - t2) * 1000),
            )
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

    # 11. Resolve conversation using explicit conversation_id when provided
    if request.conversation_id:
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        # Self-heal missing names: upgrade from 'unknown' when we detect a real name
        if (
            convo.person_name
            and convo.person_name.lower() == "unknown"
            and parsed.analysis.person_name
            and parsed.analysis.person_name.lower() != "unknown"
        ):
            convo.person_name = parsed.analysis.person_name
    else:
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
        user_organic_text=user_organic_text,
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

    # Phase 4: DB writes and response construction latency
    t4 = time.monotonic()
    logger.info(
        "vision_timing_phase_4_db_writes",
        timing_phase_4_db_writes_ms=int((t4 - t3) * 1000),
    )

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
        conversation_id=convo.id,
    )
