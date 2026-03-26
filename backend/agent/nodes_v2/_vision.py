"""
Node 1: vision_node

Single Gemini multimodal call that performs:
  1. Bouncer validation (is this a chat screenshot?)
  2. OCR extraction (bubble text, sender, quoted context)
  3. Conversation analysis (archetype, tone, effort, temperature, dialect)

Also fetches librarian context (core_lore + past_memories) from the DB inline.
Model: `settings.gemini_model` (GEMINI_MODEL) at temperature 0 (deterministic)
"""

import time
from typing import Any, cast

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agent.nodes_v2._lc_usage import invoke_structured_gemini
from agent.nodes_v2._shared import (
    VISION_MODEL,
    encode_image_from_state,
    fetch_librarian_context,
    normalize_raw_ocr_text,
    sanitize_llm_messages_for_logging,
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

    # OCR fields — only populated when is_valid_chat is true
    raw_ocr_text: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of bubble objects extracted verbatim. Each has: "
            "sender ('user'=right-aligned, 'them'=left-aligned), "
            "actual_new_message (bold fresh text below any quoted block), "
            "quoted_context (faded top block or null), "
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
        description="3-4 specific physical or environmental details from photos.",
    )
    detected_dialect: str = Field(
        default="ENGLISH",
        description="ENGLISH, HINDI, or HINGLISH based on her most recent message.",
    )
    their_tone: str = Field(default="neutral")
    their_effort: str = Field(default="medium")
    conversation_temperature: str = Field(default="warm")
    archetype_reasoning: str = Field(
        default="",
        description=(
            "2-3 sentence reasoning for archetype selection. If visual evidence in the "
            "chat screenshot contradicts Core Lore and you prioritize visuals, explicitly "
            "state that contradiction and that visual evidence overrode Lore."
        ),
    )
    detected_archetype: str = Field(default="THE WARM/STEADY")
    key_detail: str = Field(default="")
    person_name: str = Field(default="unknown")
    stage: str = Field(default="early_talking")
    their_last_message: str = Field(default="")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

VISION_NODE_SYSTEM_PROMPT = """
You are a combined chat screenshot analyzer. Process the image in THREE sequential steps.

══════════════════════════════════════
STEP 1 — BOUNCER VALIDATION
══════════════════════════════════════
Decide if this image is either:
  (A) a text/chat conversation screenshot (contains chat bubbles), OR
  (B) a dating app profile page screenshot (contains bio/prompts/overlay text and photos used for generating openers).

- is_valid_chat = true → it contains chat bubbles OR it is a dating app profile page suitable for generating openers.
- is_valid_chat = false → it is a random photo, menu, meme, blank screen, or non-chat/non-profile image.
- Provide a short bouncer_reason indicating whether it was chat bubbles vs a dating app profile page.

Dating app profiles are valid inputs for generating openers.

If is_valid_chat = false, stop here. Return empty arrays for all other fields.

══════════════════════════════════════
STEP 2 — OCR EXTRACTION (only if is_valid_chat = true)
══════════════════════════════════════
CRITICAL: Bubble ownership and quoted-reply splitting.
If this is a dating app profile page and there are NO chat bubbles:
  - Extract all visible textual content from the profile (bio, prompts, interests, captions, overlay headlines/buttons).
  - Combine the extracted text into a single object in raw_ocr_text with:
      sender = "them"
      actual_new_message = extracted profile text (verbatim; if multiple snippets, join with newline in screen order)
      quoted_context = null
      is_reply = false
  - Then go directly to STEP 3 (analysis). Do NOT apply chat-bubble/quoted-reply splitting rules.

Otherwise (if it is a chat conversation with message bubbles), read the image from top to bottom. For each message bubble:

1) Identify the Anchor (sender) using COLOR as the ABSOLUTE source of truth:
   - GRAY or WHITE bubble = "them" (The Match)
   - BLUE, PURPLE, GREEN, or ORANGE bubble = "user" (You)
   - If there are checkmarks (✓✓) or "Read" text under a bubble = "user".

   CRITICAL RULES:
   - DO NOT use the "meaning" of the words to decide who sent it. 
   - If a bubble is GRAY, it is "them", even if it is a question, even if it is an answer, and even if it is the very last bubble in the chat.
   - The "Anti-Bias" rule is now secondary: Only assume the last message is "user" if the bubble is physically COLORED. If it is GRAY, it is "them".

   * Ignore the "Type a message..." input text bar entirely.

2) Detect Quoted Layers (quoted_context):
   - If there is a nested/grey/indented faded quoted block at the TOP of the bubble, extract that quoted block text.
   - If there are multiple faded nested quote blocks at the top, extract all of them and join with newline.
   - If there is no quoted/faded block at the top, set quoted_context = null.

3) Actual Message (actual_new_message):
   - Extract the bold/solid actual fresh message BELOW the quoted_context (the bottom-most solid text in the bubble).
   - actual_new_message MUST NOT include any faded/quoted text.

4) is_reply:
   - true iff quoted_context is not null and not empty.

Populate raw_ocr_text as a list of objects with keys:
  sender, actual_new_message, quoted_context, is_reply

Do not translate or summarize. Extract the exact text, emojis, and punctuation as they appear on screen.

══════════════════════════════════════
STEP 3 — ANALYSIS (VISUAL GROUND TRUTH ONLY)
══════════════════════════════════════
You are an expert social profiler. Use ONLY what is visible in this screenshot (chat bubbles/profile text/photos).
Do not use prior memory, lore, or historical assumptions to decide vibe, tone, or archetype.

Also use the image strictly to extract visual_hooks (3-4 specific physical or environmental details
from any photos visible, e.g. "Wearing a high-end watch", "In a library", "Holding a specific breed of dog").
If no photos are visible, return an empty list.

From the raw_ocr_text:
- Build visual_transcript by mapping each object 1:1 into a ChatBubble dict:
  - sender = item.sender (absolute bubble alignment; do NOT infer from text)
  - quoted_context = item.quoted_context or "" if null
  - actual_new_message = item.actual_new_message
- Ownership rule:
  - actual_new_message always belongs to the bubble's sender.
  - quoted_context is past context and MUST NOT be used as the "latest actual message" for her last message.

For ALL analysis fields below, your primary focus is the most recent bubble where sender == "them" (ignore its quoted_context). HOWEVER, you must also look at the absolute bottom of the transcript to see who sent the final message.

- detected_dialect: ENGLISH, HINDI, or HINGLISH based on her most recent bubble's actual_new_message.
- their_tone: excited / playful / flirty / neutral / dry / upset / testing / vulnerable / sarcastic
- their_effort: high / medium / low
- conversation_temperature: hot / warm / lukewarm / cold
  - archetype_reasoning: FIRST, count how many words are in her most recent actual_new_message.
  THEN classify her message structure: is it a question? a statement? an emoji-only response?
  a sarcastic comeback with a specific punchline? a longer paragraph with a topic? a short
  "haha ok" filler? Write 2-3 sentences analyzing her MESSAGE STRUCTURE and EFFORT PATTERN
  before picking an archetype. Keep reasoning grounded only in currently visible message evidence.
  Do NOT default to banter just because the message is playful —
  most dating conversations are playful, that alone is not banter.
- detected_archetype: Based strictly on the reasoning above, select EXACTLY ONE:

    "THE BANTER GIRL"       — STRICT: She must be doing at least ONE of these: (a) explicit sarcasm
                               with a punchline ("oh wow what a catch"), (b) flipping a question/test
                               back at the user ("why dont YOU tell me"), (c) playful accusations
                               ("youre definitely a catfish"). Normal playful/friendly messages like
                               "haha thats funny" or "omg really" are NOT banter — those are WARM/STEADY.
    "THE INTELLECTUAL"      — Her message is 15+ words AND contains a substantive topic, opinion,
                               question about ideas/values/experiences, or cultural reference.
                               Not just a long message — it must have DEPTH or a topic to discuss.
    "THE WARM/STEADY"       — DEFAULT for most normal conversations. She is friendly, engaged,
                               responsive, uses emojis/laughter naturally, asks casual questions,
                               shares updates. This is the MOST COMMON archetype. If you are unsure
                               between this and BANTER GIRL, pick this one.
    "THE GUARDED/TESTER"    — She is asking qualifying/screening questions: "what are you looking
                               for", "are you serious or just here for fun", "do you do this with
                               all girls", "why did your last relationship end". These are TESTS
                               that require sincerity, not banter.
    "THE EAGER/DIRECT"      — She is showing clear forward interest: suggesting to meet, giving
                               her number unprompted, explicit flirting ("come over", "when are we
                               meeting"), or enthusiastically agreeing to plans. She is past games.
    "THE LOW-INVESTMENT"    — Her ENTIRE message is under 4 words AND is filler: "haha", "ok",
                               "yeah", "nice", "lol", single emoji. If she wrote 5+ words or asked
                               ANY question, she is NOT low-investment.
CRITICAL: STRICT SPEAKER ATTRIBUTION
When extracting facts to save into Core Lore or Past Memories, you MUST attribute the fact to the correct speaker based strictly on who sent the message.
- If 'them' (the Match) asks a question like 'Are you an HR?', DO NOT save 'User is an HR'. Save: 'Match asked about the User's job/HR role.'
- Only save facts about the User if the 'user' explicitly stated or confirmed them in their own outgoing messages.
- Never assume a playful accusation or question from the Match is a permanent factual truth about the User.

- key_detail: One specific thing from her most recent actual_new_message to hook into.
- person_name: First name of the match if discernible from the top UI header or profile text, else "unknown". Do NOT look for her name inside her own text bubbles.
- stage: new_match / opening / early_talking / building_chemistry / deep_connection / relationship / stalled / argument
- their_last_message: Short paraphrase of her most recent message. CRITICAL: If the absolute last message in the chat belongs to "user", you MUST append this exact note to the end of your paraphrase: " [Note: User already replied with: '<insert user's last message>']". This ensures the downstream generator knows it is writing a double-text.

Return ALL fields. Populate everything.
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def vision_node(state: AgentState) -> dict:
    """
    Single Gemini multimodal call that performs:
      1. Bouncer validation
      2. OCR extraction
      3. Conversation analysis

    Also fetches librarian context (core_lore + past_memories) from the DB inline.

    Returns partial state update (LangGraph merges into full state).
    """
    user_id = state.get("user_id", "")
    trace_id = state.get("trace_id", "")
    conversation_id = state.get("conversation_id")
    direction = state.get("direction", "")
    t_start = time.monotonic()
    logger.info(
        "llm_lifecycle",
        stage="vision_node_start",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id or "",
        direction=direction,
        revision_count=state.get("revision_count", 0),
        has_ocr_hint=bool((state.get("ocr_hint_text") or "").strip()),
        has_image_bytes=bool(state.get("image_bytes")),
    )

    image_url = encode_image_from_state(state)
    core_lore = ""
    past_memories = ""

    # --- Librarian fetch (before the LLM call so lore is available) ---
    if conversation_id and user_id:
        try:
            librarian = fetch_librarian_context(
                user_id=user_id,
                conversation_id=conversation_id,
                current_text=state.get("ocr_hint_text") or "",
            )
            core_lore = librarian.get("core_lore") or ""
            past_memories = librarian.get("past_memories") or ""
        except Exception as e:
            logger.warning(
                "agent_v2_librarian_failed",
                trace_id=trace_id,
                error=str(e),
                user_id=user_id,
                conversation_id=conversation_id or "",
            )

    content = [
        {"type": "image_url", "image_url": {"url": image_url}},
        {
            "type": "text",
            "text": (
                f"OCR hint text (may be partial/noisy):\n{(state.get('ocr_hint_text') or '').strip()}\n\n"
                "Process the attached image as the absolute current reality."
            ),
        },
    ]

    messages = [
        SystemMessage(content=VISION_NODE_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]

    logger.info(
        "llm_lifecycle",
        stage="vision_node_pre_llm",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id or "",
        direction=direction,
        model=VISION_MODEL,
        temperature=0,
        core_lore_chars=len(core_lore or ""),
        past_memories_chars=len(past_memories or ""),
        ocr_hint_chars=len((state.get("ocr_hint_text") or "").strip()),
    )
    logger.info(
        "vision_node_llm_messages",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id or "",
        direction=direction,
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
        logger.info(
            "vision_node_llm_result",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id or "",
            direction=direction,
            out=out.model_dump(),
            usage_phase=usage_row.get("phase"),
            usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
            usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
        )
    except Exception as e:
        logger.error(
            "vision_node_llm_error",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id or "",
            direction=direction,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
        )
        raise

    if not out.is_valid_chat:
        logger.info(
            "llm_lifecycle",
            stage="vision_node_complete",
            trace_id=trace_id,
            is_valid_chat=False,
            user_id=user_id,
            conversation_id=conversation_id or "",
            direction=direction,
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
            usage_phase=usage_row.get("phase"),
            usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
            usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
            bouncer_reason=(out.bouncer_reason or "")[:200],
        )
        return {
            "is_valid_chat": False,
            "bouncer_reason": out.bouncer_reason,
            "core_lore": core_lore,
            "past_memories": past_memories,
            "gemini_usage_log": [usage_row],
        }

    # Build AnalystOutput from VisionNodeOutput fields
    visual_transcript = []
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
        detected_dialect=out.detected_dialect,  # type: ignore[arg-type]
        their_tone=out.their_tone,
        their_effort=out.their_effort,
        conversation_temperature=out.conversation_temperature,
        archetype_reasoning=out.archetype_reasoning,
        detected_archetype=out.detected_archetype,
        key_detail=out.key_detail,
        person_name=out.person_name,
        stage=out.stage,
        their_last_message=out.their_last_message,
    )

    raw_ocr_text = normalize_raw_ocr_text(out.raw_ocr_text)

    logger.info(
        "llm_lifecycle",
        stage="vision_node_complete",
        trace_id=trace_id,
        is_valid_chat=True,
        user_id=user_id,
        conversation_id=conversation_id or "",
        direction=direction,
        elapsed_ms=int((time.monotonic() - t_start) * 1000),
        bubble_count=len(raw_ocr_text),
        visual_transcript_count=len(visual_transcript),
        visual_hooks_count=len(out.visual_hooks or []),
        detected_archetype=out.detected_archetype,
        detected_dialect=out.detected_dialect,
        conversation_temperature=out.conversation_temperature,
        analysis_stage=out.stage,
        person_name=out.person_name,
        core_lore_chars=len(core_lore or ""),
        past_memories_chars=len(past_memories or ""),
        usage_phase=usage_row.get("phase"),
        usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
        usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
    )

    return {
        "is_valid_chat": True,
        "bouncer_reason": out.bouncer_reason,
        "raw_ocr_text": raw_ocr_text,
        "analysis": analysis,
        "core_lore": core_lore,
        "past_memories": past_memories,
        "gemini_usage_log": [usage_row],
    }
