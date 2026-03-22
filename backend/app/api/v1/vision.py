"""Main reply generation endpoint — the core product."""

import asyncio
import copy
import dataclasses
import json
from datetime import datetime, timezone
import time

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    CalibrationRequest,
    CalibrationResponse,
    ReplyOptionPayload,
    VisionRequest,
    VisionResponse,
    RequiresUserConfirmation,
)
from app.api.v1.vision_shared import (
    resolve_hybrid_stitch_conversation_id,
    save_alias,
)
from app.config import settings
from app.domain.conversation import (
    build_conversation_context,
    find_or_create_conversation,
)
from app.domain.models import (
    AnalysisResult,
    ConversationContext,
    ParsedLlmResponse,
    ReplyOption as DomainReplyOption,
    StrategyResult,
    VisualTranscriptItem,
    VoiceDNA,
)
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.domain.voice_dna import to_domain as voice_to_domain
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import (
    Conversation,
    Interaction,
    User,
    UserVoiceDNA,
)
from app.services.quota_manager import QuotaExceededException, QuotaManager
from app.domain.voice_dna import update_voice_dna_stats, is_echo_text
from app.services.voice_dna import generate_semantic_profile_background
from app.llm.gemini_client import GeminiClient
from app.llm.response_parser import parse_llm_response
from app.prompts.engine import prompt_engine
from app.services.hybrid_stitch_pending import (
    has_pending_hybrid_resolution,
    store_pending_hybrid_resolution,
)

router = APIRouter()
logger = structlog.get_logger()

# Lazy-initialized client
_client: GeminiClient | None = None


# ---------- LangGraph agent wiring ----------

def _build_agent_initial_state(
    image_base64: str,
    direction: str,
    custom_hint: str,
    user_id: str,
    conversation_id: str | None,
    voice_dna: VoiceDNA | None,
    conversation_context: ConversationContext | None,
) -> dict:
    """Build initial AgentState for the LangGraph agent."""
    voice_dict = dataclasses.asdict(voice_dna) if voice_dna else {}
    context_dict = dataclasses.asdict(conversation_context) if conversation_context else {}
    return {
        "image_bytes": image_base64,
        "direction": direction,
        "custom_hint": custom_hint,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "voice_dna_dict": voice_dict,
        "conversation_context_dict": context_dict,
        "is_valid_chat": True,
        "bouncer_reason": "",
        "analysis": None,
        "strategy": None,
        "drafts": None,
        "is_cringe": False,
        "auditor_feedback": "",
        "revision_count": 0,
        "core_lore": "",
        "past_memories": "",
        "raw_ocr_text": [],
        "ocr_hint_text": "",
        "gemini_usage_log": [],
    }


def _run_agent_sync(initial_state: dict) -> dict:
    """Run the compiled LangGraph agent (sync, for use in thread)."""
    from agent.graph import rizz_agent
    return rizz_agent.invoke(initial_state)


async def _run_agent(initial_state: dict) -> dict:
    """Run the agent without blocking the event loop."""
    return await asyncio.to_thread(_run_agent_sync, initial_state)


def _parsed_from_agent_state(final_state: dict) -> ParsedLlmResponse:
    """Map final agent state to ParsedLlmResponse for persistence and response."""
    analysis_out = final_state["analysis"]
    strategy_out = final_state["strategy"]
    drafts = final_state["drafts"]

    visual_transcript = []
    for bubble in analysis_out.visual_transcript:
        visual_transcript.append(
            VisualTranscriptItem(
                side="right" if bubble.sender == "user" else "left",
                sender=bubble.sender,
                quoted_context=bubble.quoted_context,
                actual_new_message=bubble.actual_new_message,
                is_reply_to_user=False,
            )
        )

    analysis = AnalysisResult(
        their_last_message=getattr(analysis_out, "their_last_message", "") or "",
        who_texted_last="unclear",
        their_tone=analysis_out.their_tone,
        their_effort=analysis_out.their_effort,
        conversation_temperature=analysis_out.conversation_temperature,
        stage=getattr(analysis_out, "stage", "early_talking") or "early_talking",
        person_name=getattr(analysis_out, "person_name", "unknown") or "unknown",
        key_detail=analysis_out.key_detail,
        what_they_want="",
        detected_dialect=analysis_out.detected_dialect,
        their_actual_new_message=(
            next(
                (b.actual_new_message for b in reversed(analysis_out.visual_transcript) if b.sender == "them"),
                "",
            )
            if analysis_out.visual_transcript else ""
        ),
        detected_archetype=analysis_out.detected_archetype,
        archetype_reasoning=analysis_out.archetype_reasoning,
    )

    strategy = StrategyResult(
        wrong_moves=strategy_out.wrong_moves,
        right_energy=strategy_out.right_energy,
        hook_point=strategy_out.hook_point,
    )

    replies = [
        DomainReplyOption(
            text=r.text,
            strategy_label=r.strategy_label,
            is_recommended=r.is_recommended,
            coach_reasoning=r.coach_reasoning,
        )
        for r in drafts.replies[:4]
    ]

    return ParsedLlmResponse(
        visual_transcript=visual_transcript,
        analysis=analysis,
        strategy=strategy,
        replies=replies,
    )


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
                        "description": "Exactly 'left' or 'right'.",
                    },
                    "sender": {
                        "type": "STRING",
                        "description": "'user' if right, 'them' if left.",
                    },
                    "quoted_context": {
                        "type": "STRING",
                        "description": (
                            "If you see a grey/indented box at the top of a bubble, "
                            "this field MUST contain ONLY the text from that nested box. "
                            "If there is no quoted box, return an empty string."
                        ),
                    },
                    "actual_new_message": {
                        "type": "STRING",
                        "description": (
                            "The ACTUAL new message text in this bubble. "
                            "This is the bottom-most text directly typed by the sender, "
                            "NOT any quoted/previous message."
                        ),
                    },
                    "is_reply_to_user": {
                        "type": "BOOLEAN",
                        "description": (
                            "true if the ACTUAL new message is replying to something "
                            "the user previously said (e.g., when a quoted box shows "
                            "the user's older message), otherwise false."
                        ),
                    },
                },
                "required": [
                    "side",
                    "sender",
                    "actual_new_message",
                    "is_reply_to_user",
                ],
            },
            "description": (
                "Chronological transcript of the last 3-4 visible chat bubbles. "
                "For each bubble, separate any nested quoted box text into "
                "`quoted_context` and put only the bottom-most, fresh text into "
                "`actual_new_message`."
            ),
        },
        "analysis": {
            "type": "OBJECT",
            "properties": {
                "detected_language_and_vibe": {
                    "type": "STRING",
                    "description": "Max 5 words.",
                },
                "detected_dialect": {
                    "type": "STRING",
                    "enum": ["ENGLISH", "HINDI", "HINGLISH"],
                    "description": (
                        "High-level language bucket for the chat text. "
                        "Classify based on the dominant style of the ACTUAL messages "
                        "and Voice DNA: pure English, pure Hindi, or Romanized Hinglish "
                        "(e.g., 'kya kar rahe ho'). Do NOT translate when deciding this."
                    ),
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
                "their_actual_new_message": {
                    "type": "STRING",
                    "description": (
                        "The EXACT, verbatim text of her most recent ACTUAL new message "
                        "from the latest left-side bubble (bottom-most text only, no quoted context)."
                    ),
                },
                "detected_archetype": {
                    "type": "STRING",
                    "enum": [
                        "THE BANTER GIRL",
                        "THE INTELLECTUAL",
                        "THE SOFT/TRADITIONAL",
                        "THE LOW-INVESTMENT",
                    ],
                    "description": (
                        "High-level persona label inferred from her texting style and "
                        "ACTUAL new message, not the user's. Exactly one of the defined archetypes."
                    ),
                },
                "archetype_reasoning": {
                    "type": "STRING",
                    "description": (
                        "One short sentence explaining WHY you chose that archetype, "
                        "grounded in her actual new message and recent behavior."
                    ),
                },
            },
            "required": [
                "detected_language_and_vibe",
                "detected_dialect",
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
                "their_actual_new_message",
                "detected_archetype",
                "archetype_reasoning",
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
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {
                        "type": "STRING",
                        "description": "The reply string to show the user.",
                    },
                    "strategy_label": {
                        "type": "STRING",
                        "enum": [
                            "PUSH-PULL",
                            "FRAME CONTROL",
                            "SOFT CLOSE",
                            "VALUE ANCHOR",
                            "PATTERN INTERRUPT",
                        ],
                        "description": "High-level strategy tag describing what this reply is doing.",
                    },
                    "is_recommended": {
                        "type": "BOOLEAN",
                        "description": (
                            "Exactly ONE reply in the array must have is_recommended=true. "
                            "That reply is the Wingman's Choice — the most high-status, "
                            "context-aware option."
                        ),
                    },
                    "coach_reasoning": {
                        "type": "STRING",
                        "description": (
                            "One-sentence explanation of the psychology, cultural reference, "
                            "or dating context behind this reply (e.g., explaining an Indian "
                            "TV reference like Byomkesh Bakshi)."
                        ),
                    },
                },
                "required": [
                    "text",
                    "strategy_label",
                    "is_recommended",
                    "coach_reasoning",
                ],
            },
            "description": (
                "Exactly 4 distinct reply objects. Each must include a strategy_label, "
                "an is_recommended flag, and a one-sentence coach_reasoning. "
                "STRICT RULE: exactly ONE reply must have is_recommended=true "
                "(the Wingman's Choice)."
            ),
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


# ---------- Hybrid Stitch OCR extraction (v1-specific Gemini call) ----------


async def _extract_hybrid_stitch_ocr_signals(*, image_base64: str) -> tuple[str, list[str]]:
    """
    Extract:
    - person_name: other person's visible name (or "unknown")
    - extracted_texts: last few bubble messages (verbatim OCR-ish)
    """

    OCR_SIGNALS_SCHEMA: dict = {
        "type": "OBJECT",
        "properties": {
            "person_name": {"type": "STRING"},
            "extracted_bubbles": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "sender": {
                            "type": "STRING",
                            "description": "Either 'them' (left-aligned) or 'user' (right-aligned).",
                        },
                        "text": {
                            "type": "STRING",
                            "description": "ACTUAL NEW MESSAGE TEXT only; no quoted/indented boxes; verbatim.",
                        },
                    },
                    "required": ["sender", "text"],
                },
            },
        },
        "required": ["person_name", "extracted_bubbles"],
    }

    client = _get_client()
    system_prompt = (
        "You are a strict OCR extractor for a dating app screenshot. "
        "Return valid JSON only.\n\n"
        "Extract:\n"
        "1) person_name: the visible first name of the other person. If not clearly visible, return 'unknown'.\n"
        "2) extracted_bubbles: the last 4-6 visible chat bubbles, in chronological order. For each bubble:\n"
        "- Determine sender by alignment: left-aligned = 'them', right-aligned = 'user'.\n"
        "- Extract ONLY the ACTUAL new message text (the bottom-most text in the bubble). "
        "Ignore any quoted/indented boxes.\n"
        "- Extract VERBATIM: do not translate or paraphrase.\n"
        "If any bubble text is unreadable, return an empty string for that bubble's text.\n"
    )

    user_prompt = "Extract person_name and extracted_bubbles from this screenshot."

    try:
        raw = await client.vision_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            base64_images=[image_base64],
            temperature=0.1,
            model=settings.gemini_model,
            max_output_tokens=800,
            response_schema=OCR_SIGNALS_SCHEMA,
        )
        parsed = json.loads(raw)
        person_name = str(parsed.get("person_name") or "unknown")
        bubbles = parsed.get("extracted_bubbles") or []
        extracted_texts: list[str] = []
        for b in bubbles:
            if not isinstance(b, dict):
                continue
            t = b.get("text")
            if isinstance(t, str):
                t = t.strip()
                if t:
                    extracted_texts.append(t)
        return person_name, extracted_texts
    except Exception as e:  # pragma: no cover - defensive
        logger.error("hybrid_stitch_ocr_extraction_failed", error=str(e))
        return "unknown", []


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
                    "(usually on the right side in blue or green). Ignore the other person's text. "
                    "Extract text VERBATIM with no translation: if the message is in Hindi, "
                    "Devanagari script, or Romanized Hinglish, keep it exactly as shown on screen."
                ),
            }
        },
        "required": ["user_messages"],
    }

    client = _get_client()
    system_prompt = (
        "You are a data extractor. Read the screenshot and extract the exact text of "
        "the messages sent by the user. CRITICAL: Extract all text VERBATIM. If the "
        "text is in Hindi, Devanagari script, or Romanized Hinglish (e.g., 'kya kar rahe ho'), "
        "DO NOT translate it to English. Extract the exact letters on the screen."
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


@router.post("/vision/generate", response_model=VisionResponse | RequiresUserConfirmation)
async def generate_replies(
    request: VisionRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisionResponse | RequiresUserConfirmation:
    """Analyze screenshot and generate 4 reply suggestions."""
    # 1. Resolve tier and feature config
    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])

    # 2. Resolve images (support both `image` and `images` fields)
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
    max_screenshots = tier_config["limits"]["max_screenshots_per_request"]
    if len(images) > max_screenshots:
        images = images[-max_screenshots:]  # keep most recent

    # 5. Validate direction against tier's allowed directions
    allowed_directions = tier_config["features"]["allowed_ui_directions"]
    if request.direction.value not in allowed_directions:
        raise HTTPException(
            status_code=403,
            detail="This chat direction is locked for your current plan. Please upgrade.",
        )

    # 6. Strip custom hint if tier doesn't support it, and enforce max length
    max_hint_chars = tier_config["limits"]["max_custom_hint_chars"]
    if not tier_config["features"]["custom_hints_enabled"]:
        custom_hint = None
    elif request.custom_hint and len(request.custom_hint) > max_hint_chars:
        # Truncate if over limit
        custom_hint = request.custom_hint[:max_hint_chars]
    else:
        custom_hint = request.custom_hint

    effective_conversation_id = request.conversation_id
    new_conversation_person_name: str | None = None

    # 7. Hybrid Stitch resolution: decide which conversation_id to use.
    # This MUST happen before any LangGraph agent nodes run.
    if not effective_conversation_id:
        ocr_person_name, extracted_texts = await _extract_hybrid_stitch_ocr_signals(
            image_base64=images[-1]
        )

        # Use the shared composite-scoring stitch resolver
        outcome, matched_conversation_id, payload = (
            await resolve_hybrid_stitch_conversation_id(
                user_id=user.id,
                ocr_person_name=ocr_person_name,
                extracted_texts=extracted_texts,
                db=db,
            )
        )

        if outcome == "requires_user_confirmation" and payload:
            matched_id = matched_conversation_id or ""

            # Concurrency Lock: another request already created a pending resolution.
            if matched_id and await has_pending_hybrid_resolution(
                db=db, user_id=user.id, suggested_conversation_id=matched_id
            ):
                logger.warning(
                    "hybrid_stitch_processing_lock",
                    user_id=user.id,
                    locked_conversation_id=matched_id,
                )

            conflict_reason = "hybrid_stitch_ambiguity"
            payload["detail"] = f"409 requires user confirmation. reason={conflict_reason}"

            await store_pending_hybrid_resolution(
                db=db,
                user_id=user.id,
                suggested_conversation_id=matched_id,
                images=images,
                direction=request.direction.value,
                custom_hint=custom_hint,
                extracted_person_name=ocr_person_name,
                conflict_reason=conflict_reason,
                conflict_detail=payload.get("detail"),
            )
            return JSONResponse(status_code=409, content=payload)

        if outcome == "auto_stitch" and matched_conversation_id:
            effective_conversation_id = matched_conversation_id
        elif outcome == "new_match":
            new_conversation_person_name = ocr_person_name

    # 8. Check daily/weekly rate limits via QuotaManager (0 = unlimited).
    # Check-only here — we increment after the agent succeeds so errors don't cost the user.
    daily_limit = tier_config["limits"]["chat_generations_per_day"]
    effective_limit = daily_limit + user.bonus_replies

    daily_used = 0
    quota_manager: QuotaManager | None = None
    if user.google_provider_id:
        quota_manager = QuotaManager(db)
        try:
            await quota_manager.check_only(
                user.google_provider_id,
                daily_limit=effective_limit,
                weekly_limit=None,
            )
        except QuotaExceededException:
            raise HTTPException(
                status_code=429,
                detail="Daily limit reached. Upgrade to Premium for more replies.",
            )

    # 9. Load Voice DNA only if tier supports it
    voice_dna = None
    if tier_config["features"]["voice_dna_enabled"]:
        result = await db.execute(
            select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
        )
        voice_db = result.scalar_one_or_none()
        if voice_db and voice_db.sample_count >= 8:
            voice_dna = await voice_to_domain(voice_db, db)

    # 10. Load conversation context only if tier supports memory.
    # If Hybrid Stitch decided "new match", create the conversation now (after quota checks).
    conversation_context = None
    convo = None
    if effective_conversation_id is None and new_conversation_person_name is not None:
        # Singleton active conversation per user:
        # Deactivate any previously-active conversation before starting the new one.
        await db.execute(
            text(
                "UPDATE conversations SET is_active = false "
                "WHERE user_id = :user_id AND is_active = true"
            ),
            {"user_id": user.id},
        )
        convo = Conversation(
            user_id=user.id, person_name=new_conversation_person_name, is_active=True
        )
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        effective_conversation_id = convo.id

    if (
        tier_config["features"]["chemistry_tracking_enabled"]
        and effective_conversation_id
    ):
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == effective_conversation_id,
                Conversation.user_id == user.id,
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo and convo.is_active:
            conversation_context = await build_conversation_context(convo, db)

    # 9. Run LangGraph agent (bouncer -> analyst -> strategist -> writer -> auditor) or legacy Gemini path
    parsed = None
    user_organic_text = None
    # Default temperature used for persistence when the agent path is taken.
    llm_temperature = 0.7
    start = time.monotonic()
    use_agent = True

    if use_agent:
        initial_state = _build_agent_initial_state(
            images[0],
            request.direction.value,
            custom_hint or "",
            user.id,
            effective_conversation_id,
            voice_dna,
            conversation_context,
        )
        try:
            final_state = await _run_agent(initial_state)
        except Exception as e:
            logger.error("agent_run_failed", error=str(e), user_id=user.id)
            raise HTTPException(
                status_code=502,
                detail="Failed to generate replies. Try again.",
            ) from e
        if not final_state.get("is_valid_chat", True):
            raise HTTPException(
                status_code=400,
                detail=final_state.get(
                    "bouncer_reason",
                    "Image is not a valid chat or dating app screenshot.",
                ),
            )
        parsed = _parsed_from_agent_state(final_state)
        # Extract user's last message from transcript for persistence (legacy path does this in its try block)
        if parsed and parsed.visual_transcript:
            for msg in reversed(parsed.visual_transcript):
                if getattr(msg, "side", "").lower() == "right" or getattr(msg, "sender", "").lower() == "user":
                    user_organic_text = msg.actual_new_message
                    break

    if parsed is None:
        # Legacy path: build prompt and call Gemini directly
        payload = prompt_engine.build(
            direction=request.direction.value,
            custom_hint=custom_hint,
            voice_dna=voice_dna,
            conversation_context=conversation_context,
            variant_id="default",
        )

        # 9a. Context Threading: inject RECENT HISTORY from the last N interactions
        # for this specific person into the system prompt so the model can maintain
        # dialect and vibe continuity.
        if conversation_context and conversation_context.person_name != "unknown":
            recent_history_block = ""
            try:
                max_context_messages = tier_config["limits"]["max_context_messages"]
                history_result = await db.execute(
                    select(Interaction)
                    .where(
                        Interaction.user_id == user.id,
                        Interaction.person_name == conversation_context.person_name,
                    )
                    .order_by(Interaction.created_at.desc())
                    .limit(max_context_messages)
                )
                history_items = history_result.scalars().all()

                # Build a compact text block focusing on how the user actually types.
                lines: list[str] = []
                for interaction in reversed(history_items):
                    if interaction.user_organic_text:
                        lines.append(interaction.user_organic_text)

                if lines:
                    recent_history_block = (
                        "\n\n══════════════════════════════════════\n"
                        "RECENT HISTORY (user's texting style — maintain this dialect)\n"
                        "══════════════════════════════════════\n"
                    )
                    for idx, msg in enumerate(lines, start=1):
                        truncated = msg if len(msg) <= 160 else msg[:157] + "..."
                        recent_history_block += f"{idx}. {truncated}\n"
            except Exception as e:  # pragma: no cover - defensive logging only
                logger.warning(
                    "recent_history_injection_failed",
                    error=str(e),
                    user_id=user.id,
                )
                recent_history_block = ""

            if recent_history_block:
                payload.system_prompt = f"{payload.system_prompt}{recent_history_block}"

        # 10. Dynamic temperature routing + call Gemini with retry on JSON truncation
        client = _get_client()
        start = time.monotonic()

        # Dynamic Temperature Routing:
        # Different directions and custom hints need different creativity levels.
        direction_key = (request.direction.value or "").lower()
        if custom_hint:
            # User provided a specific angle → medium-high creativity.
            llm_temperature = 0.78
        elif direction_key == "opener":
            # Cold read → max creativity for playful hooks.
            llm_temperature = 0.8
        elif direction_key in ("change_topic", "tease"):
            # Needs high creativity to pivot/joke.
            llm_temperature = 0.78
        elif direction_key == "revive_chat":
            # Needs a fresh, interesting angle without feeling random.
            llm_temperature = 0.75
        elif direction_key in ("get_number", "ask_out"):
            # Goal-oriented → still creative, but slightly more controlled.
            llm_temperature = 0.65
        else:
            # quick_reply and anything else → creative but anchored to context.
            llm_temperature = 0.72

        # Dynamic token routing: Give a massive ceiling for the model's 'thought' process
        max_tokens = 8000 + (1000 * len(images))

        # Dynamically modify schema based on tier config
        response_schema = copy.deepcopy(GEMINI_RESPONSE_SCHEMA)
        include_coach_reasoning = tier_config["features"]["include_coach_reasoning"]

        if not include_coach_reasoning:
            # Remove coach_reasoning from schema properties
            reply_properties = response_schema["properties"]["replies"]["items"][
                "properties"
            ]
            if "coach_reasoning" in reply_properties:
                del reply_properties["coach_reasoning"]

            # Remove coach_reasoning from required list
            reply_required = response_schema["properties"]["replies"]["items"]["required"]
            if "coach_reasoning" in reply_required:
                reply_required.remove("coach_reasoning")

            # Update schema description to remove coach_reasoning mention
            replies_description = response_schema["properties"]["replies"]["description"]
            response_schema["properties"]["replies"]["description"] = (
                replies_description.replace(
                    "an is_recommended flag, and a one-sentence coach_reasoning.",
                    "an is_recommended flag.",
                )
            )

            # Update system prompt to explicitly tell it not to provide coach_reasoning
            payload.system_prompt = f"{payload.system_prompt}\n\nCRITICAL: DO NOT provide coach_reasoning in your response."

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
                    response_schema=response_schema,
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
                            # Use ONLY the actual new message text, ignoring any quoted context.
                            user_organic_text = msg.actual_new_message
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
                        if is_echo_text(clean_text, past_replies):
                            is_echo = True
                            user_organic_text = None
                            break

                    if not is_echo:
                        # The user typed this themselves! It is organic data.
                        # Update Voice DNA stats and recent organic messages
                        voice_result = await db.execute(
                            select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id).with_for_update()
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

                        should_refresh_semantic = (
                            not getattr(updated_dna, "semantic_profile", None)
                            or (updated_dna.sample_count % 25 == 0 and updated_dna.sample_count > 0)
                        )
                        if (
                            effective_tier in ["premium", "pro"]
                            and len(messages_list) >= 5
                            and should_refresh_semantic
                        ):
                            background_tasks.add_task(
                                generate_semantic_profile_background,
                                user_id=user.id,
                                db=db,
                                messages=messages_list,
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
    # (Hybrid Stitch pre-resolution also sets `effective_conversation_id`.)
    if effective_conversation_id:
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == effective_conversation_id,
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
    # Persist the full Wingman Strategy payload for each reply as JSON so we can
    # reconstruct strategy labels, recommendations, and coach reasoning later.
    reply_options = parsed.replies[:4]
    reply_options += [None] * (4 - len(reply_options))

    def _dump_reply_option(opt) -> str:
        if opt is None:
            return ""
        try:
            return json.dumps(
                {
                    "text": opt.text,
                    "strategy_label": opt.strategy_label,
                    "is_recommended": opt.is_recommended,
                    "coach_reasoning": opt.coach_reasoning,
                },
                ensure_ascii=False,
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("reply_option_serialize_failed", error=str(e))
            # Fallback to just the text so we never break the pipeline.
            return opt.text

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
        direction=request.direction.value,
        custom_hint=custom_hint,
        their_last_message=parsed.analysis.their_last_message,
        their_tone=their_tone,
        their_effort=their_effort,
        conversation_temperature=conversation_temperature,
        detected_stage=detected_stage,
        person_name=parsed.analysis.person_name,
        key_detail=parsed.analysis.key_detail,
        user_organic_text=user_organic_text,
        reply_0=_dump_reply_option(reply_options[0]),
        reply_1=_dump_reply_option(reply_options[1]),
        reply_2=_dump_reply_option(reply_options[2]),
        reply_3=_dump_reply_option(reply_options[3]),
        llm_model=settings.gemini_model,
        prompt_variant="default",
        temperature_used=llm_temperature,
        screenshot_count=len(images),
        latency_ms=latency_ms,
    )
    # Increment quota now that we have a successful reply to return.
    if quota_manager and user.google_provider_id:
        daily_used, _ = await quota_manager.increment(user.google_provider_id)

    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    if daily_limit > 0:
        remaining = max(0, effective_limit - daily_used)
    else:
        remaining = 9999

    reply_payloads: list[ReplyOptionPayload] = []
    for opt in parsed.replies[:4]:
        reply_payloads.append(
            ReplyOptionPayload(
                text=opt.text,
                strategy_label=opt.strategy_label,
                is_recommended=opt.is_recommended,
                coach_reasoning=opt.coach_reasoning,
            )
        )

    return VisionResponse(
        replies=reply_payloads,
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
