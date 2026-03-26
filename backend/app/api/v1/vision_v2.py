"""
V2 reply generation endpoint — 2-node agent (vision_node + generator_node).

Route: POST /api/v1/vision/generate_v2

Node 1 (vision_node)    : GEMINI_MODEL — bouncer + OCR + analysis in one call
Node 2 (generator_node) : GEMINI_MODEL — strategy + write + self-audit in one call

Primary reply generation endpoint (v2 agent):
  - Tier config enforcement (direction guard, screenshot limit, custom hint, coach_reasoning gate)
  - Hybrid Stitch conversation resolution (auto-stitch, 409 requires-confirmation, new match)
  - Quota check-before / increment-after pattern
  - Voice DNA (when enabled): organic text extraction + echo filter + stats update
  - Full Interaction persistence (all reply fields, latency, model, temperature)
  - Correct VisionResponse with interaction_id, usage_remaining, conversation_id, person_name, stage
"""

from __future__ import annotations

import asyncio
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    RequiresUserConfirmation,
    VisionRequest,
    VisionResponse,
)
from app.api.v1.vision_agent_state import (
    _build_agent_initial_state,
    _parsed_from_agent_state,
)
from app.api.v1.vision_shared import (
    build_vision_response,
    extract_organic_text,
    persist_interaction,
    resolve_hybrid_stitch_conversation_id,
    update_voice_dna,
)
from app.config import settings
from app.core.tier_config import TIER_CONFIG, voice_dna_feature_active
from app.domain.conversation import build_conversation_context
from app.domain.tiers import get_effective_tier
from app.domain.voice_dna import to_domain as voice_to_domain
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import Conversation, User, UserVoiceDNA
from app.llm.gemini_client import GeminiClient
from app.services.hybrid_stitch_pending import (
    has_pending_hybrid_resolution,
    store_pending_hybrid_resolution,
)
from app.services.memory_service import scrub_lore_from_contradictions
from app.services.quota_manager import QuotaExceededException, QuotaManager

router = APIRouter()
logger = structlog.get_logger(__name__)

_gemini_client: GeminiClient | None = None


def _get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient(
            api_key=settings.gemini_api_key, default_model=settings.gemini_model
        )
    return _gemini_client


# ---------------------------------------------------------------------------
# Hybrid Stitch OCR signals (lightweight pre-agent Gemini call)
# ---------------------------------------------------------------------------

async def _extract_ocr_signals(
    image_base64: str,
    usage_sink: list[dict] | None = None,
) -> tuple[str, list[str]]:
    """Quick Gemini call to extract person_name + last bubble texts for conversation stitching."""
    OCR_SIGNALS_SCHEMA: dict = {
        "type": "OBJECT",
        "properties": {
            "person_name": {"type": "STRING"},
            "extracted_bubbles": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "sender": {"type": "STRING"},
                        "text": {"type": "STRING"},
                    },
                    "required": ["sender", "text"],
                },
            },
        },
        "required": ["person_name", "extracted_bubbles"],
    }

    system_prompt = (
        "You are a strict OCR extractor for a dating app screenshot. Return valid JSON only.\n"
        "1) person_name: visible first name of the other person, or 'unknown'.\n"
        "2) extracted_bubbles: last 4-6 bubbles in order. sender: left='them', right='user'. "
        "text: ACTUAL new message only, verbatim, no quoted blocks, no translation."
    )

    try:
        client = _get_gemini_client()
        raw = await client.vision_generate(
            system_prompt=system_prompt,
            user_prompt="Extract person_name and extracted_bubbles from this screenshot.",
            base64_images=[image_base64],
            temperature=0.1,
            model=settings.gemini_model,
            max_output_tokens=800,
            response_schema=OCR_SIGNALS_SCHEMA,
            usage_sink=usage_sink,
            usage_phase="v2_hybrid_stitch_ocr",
        )
        data = __import__("json").loads(raw)
        person_name = str(data.get("person_name") or "unknown")
        extracted_texts = [
            b["text"].strip()
            for b in (data.get("extracted_bubbles") or [])
            if isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"].strip()
        ]
        logger.info(
            "llm_lifecycle",
            stage="v2_pre_agent_ocr_signals",
            person_name=person_name,
            extracted_bubble_text_count=len(extracted_texts),
        )
        return person_name, extracted_texts
    except Exception as e:
        logger.error("v2_hybrid_stitch_ocr_failed", error=str(e))
        return "unknown", []


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

def _run_v2_agent_sync(initial_state: dict) -> dict:
    from agent.graph_v2 import rizz_agent_v2
    return rizz_agent_v2.invoke(initial_state)


async def _run_v2_agent(initial_state: dict) -> dict:
    return await asyncio.to_thread(_run_v2_agent_sync, initial_state)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/vision/generate_v2", response_model=VisionResponse | RequiresUserConfirmation)
async def generate_replies_v2(
    request: VisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisionResponse | RequiresUserConfirmation:
    """
    Analyze a chat screenshot and generate 4 reply suggestions using the 2-node agent.
    Analyze a chat screenshot and generate 4 reply suggestions (v2 pipeline).
    """

    # ------------------------------------------------------------------ #
    # 1. Tier config
    # ------------------------------------------------------------------ #
    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])

    # ------------------------------------------------------------------ #
    # 2. Resolve + clamp images
    # ------------------------------------------------------------------ #
    images: list[str] = request.images or ([request.image] if request.image else [])
    if not images:
        raise HTTPException(status_code=400, detail="At least one screenshot is required.")
    max_screenshots = tier_config["limits"]["max_screenshots_per_request"]
    if len(images) > max_screenshots:
        images = images[-max_screenshots:]

    # ------------------------------------------------------------------ #
    # 3. Direction guard
    # ------------------------------------------------------------------ #
    allowed_directions = tier_config["features"]["allowed_ui_directions"]
    if request.direction.value not in allowed_directions:
        raise HTTPException(
            status_code=403,
            detail="This chat direction is locked for your current plan. Please upgrade.",
        )

    # ------------------------------------------------------------------ #
    # 4. Custom hint — strip or clamp per tier
    # ------------------------------------------------------------------ #
    max_hint_chars = tier_config["limits"]["max_custom_hint_chars"]
    if not tier_config["features"]["custom_hints_enabled"]:
        custom_hint: str | None = None
    elif request.custom_hint and len(request.custom_hint) > max_hint_chars:
        custom_hint = request.custom_hint[:max_hint_chars]
    else:
        custom_hint = request.custom_hint

    logger.info(
        "llm_lifecycle",
        stage="v2_request_begin",
        endpoint="generate_v2",
        user_id=user.id,
        tier=str(effective_tier),
        direction=request.direction.value,
        screenshot_count=len(images),
        conversation_id_supplied=bool(request.conversation_id),
        has_custom_hint=bool(custom_hint),
    )

    # ------------------------------------------------------------------ #
    # 5. Hybrid Stitch: resolve conversation_id before agent runs
    # ------------------------------------------------------------------ #
    effective_conversation_id = request.conversation_id
    new_conversation_person_name: str | None = None
    extracted_texts: list[str] = []
    pre_agent_usage: list[dict] = []

    if not effective_conversation_id:
        ocr_person_name, extracted_texts = await _extract_ocr_signals(
            images[-1], usage_sink=pre_agent_usage
        )

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

            # Concurrency lock check (DB-backed)
            if matched_id and await has_pending_hybrid_resolution(
                db=db, user_id=user.id, suggested_conversation_id=matched_id
            ):
                logger.warning(
                    "v2_hybrid_stitch_processing_lock",
                    user_id=user.id,
                    locked_conversation_id=matched_id,
                )

            conflict_reason = "hybrid_stitch_ambiguity"
            payload["detail"] = f"409 requires user confirmation. reason={conflict_reason}"

            suggested = payload.get("suggested_match", {})
            logger.warning(
                "v2_hybrid_stitch_409",
                user_id=user.id,
                suggested_person_name=suggested.get("person_name"),
                suggested_conversation_id=suggested.get("conversation_id"),
                match_confidence=payload.get("match_confidence"),
            )

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
            logger.info(
                "llm_lifecycle",
                stage="v2_hybrid_stitch_requires_confirmation",
                user_id=user.id,
                outcome="requires_user_confirmation",
                ocr_person_name=ocr_person_name,
                suggested_conversation_id=matched_id,
            )
            return JSONResponse(status_code=409, content=payload)

        if outcome == "auto_stitch" and matched_conversation_id:
            effective_conversation_id = matched_conversation_id
        elif outcome == "new_match":
            new_conversation_person_name = ocr_person_name

        logger.info(
            "llm_lifecycle",
            stage="v2_hybrid_stitch",
            user_id=user.id,
            outcome=outcome,
            ocr_person_name=ocr_person_name,
            extracted_bubble_text_count=len(extracted_texts),
            effective_conversation_id=effective_conversation_id or "",
            new_match_person=new_conversation_person_name or "",
        )
    else:
        logger.info(
            "llm_lifecycle",
            stage="v2_hybrid_stitch",
            user_id=user.id,
            outcome="skipped_client_conversation_id",
            effective_conversation_id=effective_conversation_id or "",
        )

    # ------------------------------------------------------------------ #
    # 6. Quota: check-only before running the expensive agent
    # ------------------------------------------------------------------ #
    daily_limit = tier_config["limits"]["chat_generations_per_day"]
    effective_limit = daily_limit + user.bonus_replies
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

    logger.info(
        "llm_lifecycle",
        stage="v2_quota_checked",
        user_id=user.id,
        google_quota_enforced=bool(quota_manager),
        daily_limit=daily_limit,
        effective_limit=effective_limit,
    )

    # ------------------------------------------------------------------ #
    # 7. Voice DNA — load if tier supports it
    # ------------------------------------------------------------------ #
    voice_dna = None
    if voice_dna_feature_active(tier_config):
        voice_result = await db.execute(
            select(UserVoiceDNA).where(UserVoiceDNA.user_id == user.id)
        )
        voice_db = voice_result.scalar_one_or_none()
        if voice_db and voice_db.sample_count >= 8:
            voice_dna = await voice_to_domain(voice_db, db)

    # ------------------------------------------------------------------ #
    # 8. Conversation context — create new conversation if needed
    # ------------------------------------------------------------------ #
    conversation_context = None
    convo = None
    # Track if we created a placeholder conversation before the bouncer finishes.
    # If the bouncer rejects the screenshot (`is_valid_chat=false`), we will deactivate
    # the placeholder so it doesn't get matched later.
    placeholder_conversation_id: str | None = None

    if effective_conversation_id is None and new_conversation_person_name is not None:
        convo = Conversation(
            user_id=user.id, person_name=new_conversation_person_name, is_active=True
        )
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        effective_conversation_id = convo.id
        placeholder_conversation_id = convo.id

    if tier_config["features"]["chemistry_tracking_enabled"] and effective_conversation_id:
        convo_result = await db.execute(
            select(Conversation).where(
                Conversation.id == effective_conversation_id,
                Conversation.user_id == user.id,
            )
        )
        convo = convo_result.scalar_one_or_none()
        if convo and convo.is_active:
            conversation_context = await build_conversation_context(convo, db)

    logger.info(
        "llm_lifecycle",
        stage="v2_context_ready",
        user_id=user.id,
        conversation_id=effective_conversation_id or "",
        voice_dna_loaded=voice_dna is not None,
        chemistry_context_loaded=conversation_context is not None,
        interaction_count=(
            getattr(conversation_context, "interaction_count", 0)
            if conversation_context
            else 0
        ),
    )

    # ------------------------------------------------------------------ #
    # 9. Build initial state and run the 2-node agent
    # ------------------------------------------------------------------ #
    start = time.monotonic()
    initial_state = _build_agent_initial_state(
        images[0],
        request.direction.value,
        custom_hint or "",
        user.id,
        effective_conversation_id,
        voice_dna,
        conversation_context,
    )
    trace_id = initial_state.get("trace_id", "")
    # Pass OCR text so vision_node can use it for semantic memory search
    initial_state["ocr_hint_text"] = " ".join(extracted_texts[-2:]) if extracted_texts else ""

    logger.info(
        "llm_lifecycle",
        stage="v2_agent_run_start",
        trace_id=trace_id,
        user_id=user.id,
        conversation_id=effective_conversation_id or "",
        ocr_hint_chars=len(initial_state["ocr_hint_text"] or ""),
    )

    try:
        final_state = await _run_v2_agent(initial_state)
    except Exception as e:
        logger.error(
            "agent_v2_run_failed",
            trace_id=trace_id,
            error=str(e),
            user_id=user.id,
            conversation_id=effective_conversation_id or "",
        )
        raise HTTPException(status_code=502, detail="Failed to generate replies. Try again.") from e

    if not final_state.get("is_valid_chat", True):
        # Roll back placeholder conversation on bouncer rejection.
        # This prevents empty "link chats" / matches based on placeholder rows.
        if placeholder_conversation_id and effective_conversation_id == placeholder_conversation_id:
            try:
                # Re-fetch to ensure the instance is attached to this session state.
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
                # Never mask the original bouncer error; best-effort cleanup only.
                logger.warning(
                    "v2_placeholder_convo_rollback_failed",
                    user_id=user.id,
                    placeholder_conversation_id=placeholder_conversation_id,
                    exc_info=True,
                )

        raise HTTPException(
            status_code=400,
            detail=final_state.get("bouncer_reason", "Image is not a valid chat or dating app screenshot."),
        )

    latency_ms = int((time.monotonic() - start) * 1000)
    usage_log = final_state.get("gemini_usage_log") or []
    gemini_call_count = len(usage_log) if isinstance(usage_log, list) else 0
    detected_contradictions = final_state.get("detected_contradictions") or []
    if (
        isinstance(detected_contradictions, list)
        and detected_contradictions
        and effective_conversation_id
    ):
        scrub_result = await scrub_lore_from_contradictions(
            db,
            user_id=user.id,
            conversation_id=effective_conversation_id,
            contradictions=[str(c) for c in detected_contradictions if str(c).strip()],
        )
        logger.warning(
            "llm_lifecycle",
            stage="v2_lore_memory_scrub",
            trace_id=trace_id,
            user_id=user.id,
            conversation_id=effective_conversation_id,
            contradiction_count=len(detected_contradictions),
            scrub_updated=bool(scrub_result.get("updated", False)),
            scrub_removed_lines=int(scrub_result.get("removed_lines", 0)),
        )
    logger.info(
        "llm_lifecycle",
        stage="v2_agent_run_complete",
        trace_id=trace_id,
        user_id=user.id,
        latency_ms=latency_ms,
        is_valid_chat=bool(final_state.get("is_valid_chat", True)),
        gemini_call_count=gemini_call_count,
        contradiction_count=(
            len(detected_contradictions)
            if isinstance(detected_contradictions, list)
            else 0
        ),
    )
    parsed = _parsed_from_agent_state(final_state)

    # Deterministic style post-processing — strip punctuation, force lowercase
    from agent.nodes_v2 import _post_process_replies as _pp
    from agent.state import WriterOutput as _WO, ReplyOption as _RO
    _tmp_replies = [_RO(text=r.text, strategy_label=r.strategy_label, is_recommended=r.is_recommended, coach_reasoning=r.coach_reasoning) for r in parsed.replies]
    _cleaned = _pp(_WO(replies=_tmp_replies))
    from app.domain.models import ReplyOption as DomainReply
    from dataclasses import replace as _replace
    parsed.replies = [_replace(r, text=c.text) for r, c in zip(parsed.replies, _cleaned.replies)]

    # ------------------------------------------------------------------ #
    # 10. Voice DNA: extract organic text, run echo filter, update stats
    # ------------------------------------------------------------------ #
    organic_text = await extract_organic_text(db=db, user=user, parsed=parsed, conversation_id=effective_conversation_id)
    if organic_text and voice_dna_feature_active(tier_config):
        await update_voice_dna(
            db=db,
            user=user,
            organic_text=organic_text,
        )

    # ------------------------------------------------------------------ #
    # 11. Persist interaction (conversation resolve + Interaction row)
    # ------------------------------------------------------------------ #
    convo, interaction = await persist_interaction(
        db=db,
        parsed=parsed,
        user=user,
        effective_conversation_id=effective_conversation_id,
        direction=request.direction.value,
        custom_hint=custom_hint,
        user_organic_text=organic_text,
        llm_model=settings.gemini_model,
        llm_temperature=0.7,
        latency_ms=latency_ms,
        screenshot_count=len(images),
        prompt_variant="v2_2node",
    )

    logger.info(
        "llm_lifecycle",
        stage="v2_persist_complete",
        trace_id=trace_id,
        user_id=user.id,
        interaction_id=interaction.id,
        conversation_id=convo.id if convo else "",
        person_name=parsed.analysis.person_name if parsed else "",
        detected_stage=parsed.analysis.stage if parsed else "",
    )

    # ------------------------------------------------------------------ #
    # 12. Increment quota now that we have a successful result
    # ------------------------------------------------------------------ #
    daily_used = 0
    if quota_manager and user.google_provider_id:
        daily_used, _ = await quota_manager.increment(user.google_provider_id)
        await db.commit()

    # ------------------------------------------------------------------ #
    # 13. Build and return response
    # ------------------------------------------------------------------ #
    response = build_vision_response(
        parsed=parsed,
        interaction=interaction,
        convo=convo,
        daily_limit=daily_limit,
        effective_limit=effective_limit,
        daily_used=daily_used,
    )
    # Full response observability (what the client receives).
    logger.info(
        "v2_response_full",
        trace_id=trace_id,
        user_id=user.id,
        interaction_id=interaction.id,
        conversation_id=response.conversation_id,
        person_name=response.person_name,
        stage=response.stage,
        replies=[
            {
                "text": r.text,
                "strategy_label": r.strategy_label,
                "is_recommended": r.is_recommended,
                "coach_reasoning": r.coach_reasoning,
            }
            for r in (response.replies or [])
        ],
        usage_remaining=response.usage_remaining,
    )
    logger.info(
        "llm_lifecycle",
        stage="v2_response_ready",
        trace_id=trace_id,
        user_id=user.id,
        interaction_id=interaction.id,
        usage_remaining=response.usage_remaining,
    )
    return response
