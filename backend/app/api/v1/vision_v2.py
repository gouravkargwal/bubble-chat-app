from __future__ import annotations

import asyncio
import contextvars
import time
from typing import cast

import httpx
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
from app.services.hybrid_stitch_pending import (
    has_pending_hybrid_resolution,
    store_pending_hybrid_resolution,
)
from app.services.memory_service import scrub_lore_from_contradictions
from app.services.quota_manager import QuotaExceededException, QuotaManager
from agent.nodes_v2._lc_usage import invoke_structured_gemini
from agent.nodes_v2._shared import (
    VISION_MODEL,
    encode_image_from_state,
    sanitize_llm_messages_for_logging,
    fetch_librarian_context_async,
)
from agent.nodes_v2._vision import VisionNodeOutput
from agent.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage

router = APIRouter()
logger = structlog.get_logger(__name__)
_vision_usage_row_var: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "vision_usage_row", default=None
)


def _is_transient_provider_overload(exc: BaseException) -> bool:
    """Best-effort check for upstream LLM capacity errors (Gemini 503/UNAVAILABLE)."""
    tokens = ("503", "UNAVAILABLE", "high demand", "RESOURCE_EXHAUSTED")
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        text = str(cur)
        if any(token in text for token in tokens):
            return True
        cur = cast(BaseException | None, cur.__cause__ or cur.__context__)
    return False


def _is_provider_timeout(exc: BaseException) -> bool:
    """Detect upstream read timeouts across wrapped exception chains."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, (httpx.ReadTimeout, TimeoutError)):
            return True
        cur = cast(BaseException | None, cur.__cause__ or cur.__context__)
    return False


# Vision system prompt: Steps 1–2 are shared; Step 3 branches on request direction (see
# `build_vision_system_prompt`). Copied pattern supports the v2 endpoint vision call before
# hybrid stitching.

_VISION_SYSTEM_PROMPT_STEPS_1_2 = """
You are a chat/profile screenshot analyzer. Process the image(s) strictly in 3 sequential steps. Output a complete JSON object.

STEP 1: VALIDATION
Determine if the image(s) are valid.
* is_valid_chat: true ONLY IF the image(s) show a chat conversation OR dating app profile (same thread across multiple screenshots counts as one valid chat). Else false (e.g., random photos, menus).
* bouncer_reason: Brief reason for your boolean decision.
* Stop here and return empty arrays/null for all other fields if is_valid_chat is false.

STEP 2: OCR EXTRACTION
If valid, extract verbatim text. Do not translate/summarize. Ignore text input bars.
* Dating Profiles (no chat bubbles): Extract all visible profile text into a single raw_ocr_text object: sender="them", actual_new_message=all extracted text joined by newlines, quoted_context=null, is_reply=false. Skip to Step 3.
* Chat Conversations:
    SENDER IDENTIFICATION — use the avatar as your primary anchor. Follow every step in order.

    !! COLOR AND ALIGNMENT ARE UNRELIABLE — DO NOT USE THEM AS PRIMARY SIGNALS !!
    Bubble color changes with themes and dark mode. Bubble alignment (left/right) varies by
    app version and OS. Both have high error rates. IGNORE them as primary signals.
    The PROFILE AVATAR is theme-independent and always correct — anchor everything on it.

    Step A: DETECT THE APP — Write the app name into the `detected_app` field.
    Identify the app from navigation chrome, icon shapes, button layout, or typography ONLY.

    Step B: FIND THE AVATAR ANCHOR (do this before reading any bubbles)
    Look for a small circular profile photo thumbnail in the chat thread.
    In every dating/messaging app, this thumbnail belongs to the OTHER person ("them") —
    you never see your own avatar floating next to your own messages.
       → Every bubble that has this circular avatar directly adjacent to it = sender is "them".
       → Every bubble that does NOT have this avatar next to it = sender is "user".
    If no avatar is visible anywhere in the thread, fall back to Step C.

    Step C: FALLBACK SIGNALS (use only if avatar is not visible)
       Signal 1 — DELIVERY INDICATORS: "Sent", "Delivered", "Read", checkmarks (✓✓) appear
           ONLY under the USER's messages. Strongest fallback signal.
       Signal 2 — HEADER NAME: The name at the TOP of the screen is ALWAYS "them".
           Their messages should be consistent with being from that named person.
       Signal 3 — TEXT INPUT BAR: The compose box at the bottom belongs to the USER.
           The side of screen the most recent non-input-bar bubbles are on tells you alignment.
       Signal 4 — BUBBLE ALIGNMENT: RIGHT = user, LEFT = them in most LTR apps.
           Use this LAST — it is the least reliable signal.

    Step D: WRITE REASONING into `sender_signals_used`.
    State which signal you used as your anchor (avatar preferred) and what you concluded.
    Your reasoning MUST NOT mention any color word (purple, blue, gray, green, rose, dark, light,
    colored, styled, accent, neutral, or any shade). If a color word appears in your reasoning,
    DELETE it and rewrite using only the avatar, alignment, delivery indicator, or header name.

       ✅ CORRECT: "Match's circular avatar appears next to bubbles on the left → those are 'them'.
          Bubbles on the right without any avatar → 'user'. Header name confirms match identity."
       ❌ WRONG (auto-fail): "The purple/colored bubbles belong to the match. The gray bubbles
          are the user." — any sentence mentioning color must be deleted and rewritten.
       ❌ ALSO WRONG: "Avatar next to the purple bubbles = them." — even mixing avatar + color
          is banned. Say: "Avatar next to those bubbles = them." No color words at all.

    Step E: FINAL ASSIGNMENT — Apply avatar-anchored labels consistently to ALL bubbles.
    Every bubble adjacent to the match's avatar = "them". All others = "user".
    NEVER infer sender from message content or conversational tone.

    !! REPLY / QUOTED BUBBLES — COMMON MISTAKE ZONE !!
    When someone replies to a specific message, their bubble shows a small faded preview of
    the original message at the top, with their actual reply text below it. This creates a
    bubble-within-a-bubble appearance. The rules are:

       RULE 1 — The OUTER bubble's sender is determined by the avatar anchor (Step B), NOT by
       whose text appears in the faded preview inside it.
       Example: If the match (them) replies to YOUR message, their outer bubble will show YOUR
       quoted text as a faded preview at the top, but the outer bubble sender is still "them".

       RULE 2 — When the user's last action was sending a reply, the screenshot may show the
       user's reply bubble sitting visually on top of or adjacent to the match's message.
       The user's reply bubble sender = "user". The match's message below/behind it = "them".
       Do not let the visual overlap confuse the sender assignment.

       RULE 3 — The faded quoted preview text inside a bubble is NOT a separate bubble.
       It belongs to quoted_context, not actual_new_message. Never create a separate raw_ocr_text
       entry for a quoted preview — it is part of the parent bubble only.

    Then read top-to-bottom. For each bubble, extract a raw_ocr_text object:
    * sender: "user" or "them" per Steps A–E (structural signals only — never from text semantics or color).
    * actual_new_message: The NEW text the person typed — the main bubble content BELOW any quoted preview. NEVER copy the quoted/reply preview text here.
    * quoted_context: The faded/smaller reply-preview text ABOVE the main bubble (null if the bubble has no reply preview). On Instagram/WhatsApp, this is the small gray bar showing the original message being replied to.
    * is_reply: true if quoted_context is not null.
    CRITICAL RULE: actual_new_message and quoted_context must NEVER be identical. If they look the same, you are reading the quoted preview twice — re-examine the bubble to find the actual reply text below the preview. If you truly cannot find separate text, set quoted_context=null (it is likely not a reply).

"""

# STEP 3 when direction is not "opener" (chat / reply modes): strict thread semantics + profile fallback.
_VISION_STEP_3_CHAT_MODE = """
STEP 3: ANALYSIS (VISUAL GROUND TRUTH ONLY)
Use only visible evidence. Never assume "them"'s questions/accusations are factual truths about the user.
Map raw_ocr_text 1:1 to visual_transcript (using sender, quoted_context, actual_new_message).

Fields for BOTH modes:
* visual_hooks: List 3-4 physical/environmental details from visible photos (empty list if no photos). On profiles, mine every photo across all screenshots (outfit, setting, props, vibe).
* detected_dialect: ENGLISH, HINDI, or HINGLISH — match her dominant language/mix across the visible text.
* person_name: Match's first name from UI header/profile (else "unknown").
* stage: new_match / opening / early_talking / building_chemistry / deep_connection / relationship / stalled / argument (profiles without a thread are usually new_match or opening).

IF CHAT CONVERSATION (real chat bubbles with user/them alignment):
* Base key_detail, their_last_message, and their_tone STRICTLY on her absolute newest message at the bottom of the thread.
* their_effort, conversation_temperature: From that latest message and immediate context.
* archetype_reasoning: 2-3 sentences analyzing her latest message structure (word count, questions, emojis) to justify the archetype.
* detected_archetype (Pick EXACTLY ONE): THE BANTER GIRL, THE INTELLECTUAL, THE WARM/STEADY, THE GUARDED/TESTER, THE EAGER/DIRECT, THE LOW-INVESTMENT.
* top_hooks: Exactly THREE distinct hooks from this chat turn — different angles, not the same idea reworded.
* key_detail: MUST equal top_hooks[0].
* their_last_message: A short paraphrase of her latest message that preserves relational context. If her message is a direct reaction to something the user said or hinted at (a question, a word, a plan), explain WHAT she caught on to and HOW she is reacting — not just what she literally said. Example: instead of "She is asking why he wants to meet", write "She caught on that he was hinting at meeting in Gurgaon and is playfully calling him out on it." Only paraphrase in isolation if her message has no clear reaction target.

IF DATING PROFILE (no chat thread — prompts, bio fragments, photo captions, Bumble/Hinge-style cards only):
* top_hooks: Use an empty list [] (profile mode does not use chat turn hooks).
* Do NOT anchor analysis on the last line of extracted text only. Treat the profile as a buffet: read ALL prompts, bios, and visible copy across every screenshot.
* key_detail: Pick the SINGLE strongest opener hook anywhere on the profile — prioritize interesting, funny, controversial, story-driven, or emotionally vulnerable lines (e.g. a quirky prompt beat, trust issues, a bold rule). It may come from an early prompt, a photo caption, or the middle of the bio — not necessarily the last OCR line.
* their_last_message: Summarize her overall profile vibe, energy, and what she signals she wants (playful, guarded, romantic, chaotic, etc.). This is NOT a paraphrase of one line; it is a holistic one- or two-sentence read so the reply model can choose among many angles.
* their_tone: Infer from the dominant emotional signal across the whole profile (not from one trailing fragment).
* their_effort: high if many prompts are filled with substance; medium/low if sparse or generic.
* conversation_temperature: hot / warm / lukewarm / cold from overall flirtiness and openness across the profile.
* archetype_reasoning: 2-3 sentences citing multiple profile elements (which prompts, what patterns). Do not reduce to "word count on last line."
* detected_archetype: Same enum as chat; choose based on how she presents across prompts and bio as a whole (e.g. vulnerable bio + playful prompts → weigh the mix honestly).
"""

# STEP 3 when direction == "opener": profile-first; no chronological chat tail bias.
_VISION_STEP_3_OPENER_PROFILE_BUFFET = """
STEP 3: ANALYSIS (PROFILE BUFFET MODE)
You are analyzing a dating profile to find the best possible conversation starters. There is no chronological "chat" happening yet. Treat the screenshots as a buffet of information.

Use only visible evidence. Map raw_ocr_text 1:1 to visual_transcript (using sender, quoted_context, actual_new_message) as in Step 2.

* top_hooks: Use an empty list [] (opener/profile mode does not use chat turn hooks).
* visual_hooks: Scan ALL screenshots. List 3-4 specific physical/environmental details (e.g., "red dress with balloons", "holding a matcha latte", "wearing large round glasses").
* detected_dialect: ENGLISH, HINDI, or HINGLISH. Base this on the dominant mix across all visible profile text.
* their_tone: The overall vibe of their profile prompts/bio.
* their_effort: high / medium / low based on how much they wrote.
* conversation_temperature: warm (default for profiles).
* archetype_reasoning: 2-3 sentences analyzing multiple prompts, bio elements, and photo vibes to assign an archetype.
* detected_archetype: Base this on the holistic tone of the profile.
* key_detail: Scan ALL extracted text prompts and bios. Pick the single most interesting, controversial, or vulnerable hook found ANYWHERE in the profile. Do NOT default to the bottom-most text. Pick the one that makes for the best banter.
* person_name: Match's first name from UI header/profile (else "unknown").
* stage: "new_match" or "opening".
* their_last_message: Do NOT paraphrase a single line. Instead, write a 1-2 sentence "Holistic Vibe Summary" of her entire profile (e.g., "She is a foodie who loves travel and is being very vulnerable about her trust issues.").
"""


def build_vision_system_prompt(direction: str) -> str:
    """
    Assemble the vision system prompt. Step 3 depends on UI direction: ``opener`` uses
    profile-buffet rules; all other directions keep chat-oriented Step 3 (unchanged).
    No user-controlled string interpolation — only a fixed branch on normalized direction.
    """
    d = (direction or "").strip().lower()
    step3 = (
        _VISION_STEP_3_OPENER_PROFILE_BUFFET
        if d == "opener"
        else _VISION_STEP_3_CHAT_MODE
    )
    return _VISION_SYSTEM_PROMPT_STEPS_1_2 + step3


def _multi_screenshot_user_hint(image_count: int, *, is_opener: bool) -> str:
    """Extra human-message text when multiple images are attached (no f-string user input)."""
    if image_count <= 1:
        return ""
    n = image_count
    if is_opener:
        return (
            f"\n\nMULTI-SCREENSHOT ({n} images): Same dating profile across scrolls or panels. "
            "Merge every visible prompt, bio fragment, and photo into one buffet — do not treat "
            "only the last image as the source of truth for hooks or vibe."
        )
    return (
        f"\n\nMULTI-SCREENSHOT ({n} images): Chronological order — image 1 oldest, "
        f"image {n} newest. Merge into one continuous transcript or profile view; "
        "do not duplicate bubbles that appear across crops. "
        "Latest speaker and their_last_message must match the NEWEST screenshot; "
        "use earlier images only for context when the latest crop is incomplete."
    )


def _count_image_url_parts_in_human_content(content: list) -> int:
    """LangChain HumanMessage content blocks with type ``image_url`` (each = one image to the model)."""
    return sum(
        1
        for part in content
        if isinstance(part, dict) and part.get("type") == "image_url"
    )


async def perform_full_vision_analysis(
    images_base64: list[str],
    *,
    direction: str,
    screenshots_in_request: int | None = None,
) -> VisionNodeOutput:
    """Run the full (main) Vision Node Gemini call once, returning parsed output.

    Pass every screenshot the client sent (after tier clamp), in order: oldest first, newest last.
    ``direction`` selects Step 3 (``opener`` = profile buffet; else chat-mode Step 3).
    ``screenshots_in_request`` defaults to ``len(images_base64)`` for logs if omitted.
    """
    if not images_base64:
        raise ValueError("images_base64 must be a non-empty list")

    # The endpoint runs this LLM call before hybrid stitch resolution, so we keep lore out of
    # the prompt. Any semantic memory fetching happens later in the endpoint.
    ocr_hint_text = ""
    vision_direction = (direction or "").strip().lower()
    is_opener = vision_direction == "opener"
    system_prompt = build_vision_system_prompt(vision_direction)

    content: list = []
    for b64 in images_base64:
        image_url = encode_image_from_state(cast(AgentState, {"image_bytes": b64}))
        content.append({"type": "image_url", "image_url": {"url": image_url}})

    n = len(images_base64)
    multi_hint = _multi_screenshot_user_hint(n, is_opener=is_opener)

    content.append(
        {
            "type": "text",
            "text": (
                f"OCR hint text (may be partial/noisy):\n{ocr_hint_text.strip()}\n\n"
                f"Process the attached image{'s' if n > 1 else ''} as the absolute current reality."
                + multi_hint
            ),
        }
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content),
    ]

    images_attached_to_vision_llm = _count_image_url_parts_in_human_content(content)

    t_start = time.monotonic()
    logger.info(
        "llm_lifecycle",
        stage="vision_node_pre_llm",
        trace_id="",
        user_id="",
        conversation_id="",
        direction=vision_direction,
        vision_step3_mode="opener_profile_buffet" if is_opener else "chat",
        model=VISION_MODEL,
        temperature=0,
        core_lore_chars=0,
        past_memories_chars=0,
        ocr_hint_chars=0,
        images_attached_to_vision_llm=images_attached_to_vision_llm,
        screenshots_in_request=screenshots_in_request if screenshots_in_request is not None else n,
    )
    logger.info(
        "vision_node_llm_messages",
        trace_id="",
        user_id="",
        conversation_id="",
        direction=vision_direction,
        phase="v2_vision",
        model=VISION_MODEL,
        messages=sanitize_llm_messages_for_logging(messages),
    )

    try:
        result, usage_row = invoke_structured_gemini(
            model=VISION_MODEL,
            temperature=0,
            schema=VisionNodeOutput,
            messages=messages,
            phase="v2_vision",
        )
        out = cast(VisionNodeOutput, result)
        _vision_usage_row_var.set(usage_row)
        logger.info(
            "vision_node_llm_result",
            trace_id="",
            user_id="",
            conversation_id="",
            direction=vision_direction,
            out=out.model_dump(),
            usage_phase=usage_row.get("phase"),
            usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
            usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
            images_attached_to_vision_llm=images_attached_to_vision_llm,
            screenshots_in_request=screenshots_in_request if screenshots_in_request is not None else n,
        )
        return out
    except Exception as e:
        logger.error(
            "vision_node_llm_error",
            trace_id="",
            user_id="",
            conversation_id="",
            direction=vision_direction,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
            images_attached_to_vision_llm=images_attached_to_vision_llm,
            screenshots_in_request=screenshots_in_request if screenshots_in_request is not None else n,
        )
        raise


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


@router.post(
    "/vision/generate_v2", response_model=VisionResponse | RequiresUserConfirmation
)
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
        raise HTTPException(
            status_code=400, detail="At least one screenshot is required."
        )
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
    try:
        vision_out = await perform_full_vision_analysis(
            images,
            direction=request.direction.value,
            screenshots_in_request=len(images),
        )
    except Exception as e:
        if _is_provider_timeout(e):
            raise HTTPException(
                status_code=504,
                detail="The AI took too long to read all the images. Try uploading fewer screenshots.",
            ) from e
        if _is_transient_provider_overload(e):
            raise HTTPException(
                status_code=503,
                detail="Vision model is temporarily overloaded. Please retry in a few seconds.",
            ) from e
        raise

    if not vision_out.is_valid_chat:
        raise HTTPException(400, vision_out.bouncer_reason)

    # Extract variables for stitching.
    ocr_person_name = vision_out.person_name
    extracted_texts = [
        b["actual_new_message"]
        for b in (vision_out.raw_ocr_text or [])
        if isinstance(b, dict) and "actual_new_message" in b
    ]

    effective_conversation_id = request.conversation_id
    new_conversation_person_name: str | None = None

    if not effective_conversation_id:
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
            payload["detail"] = (
                f"409 requires user confirmation. reason={conflict_reason}"
            )

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

    # Fetch librarian context after stitching resolved so conversation_id is final.
    ocr_hint_text = " ".join(extracted_texts[-2:]) if extracted_texts else ""
    core_lore = ""
    past_memories = ""
    if effective_conversation_id:
        try:
            librarian = await fetch_librarian_context_async(
                user_id=user.id,
                conversation_id=str(effective_conversation_id),
                current_text=ocr_hint_text,
            )
            core_lore = librarian.get("core_lore") or ""
            past_memories = librarian.get("past_memories") or ""
        except Exception as e:
            logger.warning(
                "agent_v2_librarian_failed",
                trace_id="",
                error=str(e),
                user_id=user.id,
                conversation_id=str(effective_conversation_id or ""),
            )

    initial_state = _build_agent_initial_state(
        images[-1],
        request.direction.value,
        custom_hint or "",
        user.id,
        effective_conversation_id,
        voice_dna,
        conversation_context,
    )
    trace_id = initial_state.get("trace_id", "")
    initial_state["ocr_hint_text"] = ocr_hint_text

    # Inject the already-computed full Vision Node output + librarian context.
    initial_state["vision_out"] = vision_out.model_dump()
    initial_state["core_lore"] = core_lore
    initial_state["past_memories"] = past_memories
    if (usage_row := _vision_usage_row_var.get()) is not None:
        initial_state["gemini_usage_log"] = [usage_row]

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
        if _is_provider_timeout(e):
            raise HTTPException(
                status_code=504,
                detail="The AI took too long to read all the images. Try uploading fewer screenshots.",
            ) from e
        if _is_transient_provider_overload(e):
            raise HTTPException(
                status_code=503,
                detail="Model is temporarily overloaded. Please retry in a few seconds.",
            ) from e
        logger.error(
            "agent_v2_run_failed",
            trace_id=trace_id,
            error=str(e),
            user_id=user.id,
            conversation_id=effective_conversation_id or "",
        )
        raise HTTPException(
            status_code=502, detail="Failed to generate replies. Try again."
        ) from e

    if not final_state.get("is_valid_chat", True):
        # Roll back placeholder conversation on bouncer rejection.
        # This prevents empty "link chats" / matches based on placeholder rows.
        if (
            placeholder_conversation_id
            and effective_conversation_id == placeholder_conversation_id
        ):
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
            detail=final_state.get(
                "bouncer_reason", "Image is not a valid chat or dating app screenshot."
            ),
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

    _tmp_replies = [
        _RO(
            text=r.text,
            strategy_label=r.strategy_label,
            is_recommended=r.is_recommended,
            coach_reasoning=r.coach_reasoning,
        )
        for r in parsed.replies
    ]
    _cleaned = _pp(_WO(replies=_tmp_replies))
    from app.domain.models import ReplyOption as DomainReply
    from dataclasses import replace as _replace

    parsed.replies = [
        _replace(r, text=c.text) for r, c in zip(parsed.replies, _cleaned.replies)
    ]

    # ------------------------------------------------------------------ #
    # 10. Voice DNA: extract organic text, run echo filter, update stats
    # ------------------------------------------------------------------ #
    organic_text = await extract_organic_text(
        db=db, user=user, parsed=parsed, conversation_id=effective_conversation_id
    )
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
