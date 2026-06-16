"""
Node 1: vision_node (pass-through)

The main VisionNode LLM call is executed in the v2 API endpoint *before* stitching.
This node only converts the already-parsed `VisionNodeOutput` stored in the
LangGraph state into:
  - `analysis` (AnalystOutput)
  - `raw_ocr_text` (normalized OCR bubble objects)

No LLM calls happen in this file anymore.
"""

from typing import Any, Literal, cast

import structlog
from pydantic import BaseModel, Field

from agent.nodes_v2._personality import (
    Engagement,
    Intent,
    Playfulness,
    Traditionalism,
    Warmth,
)
from agent.nodes_v2._shared import (
    normalize_raw_ocr_text,
)
from agent.state import AgentState, AnalystOutput, ChatBubble

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class VisionNodeOutput(BaseModel):
    """Combined output of bouncer + OCR + analyst in a single call."""

    # Bouncer fields
    is_valid_chat: bool = Field(
        description="true if this image is a chat/dating app screenshot, false otherwise."
    )
    bouncer_reason: str = Field(description="Short reason for the validity decision.")

    # App & sender reasoning — chain-of-thought fields (populated when is_valid_chat is true)
    detected_app: str = Field(
        default="unknown",
        description=(
            "Which messaging/dating app is shown (e.g., Bumble, Hinge, Tinder, "
            "WhatsApp, iMessage, Instagram, Telegram). 'unknown' if unclear."
        ),
    )
    sender_signals_used: str = Field(
        default="",
        description=(
            "Brief explanation of which visual signals were used to assign sender labels "
            "(e.g., 'right-aligned bubbles with blue color = user, left-aligned gray = them, "
            "confirmed by delivery checkmarks on right side'). This MUST be filled before "
            "assigning any sender labels in raw_ocr_text."
        ),
    )

    # OCR fields — only populated when is_valid_chat is true
    raw_ocr_text: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of bubble objects extracted verbatim. Each has: "
            "sender ('user' or 'them' based on multi-signal triangulation), "
            "actual_new_message (text inside the bubble), "
            "quoted_context (faded/nested reply text or null), "
            "is_reply (true iff quoted_context present)."
        ),
    )

    # Analyst fields — only populated when is_valid_chat is true
    visual_transcript: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of ChatBubble dicts: sender, quoted_context, actual_new_message.",
    )
    visual_hooks: list[str] = Field(
        default_factory=list,
        description=(
            "3-4 specific physical or environmental details from photos; on profiles scan "
            "all screenshots for outfits, settings, props."
        ),
    )
    photo_persona: str = Field(
        default="",
        description=(
            "1-3 words capturing the PERSONA/aesthetic her photos project as a CURATED "
            "self-presentation (e.g. 'rebel/edgy', 'soft romantic', 'influencer-polished', "
            "'girl-next-door', 'old-money', 'outdoorsy adventurer', 'corporate put-together'). "
            "Read the vibe she CHOSE to present, NOT a judgment of her face or body. "
            "Empty if there are no photos."
        ),
    )
    detected_dialect: str = Field(
        default="ENGLISH",
        description=(
            "ENGLISH, HINDI, or HINGLISH. Chat: match her latest message. Profile: dominant mix "
            "across all visible profile text."
        ),
    )
    their_tone: str = Field(default="neutral")
    their_effort: str = Field(default="medium")
    conversation_temperature: str = Field(default="warm")
    archetype_reasoning: str = Field(
        default="",
        description=(
            "2-3 sentences justifying the dimension scores below. Chat: cite the structure of her "
            "latest message. Profile: cite multiple prompts/bio elements. If chat visuals contradict "
            "Core Lore, say you prioritized visuals."
        ),
    )
    # Personality dimensions (constrained — see _personality.py). The LLM scores
    # these; the archetype label is DERIVED from them in code, not chosen here.
    warmth: Warmth = Field(
        default="neutral",
        description="guarded = walls up/testing/cold; neutral; warm = open and receptive.",
    )
    playfulness: Playfulness = Field(
        default="balanced",
        description="earnest = sincere/serious; balanced; playful = banter-y, teasing, sarcastic.",
    )
    engagement: Engagement = Field(
        default="medium",
        description="low = short/flat/low-effort; medium; high = invests real effort, long/curious.",
    )
    traditionalism: Traditionalism = Field(
        default="mixed",
        description="modern = casual/contemporary; mixed; traditional = culturally rooted, values-forward.",
    )
    intent: Intent = Field(
        default="open",
        description="exploring = figuring it out; open; long_term = explicitly seeks a serious relationship.",
    )
    # Derived in code from the dimensions above (see _personality.derive_archetype).
    # Kept for logging + Phase 4/5 learning continuity; not chosen by the LLM.
    detected_archetype: str = Field(default="THE WARM/STEADY")
    top_hooks: list[str] = Field(
        default_factory=list,
        description=(
            "Chat: exactly three distinct hooks for this turn; key_detail must equal index 0. "
            "Profile/opener: empty list."
        ),
    )
    key_detail: str = Field(
        default="",
        description=(
            "Chat: must equal top_hooks[0] when in chat mode. Profile: the single best opener hook "
            "anywhere (funny, vulnerable, controversial, story) — not only the last OCR line."
        ),
    )
    person_name: str = Field(default="unknown")
    stage: str = Field(default="early_talking")
    their_last_message: str = Field(
        default="",
        description=(
            "Chat: short paraphrase of her latest message that preserves relational context. "
            "If her message is a direct reaction to something the user said or hinted at, "
            "explain WHAT she caught on to and HOW she is reacting — not just what she literally said. "
            "Example: 'She caught on that he was hinting at meeting in Gurgaon and is playfully calling him out on it' "
            "rather than 'She is asking why he wants to meet.' Only paraphrase in isolation if her message has no clear reaction target. "
            "Profile: holistic 1-2 sentence vibe summary of the whole profile (buffet of angles), not one-line paraphrase."
        ),
    )
    user_last_move: str = Field(
        default="",
        description=(
            "Chat ONLY (empty for profiles/openers with no user message). Read the USER's own most "
            "recent message in the thread and judge it in 1 sentence: was it high-effort or low-effort "
            "(generic compliment like 'wow so touching', one-word, 'haha', 'nice'), and is her current "
            "tone likely a REACTION to it? Example: 'User replied with a low-effort generic compliment; "
            "her flat \"may be\" reads as mild disappointment at his weak reply, not loss of interest.' "
            "If the user's last message was strong/substantive, say so. Empty if there is no user message."
        ),
    )
    inbound_image: Literal["none", "selfie_of_her", "object_or_scene"] = Field(
        default="none",
        description=(
            "Did SHE send an image AS a chat message (not a profile photo, not the app avatar)? "
            "'selfie_of_her' = a photo of herself (interest/escalation signal). "
            "'object_or_scene' = a thing/moment she shared — coffee, food, pet, view, meme, screenshot. "
            "'none' = no image she sent (normal text chat, or this is a profile/opener). "
            "Only classify an image that appears as one of HER chat bubbles."
        ),
    )
    inbound_image_detail: str = Field(
        default="",
        description=(
            "If inbound_image is not 'none', a SHORT noun phrase naming the durable, memory-worthy "
            "subject of the image she sent (e.g. 'her golden retriever', 'a latte at a cafe', "
            "'hiking at a mountain viewpoint', 'her in a red saree at a wedding'). This becomes a "
            "long-term fact about her. Empty if inbound_image is 'none' or there's nothing notable."
        ),
    )
    durable_facts: list[str] = Field(
        default_factory=list,
        description=(
            "0-5 ATOMIC, durable, third-person facts about HER worth remembering long-term, each a "
            "SHORT self-contained statement (e.g. 'Works in her family design business', 'Has a golden "
            "retriever', 'Divorced', 'From Ghaziabad', 'Training for a half-marathon', 'Into stand-up "
            "comedy', 'Vegetarian'). Extract from her messages AND profile. RULES: one fact per item, "
            "no 'she said...'; DURABLE only — skip ephemeral/throwaway turns, her current mood, and "
            "online-status; skip facts about the USER; skip obvious app metadata. Empty list if "
            "nothing durable this turn."
        ),
    )


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def vision_node(state: AgentState) -> dict:
    """
    Pass-through node: the endpoint already ran the full VisionNode LLM call and
    stored the parsed `VisionNodeOutput` under `state["vision_out"]`.

    This node only:
      - converts `VisionNodeOutput` -> `AnalystOutput`
      - normalizes `raw_ocr_text`
    """
    trace_id = state.get("trace_id", "")
    user_id = state.get("user_id", "")
    conversation_id = state.get("conversation_id") or ""
    direction = state.get("direction", "")

    out_raw = state.get("vision_out") or {}
    out = VisionNodeOutput.model_validate(out_raw)

    core_lore = state.get("core_lore", "") or ""
    past_memories = state.get("past_memories", "") or ""

    logger.info(
        "llm_lifecycle",
        stage="vision_node_start_pass_through",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        is_valid_chat=bool(out.is_valid_chat),
        person_name=out.person_name,
        detected_app=out.detected_app,
        sender_signals_used=out.sender_signals_used,
    )

    if not out.is_valid_chat:
        return {
            "is_valid_chat": False,
            "bouncer_reason": out.bouncer_reason,
            "analysis": None,
            "raw_ocr_text": [],
            "core_lore": core_lore,
            "past_memories": past_memories,
        }

    # Build AnalystOutput from VisionNodeOutput fields
    visual_transcript: list[ChatBubble] = []
    for bubble in out.visual_transcript:
        if isinstance(bubble, ChatBubble):
            visual_transcript.append(bubble)
        elif isinstance(bubble, dict):
            visual_transcript.append(
                ChatBubble(
                    sender=bubble.get("sender", "them"),
                    quoted_context=bubble.get("quoted_context") or "",
                    actual_new_message=bubble.get("actual_new_message", ""),
                )
            )

    analysis = AnalystOutput(
        visual_transcript=visual_transcript,
        visual_hooks=out.visual_hooks,
        photo_persona=out.photo_persona,
        detected_dialect=out.detected_dialect,  # type: ignore[arg-type]
        their_tone=out.their_tone,
        their_effort=out.their_effort,
        conversation_temperature=out.conversation_temperature,
        archetype_reasoning=out.archetype_reasoning,
        warmth=out.warmth,
        playfulness=out.playfulness,
        engagement=out.engagement,
        traditionalism=out.traditionalism,
        intent=out.intent,
        detected_archetype=out.detected_archetype,
        top_hooks=out.top_hooks,
        key_detail=out.key_detail,
        person_name=out.person_name,
        stage=out.stage,
        their_last_message=out.their_last_message,
        user_last_move=out.user_last_move,
        inbound_image=out.inbound_image,
        inbound_image_detail=out.inbound_image_detail,
        durable_facts=out.durable_facts,
    )

    raw_ocr_text = normalize_raw_ocr_text(out.raw_ocr_text)

    logger.info(
        "llm_lifecycle",
        stage="vision_node_complete_pass_through",
        trace_id=trace_id,
        is_valid_chat=True,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        bubble_count=len(raw_ocr_text),
        visual_transcript_count=len(visual_transcript),
        visual_hooks_count=len(out.visual_hooks or []),
        detected_archetype=out.detected_archetype,
        detected_dialect=out.detected_dialect,
        conversation_temperature=out.conversation_temperature,
        analysis_stage=out.stage,
        person_name=out.person_name,
    )

    return {
        "is_valid_chat": True,
        "bouncer_reason": out.bouncer_reason,
        "raw_ocr_text": raw_ocr_text,
        "analysis": analysis,
        "core_lore": core_lore,
        "past_memories": past_memories,
    }
