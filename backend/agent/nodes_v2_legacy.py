"""
V2 agent nodes — 3-node architecture with evaluator-rewriter loop.

Node 1: vision_node
  - Bouncer validation + OCR extraction + Analysis in a single Gemini multimodal call
  - Also runs the librarian (DB memory fetch) inline
  - Model: gemini-3.1-flash-lite-preview

Node 2: generator_node
  - Strategy + Writing in a single Gemini call with structured output
  - On rewrites, receives auditor feedback to fix specific issues
  - Model: gemini-3.1-flash-lite-preview
  - Dynamic temperature from direction × conversation state

Node 3: auditor_node
  - Evaluates reply quality against context, archetype, direction, and substance
  - Does NOT check style/punctuation (handled by deterministic post-processor)
  - Returns per-reply verdicts with specific rewrite instructions
  - If any reply fails → routes back to generator with feedback (max 1 rewrite)
  - Model: gemini-3.1-flash-lite-preview at temperature 0 (deterministic judgment)

Post-processor: _post_process_replies()
  - Deterministic mechanical fixes (punctuation, casing) — runs after final approval
  - Zero latency cost, 100% enforcement
"""

from typing import cast, Any, Literal
import asyncio
import base64
import json
import time

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agent.state import (
    AgentState,
    AnalystOutput,
    WriterOutput,
    StrategyOutput,
    StrategyLabel,
    ReplyOption,
)
from app.prompts.temperature import calculate_temperature
from app.services.memory_service import get_match_context
from app.config import settings
from app.infrastructure.database.engine import async_session

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LLM_TIMEOUT_SECONDS = 30
_LLM_MAX_RETRIES = 2
_REQUIRED_REPLY_COUNT = 4
_MAX_REWRITES = 1  # Max rewrite attempts before shipping as-is
_VISION_MODEL = "gemini-3.1-flash-lite-preview"
_GENERATOR_MODEL = "gemini-3.1-flash-lite-preview"
_AUDITOR_MODEL = "gemini-3.1-flash-lite-preview"

# MIME magic bytes for common image formats
_MIME_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # WebP starts with RIFF
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(val: Any, max_len: int = 220) -> Any:
    if isinstance(val, str):
        return val if len(val) <= max_len else val[: max_len - 3] + "..."
    if isinstance(val, list):
        return [_truncate(v, max_len=max_len) for v in val[:10]]
    if isinstance(val, dict):
        return {k: _truncate(v, max_len=max_len) for k, v in list(val.items())[:30]}
    return val


def _detect_mime_type(data: str | bytes) -> str:
    """Detect image MIME type from base64 string or raw bytes. Falls back to JPEG."""
    raw: bytes
    if isinstance(data, str):
        # Strip data URI prefix if present
        if data.startswith("data:image"):
            return data  # Already has MIME type embedded
        try:
            raw = base64.b64decode(data[:32])  # Only need first few bytes
        except Exception:
            return f"data:image/jpeg;base64,{data}"
    elif isinstance(data, (bytes, bytearray)):
        raw = bytes(data[:16])
    else:
        return f"data:image/jpeg;base64,{data}"

    for signature, mime in _MIME_SIGNATURES:
        if raw[: len(signature)] == signature:
            if isinstance(data, str):
                return f"data:{mime};base64,{data}"
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"

    # Default to JPEG
    if isinstance(data, str):
        return f"data:image/jpeg;base64,{data}"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _encode_image_from_state(state: AgentState) -> str:
    """Encode image from state with correct MIME type detection."""
    img = state.get("image_bytes")
    if img is None:
        raise ValueError("vision_node requires 'image_bytes' in state.")
    if isinstance(img, str) and img.startswith("data:image"):
        return img
    return _detect_mime_type(img)


def _normalize_raw_ocr_text(raw_ocr_text: Any) -> list[dict[str, Any]]:
    if raw_ocr_text is None:
        return []
    if isinstance(raw_ocr_text, str):
        return [
            {
                "sender": "them",
                "actual_new_message": raw_ocr_text,
                "quoted_context": None,
                "is_reply": False,
            }
        ]
    if isinstance(raw_ocr_text, list):
        normalized: list[dict[str, Any]] = []
        for item in raw_ocr_text:
            if hasattr(item, "model_dump"):
                normalized.append(cast(dict[str, Any], item.model_dump()))
            elif isinstance(item, dict):
                normalized.append(item)
        return normalized
    return []


def has_forbidden_punctuation(text: str) -> bool:
    forbidden = ["'", '"', ",", ".", "!", "?", ";"]
    return any(ch in text for ch in forbidden)


def _build_llm(
    *,
    model: str,
    temperature: float,
    structured_output: type[BaseModel] | None = None,
) -> Any:
    """Build a Gemini LLM client with timeout, retry, and optional structured output."""
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        timeout=_LLM_TIMEOUT_SECONDS,
        max_retries=_LLM_MAX_RETRIES,
    )
    if structured_output:
        return llm.with_structured_output(structured_output)
    return llm


# ---------------------------------------------------------------------------
# Librarian: shared DB engine (no per-call connection pool creation)
# ---------------------------------------------------------------------------


def _fetch_librarian_context(
    user_id: str,
    conversation_id: str,
    current_text: str,
) -> dict[str, str]:
    """Runs the async DB fetch using the shared engine (no new pool per call)."""

    async def _fetch() -> dict[str, str]:
        async with async_session() as local_db:
            return await get_match_context(
                local_db,
                user_id=user_id,
                conversation_id=conversation_id,
                current_text=current_text,
            )

    # LangGraph nodes run in threads via asyncio.to_thread, so we need a new loop
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_fetch())
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Node 1 schemas
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
    archetype_reasoning: str = Field(default="")
    detected_archetype: str = Field(default="THE WARM/STEADY")
    key_detail: str = Field(default="")
    person_name: str = Field(default="unknown")
    stage: str = Field(default="early_talking")
    their_last_message: str = Field(default="")


# ---------------------------------------------------------------------------
# Node 1 prompt
# ---------------------------------------------------------------------------

VISION_NODE_SYSTEM_PROMPT = """
You are a combined chat screenshot analyzer. Process the image in THREE sequential steps.

══════════════════════════════════════
STEP 1 — BOUNCER VALIDATION
══════════════════════════════════════
Decide if this image is a text message or dating app conversation screenshot.
- is_valid_chat = true → it contains chat bubbles (WhatsApp, Tinder, Bumble, iMessage, etc.)
- is_valid_chat = false → it is a random photo, menu, meme, blank screen, or non-chat image
- Provide a short bouncer_reason.

If is_valid_chat = false, stop here. Return empty arrays for all other fields.

══════════════════════════════════════
STEP 2 — OCR EXTRACTION (only if is_valid_chat = true)
══════════════════════════════════════
CRITICAL: Bubble ownership and quoted-reply splitting.
Read the image from top to bottom. For each message bubble:

1) Identify the Anchor (sender) using ONLY horizontal alignment:
   - LEFT-aligned bubble  → sender = "them"
   - RIGHT-aligned bubble → sender = "user"
   This sender is the ABSOLUTE source of truth for that bubble.
   Do NOT change sender because the quoted/faded text inside the bubble seems to belong to someone else.

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
STEP 3 — ANALYSIS (only if is_valid_chat = true)
══════════════════════════════════════
You are an expert social profiler. Use the Core Lore and Past Memories provided to interpret the
raw_ocr_text you extracted above. Do not just look at the words; look at the established relationship
dynamic to determine the vibe (e.g., if the lore says they tease each other, label
aggressive-sounding text as "playful/high-interest").

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

For ALL analysis fields below, use ONLY the most recent bubble where sender == "them",
and use ONLY its actual_new_message (ignore quoted_context entirely):

- detected_dialect: ENGLISH, HINDI, or HINGLISH based on her most recent bubble's actual_new_message.
- their_tone: excited / playful / flirty / neutral / dry / upset / testing / vulnerable / sarcastic
- their_effort: high / medium / low
- conversation_temperature: hot / warm / lukewarm / cold
- archetype_reasoning: FIRST, count how many words are in her most recent actual_new_message.
  THEN classify her message structure: is it a question? a statement? an emoji-only response?
  a sarcastic comeback with a specific punchline? a longer paragraph with a topic? a short
  "haha ok" filler? Write 2-3 sentences analyzing her MESSAGE STRUCTURE and EFFORT PATTERN
  before picking an archetype. Do NOT default to banter just because the message is playful —
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
- key_detail: One specific thing from her most recent actual_new_message to hook into.
- person_name: First name if discernible, else "unknown" (from her most recent actual_new_message).
- stage: new_match / opening / early_talking / building_chemistry / deep_connection / relationship / stalled / argument
- their_last_message: Short paraphrase of the other person's most recent message (use only the most
  recent sender=="them" bubble's actual_new_message, ignore quoted_context).

Return ALL fields. Populate everything.
"""


# ---------------------------------------------------------------------------
# Node 2 schemas
# ---------------------------------------------------------------------------


class GeneratorOutput(BaseModel):
    """Combined strategy + writer output from a single call with structured output."""

    # Strategy thinking
    wrong_moves: list[str] = Field(description="2-3 moves to avoid given the context.")
    right_energy: str = Field(description="Single best tone phrase.")
    hook_point: str = Field(description="The specific topic or detail to build around.")
    recommended_strategy_label: StrategyLabel = Field(
        description="ONE of: PUSH-PULL, FRAME CONTROL, SOFT CLOSE, VALUE ANCHOR, PATTERN INTERRUPT"
    )

    # Writer output — exactly 4 reply options
    replies: list[ReplyOption] = Field(
        description="Exactly 4 reply options. Exactly ONE must have is_recommended=true."
    )


# ---------------------------------------------------------------------------
# Node 2 prompt — conditional archetype injection
# ---------------------------------------------------------------------------

# Core prompt (always included) — kept concise to avoid "lost in the middle" effect
_GENERATOR_CORE_PROMPT = """
You are a dating text coach. Your job is to:
  PHASE 1 — decide the psychological strategy (no reply text yet)
  PHASE 2 — write exactly 4 reply options
  PHASE 3 — self-audit and fix any cringe before outputting

You will be given a JSON payload with:
  analysis, direction, person_name, core_lore, past_memories, transcript_text,
  voice_dna_dict, conversation_context_dict

══════════════════════════════════════
PHASE 1 — STRATEGY
══════════════════════════════════════
Match Identity: Respond to [person_name].
The Lore: Use core_lore to maintain the established dynamic.
The Memories: Use past_memories to reference inside jokes ONLY if they fit naturally.
The Transcript: Base the immediate reply on transcript_text (her latest actual new message).

{archetype_rules}

ESCALATION ROUTING WHEN CHAT IS HOT:
- If conversation_temperature is "hot" AND her message mentions meet-up logistics,
  treat this as a closing moment. recommended_strategy_label should be "SOFT CLOSE".

THE INTENTIONS OVERRIDE:
- If transcript contains talk about dating goals, "what are you looking for", or marriage,
  the archetype should already be GUARDED/TESTER. If it isn't, treat it as one anyway.
  Drop all cocky/push-pull banter. Use HONEST FRAME.
  WRONG_MOVES must include being evasive about seriousness.

CONVERSION RULE:
- Do NOT generate "SOFT CLOSE" or ask for number unless their_effort is HIGH or temperature is HOT.
- If she is LOW-INVESTMENT or WARM/STEADY with medium effort, your ONLY goal is to spark curiosity.

STRATEGY LABELS:
- PUSH-PULL: create tension with a mix of interest and playful withdrawal
- FRAME CONTROL: lead the conversation frame, redefine the dynamic
- SOFT CLOSE: gently escalate toward plans, number, or meeting
- VALUE ANCHOR: show substance, depth, or social proof
- PATTERN INTERRUPT: break the current dynamic with something unexpected
- HONEST FRAME: be direct, sincere, and clear (for GUARDED/TESTER and DE-ESCALATE)

Fill: wrong_moves (2-3), right_energy, hook_point, recommended_strategy_label

══════════════════════════════════════
PHASE 2 — WRITE 4 REPLIES
══════════════════════════════════════
Each must use a clearly different psychological angle.

LANGUAGE LOCK:
- Write replies in the EXACT language/script/slang identified in detected_dialect.
- If detected_dialect is HINGLISH, reply in Romanized Hindi-English mix.
- If detected_dialect is ENGLISH, write casual lowercase English ONLY. No Hinglish words.
- Match their vocabulary. If they say "yaar", you can use "yaar".

STYLE RULE:
- NO PROPER PUNCTUATION. No apostrophes, commas, periods, exclamation marks, question marks.
- "dont" not "don't". "im" not "i'm". "youre" not "you're".
- Lowercase only. You are a lazy high-status texter, not an English professor.

LENGTH & MIRRORING:
- Match her message length or be slightly shorter. Single punchy sentence or phrase.
- If she gives low effort, be equally brief and unbothered.

THE TENSION SUSPENSION RULE:
- If she playfully accuses you of something, NEVER confirm or deny. Suspend the tension.

VIBE CONTINUITY:
- Optimize for the USER'S established texting persona from voice_dna_dict.
- Do NOT switch styles even if her language shifts.

FRESHNESS PENALTY:
- conversation_context_dict may include recent tactics. Do NOT repeat the same strategy or phrases.
- Force creative divergence across all 4 suggestions.

{direction_rules}

VOICE DNA & CONTEXT:
- voice_dna_dict: match length, emojis, capitalization, punctuation, favorite words. Never violate dislikes.
- conversation_context_dict: use history, avoid exhausted topics, keep persona consistent.

For each reply fill: text, strategy_label, is_recommended (exactly ONE true), coach_reasoning

══════════════════════════════════════
PHASE 3 — SELF-AUDIT
══════════════════════════════════════
Check every reply against all rules. Fix inline before outputting.
- Apostrophes (') → rewrite without
- Exclamation/question marks → rewrite
- Commas or periods → rewrite
- Generic dating app opener or therapy speak → rewrite
- If ENGLISH dialect but reply has Hindi words → rewrite
- If direction is "opener" and reply lacks a specific visual_hook → rewrite
- Overly eager or explanatory → rewrite
- If asking for number but their_effort is LOW/MEDIUM and strategy is NOT "SOFT CLOSE" → rewrite as tease

Only output replies that pass ALL checks.
"""

# Archetype-specific prompt segments (only the relevant one is injected)
_ARCHETYPE_PROMPTS: dict[str, str] = {
    "THE BANTER GIRL": """
ARCHETYPE STRATEGY — THE BANTER GIRL:
- She is actively sparring — sarcasm, tests, punchlines. Match her energy.
- Prioritize PUSH-PULL and PATTERN INTERRUPT.
- Tone: cocky, playful, unbothered. Tease her, misinterpret her in a funny way, or flip tests back.
- Do NOT be sincere or reassuring — she wants a sparring partner, not a therapist.
- If she accuses you of something playfully, do NOT confirm or deny. Suspend the tension.""",

    "THE INTELLECTUAL": """
ARCHETYPE STRATEGY — THE INTELLECTUAL:
- She sent a substantive message with a real topic. Engage with it.
- Prioritize VALUE ANCHOR and FRAME CONTROL.
- Tone: witty, thoughtful, culturally aware. Reference ideas, observations, or shared interests.
- Show depth without writing a lecture — match her message length.
- Avoid low-effort one-liners; they signal you dont match her investment.""",

    "THE WARM/STEADY": """
ARCHETYPE STRATEGY — THE WARM/STEADY:
- She is being normal, friendly, and engaged. This is the most common archetype.
- Mix strategies: use PUSH-PULL lightly, VALUE ANCHOR for substance, FRAME CONTROL to lead.
- Tone: confident but warm. You can tease lightly but the base energy is friendly and interested.
- Do NOT go full cocky/sarcastic — she is not testing you, she is just talking.
- Do NOT be overly sincere or serious either — keep it light and fun.
- This is where most conversations live. Be the fun, confident version of yourself.""",

    "THE GUARDED/TESTER": """
ARCHETYPE STRATEGY — THE GUARDED/TESTER:
- She is screening you. This is NOT banter — she wants a real answer.
- Prioritize HONEST FRAME and VALUE ANCHOR.
- Tone: high-status sincerity. Be clear, direct, and honest without oversharing.
- STRICT: Do NOT deflect, dodge, or joke your way out of the question. Evasion is low-status.
- STRICT: Do NOT use PUSH-PULL or sarcasm — she will read it as avoidance.
- Show you have standards and know what you want. Confidence comes from clarity, not mystery.
- One reply can add a light human touch after the honest answer ("but honestly...").
- wrong_moves MUST include "being evasive" and "deflecting with humor".""",

    "THE EAGER/DIRECT": """
ARCHETYPE STRATEGY — THE EAGER/DIRECT:
- She is clearly interested and moving forward. Do NOT play games.
- Prioritize SOFT CLOSE and FRAME CONTROL.
- Tone: confident, warm, decisive. Match her energy and close the deal.
- If she mentions meeting up, be specific with plans (place, time, activity).
- If she is flirting explicitly, flirt back but lead toward logistics.
- Do NOT tease or create artificial tension — she is past that stage.
- At least one reply should include a concrete next step.""",

    "THE LOW-INVESTMENT": """
ARCHETYPE STRATEGY — THE LOW-INVESTMENT:
- Her entire message was under 4 words of filler. She is on autopilot.
- Prioritize PATTERN INTERRUPT to shake her out of it, or "walk away" energy.
- Tone: unbothered, high-standard. Do NOT over-explain or chase.
- Keep your replies SHORT — match or undercut her length. Do NOT write a paragraph.
- At least one reply should make it easy to gracefully disengage ("no stress if youre busy").
- At least one reply should be a bold, unexpected pattern interrupt.""",
}

# Direction-specific prompt segments (only the relevant one is injected)
_DIRECTION_PROMPTS: dict[str, str] = {
    "opener": """
DIRECTION — OPENER:
- FORBIDDEN: Do NOT say "hi", "hey", "hello", or any greeting.
- Generate a "Reaction Comment" for her profile photo using visual_hooks from the analysis.
- A good comment is a playful assumption based on a specific visual detail.
- Example: "i bet you spent more time picking that camera than actually taking photos with it".
- Every reply MUST reference a concrete visual detail — generic openers are cringe.""",

    "quick_reply": """
DIRECTION — QUICK REPLY:
- Standard conversational reply. Respond naturally to what she said.
- No special constraints — let the archetype strategy guide the tone.""",

    "change_topic": """
DIRECTION — CHANGE TOPIC:
- Use LONG TERM MEMORY & PROFILE CONTEXT from conversation_context_dict as your ONLY source for new topics.
- BANNED: pineapple on pizza, zombie apocalypse, teleportation, winning lottery, generic travel questions.
- Study the topic exhaustion map and do NOT repeat listed themes.
- Pivot to a genuinely fresh, specific angle grounded in their actual profile or earlier chemistry.""",

    "tease": """
DIRECTION — TEASE:
- The goal is playful teasing — misinterpret something she said in a funny way, make a cocky observation,
  or lightly challenge her.
- Tone: cocky-funny, not mean. The tease should make her laugh or roll her eyes, not feel attacked.
- At least 2 replies should use PUSH-PULL or PATTERN INTERRUPT.
- Do NOT tease about sensitive topics (appearance, intelligence, family).""",

    "revive_chat": """
DIRECTION — REVIVE CHAT:
- The conversation has gone quiet. Your job is a high-energy fresh restart.
- You MAY reference her last text with a twist ("wait i just realized..." or "ok but you never told me...")
  IF it creates a natural callback. You may also ignore it entirely and go fresh.
- At least one reply should be a bold, unexpected angle (not "hey how are you").
- At least one reply should reference something from core_lore or past_memories if available.""",

    "get_number": """
DIRECTION — GET NUMBER / MOVE OFF APP:
- At least one reply MUST include a clear transition to moving off the app.
- Use casual style: "whatsapp pe switch karein", "drop your number", etc.
- If temperature is "hot", be more direct and confident.
- If temperature is "warm", frame the close as a natural next step, not a demand.
- Teasing is allowed ONLY if it still leads to an explicit "move off app" line in that reply.""",

    "ask_out": """
DIRECTION — ASK OUT:
- The goal is to ASK THEM OUT. Be specific with a concrete plan.
- Include a place, activity, or time suggestion — not just "we should meet".
- Match the vibe: if the conversation is playful, frame the ask-out playfully.
- At least one reply should be a bold, direct ask. At least one can be a softer suggestion.""",

    "de_escalate": """
DIRECTION — DE-ESCALATE:
- She is upset, annoyed, testing aggressively, or the conversation has gotten tense.
- STRICT: Do NOT match her negative energy. Do NOT get defensive or sarcastic.
- STRICT: Do NOT dismiss her feelings ("chill", "relax", "its not that deep").
- Prioritize HONEST FRAME and VALUE ANCHOR.
- Tone: calm, grounded, accountable where appropriate. Show emotional maturity.
- Acknowledge what she said without being a pushover.
- At least one reply should be a brief, sincere acknowledgment.
- At least one reply should gently redirect to positive ground.
- If she is testing (not genuinely upset), one reply can call it out calmly.""",
}


def _build_generator_prompt(detected_archetype: str, direction: str) -> str:
    """Build the generator system prompt with only the relevant archetype and direction rules."""
    archetype_rules = _ARCHETYPE_PROMPTS.get(
        detected_archetype,
        _ARCHETYPE_PROMPTS["THE WARM/STEADY"],
    )
    direction_rules = _DIRECTION_PROMPTS.get(direction, "")

    return _GENERATOR_CORE_PROMPT.format(
        archetype_rules=archetype_rules,
        direction_rules=direction_rules,
    )


# ---------------------------------------------------------------------------
# Reply validation & backfill
# ---------------------------------------------------------------------------


def _validate_and_fix_replies(gen_out: GeneratorOutput) -> GeneratorOutput:
    """Ensure exactly 4 replies with exactly 1 recommended. Backfill if short."""
    replies = list(gen_out.replies)

    # Backfill if fewer than 4 replies
    while len(replies) < _REQUIRED_REPLY_COUNT:
        logger.warning("generator_backfill_reply", current_count=len(replies))
        # Clone the last reply with a different label as a fallback
        if replies:
            last = replies[-1]
            fallback_labels: list[StrategyLabel] = [
                "PUSH-PULL",
                "FRAME CONTROL",
                "SOFT CLOSE",
                "VALUE ANCHOR",
                "PATTERN INTERRUPT",
            ]
            used_labels = {r.strategy_label for r in replies}
            unused = [l for l in fallback_labels if l not in used_labels]
            label = unused[0] if unused else "PATTERN INTERRUPT"
            replies.append(
                ReplyOption(
                    text=last.text,
                    strategy_label=label,
                    is_recommended=False,
                    coach_reasoning="(auto-generated fallback)",
                )
            )
        else:
            break  # No replies at all — can't backfill from nothing

    # Truncate if more than 4
    replies = replies[:_REQUIRED_REPLY_COUNT]

    # Ensure exactly 1 recommended
    recommended_count = sum(1 for r in replies if r.is_recommended)
    if recommended_count == 0 and replies:
        replies[0] = replies[0].model_copy(update={"is_recommended": True})
    elif recommended_count > 1:
        seen_first = False
        for i, r in enumerate(replies):
            if r.is_recommended:
                if seen_first:
                    replies[i] = r.model_copy(update={"is_recommended": False})
                else:
                    seen_first = True

    return gen_out.model_copy(update={"replies": replies})


# ---------------------------------------------------------------------------
# Node 1: vision_node
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
    t0 = time.monotonic()
    user_id = state.get("user_id", "")
    logger.info("agent_v2_vision_start", user_id=user_id)

    image_url = _encode_image_from_state(state)
    core_lore = ""
    past_memories = ""

    # --- Librarian fetch (before the LLM call so lore is available) ---
    conversation_id = state.get("conversation_id")
    if conversation_id and user_id:
        try:
            librarian = _fetch_librarian_context(
                user_id=user_id,
                conversation_id=conversation_id,
                current_text=state.get("ocr_hint_text") or "",
            )
            core_lore = librarian.get("core_lore") or ""
            past_memories = librarian.get("past_memories") or ""
        except Exception as e:
            logger.warning("agent_v2_librarian_failed", error=str(e), user_id=user_id)

    # --- Single LLM call with structured output + timeout + retry ---
    llm = _build_llm(
        model=_VISION_MODEL,
        temperature=0,
        structured_output=VisionNodeOutput,
    )

    content = [
        {
            "type": "text",
            "text": (
                f"Core Lore:\n{core_lore}\n\n"
                f"Past Memories:\n{past_memories}\n\n"
                "Process this image through all three steps as instructed."
            ),
        },
        {"type": "image_url", "image_url": {"url": image_url}},
    ]

    t_call = time.monotonic()
    result = llm.invoke(
        [
            SystemMessage(content=VISION_NODE_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]
    )
    out = cast(VisionNodeOutput, result)
    llm_ms = int((time.monotonic() - t_call) * 1000)

    logger.info(
        "agent_v2_vision_done",
        total_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=llm_ms,
        is_valid_chat=out.is_valid_chat,
        bouncer_reason=_truncate(out.bouncer_reason),
        detected_dialect=out.detected_dialect,
        detected_archetype=out.detected_archetype,
        their_effort=out.their_effort,
        conversation_temperature=out.conversation_temperature,
        transcript_count=len(out.visual_transcript),
    )

    if not out.is_valid_chat:
        # Return only the keys this node owns (partial state update)
        return {
            "is_valid_chat": False,
            "bouncer_reason": out.bouncer_reason,
            "core_lore": core_lore,
            "past_memories": past_memories,
        }

    # Build AnalystOutput from VisionNodeOutput fields
    from agent.state import ChatBubble

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

    raw_ocr_text = _normalize_raw_ocr_text(out.raw_ocr_text)

    return {
        "is_valid_chat": True,
        "bouncer_reason": out.bouncer_reason,
        "raw_ocr_text": raw_ocr_text,
        "analysis": analysis,
        "core_lore": core_lore,
        "past_memories": past_memories,
    }


# ---------------------------------------------------------------------------
# Node 2: generator_node
# ---------------------------------------------------------------------------


def generator_node(state: AgentState) -> dict:
    """
    Gemini call with structured output that performs:
      1. Strategy decision (wrong moves, right energy, hook point, label)
      2. Write 4 reply options
      3. On rewrites: incorporates auditor feedback to fix flagged replies

    Uses dynamic temperature from direction × conversation state.
    Returns partial state update (LangGraph merges into full state).
    """
    t0 = time.monotonic()
    user_id = state.get("user_id", "")
    revision_count = state.get("revision_count", 0)
    auditor_feedback = state.get("auditor_feedback", "")
    is_rewrite = revision_count > 0 and bool(auditor_feedback)

    analysis = state.get("analysis")
    if analysis is None:
        raise ValueError("generator_node requires 'analysis' in state.")
    # LangGraph may serialize Pydantic models to dict or str when passing state
    if isinstance(analysis, dict):
        analysis = AnalystOutput(**analysis)
    elif isinstance(analysis, str):
        analysis = AnalystOutput(**json.loads(analysis))

    direction = state.get("direction", "quick_reply")
    voice_dna = state.get("voice_dna_dict", {})
    conversation_context = state.get("conversation_context_dict", {})
    core_lore = state.get("core_lore", "") or ""
    past_memories = state.get("past_memories", "") or ""

    # Resolve person_name from context or analysis
    person_name = getattr(analysis, "person_name", None) or "unknown"
    convo_ctx_person = (conversation_context or {}).get("person_name")
    if convo_ctx_person and str(convo_ctx_person).lower() != "unknown":
        person_name = str(convo_ctx_person)

    # Build transcript_text from the latest "them" bubble
    transcript_text = ""
    for bubble in reversed(getattr(analysis, "visual_transcript", []) or []):
        if getattr(bubble, "sender", "") == "them":
            transcript_text = getattr(bubble, "actual_new_message", "") or ""
            break
    if not transcript_text:
        for bubble in reversed(getattr(analysis, "visual_transcript", []) or []):
            actual = getattr(bubble, "actual_new_message", "") or ""
            if actual:
                transcript_text = actual
                break

    # --- Dynamic temperature from the matrix ---
    conversation_temperature = (
        getattr(analysis, "conversation_temperature", "warm") or "warm"
    )
    stage = getattr(analysis, "stage", "early_talking") or "early_talking"
    interaction_count = (conversation_context or {}).get("interaction_count", 0)
    llm_temperature = calculate_temperature(
        direction=direction,
        conversation_temperature=conversation_temperature,
        stage=stage,
        interaction_count=(
            interaction_count if isinstance(interaction_count, int) else 0
        ),
    )

    detected_archetype = (
        getattr(analysis, "detected_archetype", "THE LOW-INVESTMENT")
        or "THE LOW-INVESTMENT"
    )

    logger.info(
        "agent_v2_generator_start",
        user_id=user_id,
        direction=direction,
        is_rewrite=is_rewrite,
        revision_count=revision_count,
        person_name=person_name,
        detected_archetype=detected_archetype,
        detected_dialect=getattr(analysis, "detected_dialect", None),
        their_effort=getattr(analysis, "their_effort", None),
        conversation_temperature=conversation_temperature,
        stage=stage,
        llm_temperature=llm_temperature,
        transcript_text=_truncate(transcript_text, max_len=120),
    )

    payload: dict[str, Any] = {
        "analysis": analysis.model_dump(),
        "direction": direction,
        "person_name": person_name,
        "core_lore": core_lore,
        "past_memories": past_memories,
        "transcript_text": transcript_text,
        "voice_dna_dict": voice_dna,
        "conversation_context_dict": conversation_context,
    }

    semantic_profile = (
        voice_dna.get("semantic_profile") if isinstance(voice_dna, dict) else None
    )
    if semantic_profile:
        payload["USER_PSYCHOLOGICAL_STYLE_GUIDE"] = (
            f"CRITICAL — match this style in every reply: {semantic_profile}"
        )

    # --- On rewrite: inject the previous drafts + auditor feedback ---
    if is_rewrite:
        prev_drafts = state.get("drafts")
        if prev_drafts:
            if isinstance(prev_drafts, dict):
                payload["previous_replies"] = prev_drafts
            elif hasattr(prev_drafts, "model_dump"):
                payload["previous_replies"] = prev_drafts.model_dump()
        payload["AUDITOR_FEEDBACK"] = (
            "CRITICAL: Your previous replies were rejected by the quality auditor. "
            "Fix the specific issues below while keeping what worked. "
            "Do NOT just regenerate from scratch — improve the flagged replies.\n\n"
            f"{auditor_feedback}"
        )

    # --- Build conditional prompt (only relevant archetype + direction injected) ---
    system_prompt = _build_generator_prompt(detected_archetype, direction)

    # --- Structured output LLM call with dynamic temperature + timeout + retry ---
    llm = _build_llm(
        model=_GENERATOR_MODEL,
        temperature=llm_temperature,
        structured_output=GeneratorOutput,
    )

    t_call = time.monotonic()
    try:
        result = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=json.dumps(payload)),
            ]
        )
        gen_out = cast(GeneratorOutput, result)
    except Exception as e:
        logger.error(
            "agent_v2_generator_llm_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=int((time.monotonic() - t_call) * 1000),
        )
        raise
    llm_ms = int((time.monotonic() - t_call) * 1000)

    # --- Validate reply count and fix if needed ---
    gen_out = _validate_and_fix_replies(gen_out)

    # Build StrategyOutput and WriterOutput from GeneratorOutput
    strategy = StrategyOutput(
        wrong_moves=gen_out.wrong_moves,
        right_energy=gen_out.right_energy,
        hook_point=gen_out.hook_point,
        recommended_strategy_label=gen_out.recommended_strategy_label,
    )
    drafts = WriterOutput(replies=gen_out.replies)

    recommended_idx = next(
        (i for i, r in enumerate(gen_out.replies) if r.is_recommended), -1
    )

    logger.info(
        "agent_v2_generator_done",
        user_id=user_id,
        total_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=llm_ms,
        llm_temperature=llm_temperature,
        is_rewrite=is_rewrite,
        reply_count=len(gen_out.replies),
        strategy_labels=[r.strategy_label for r in gen_out.replies],
        recommended_index=recommended_idx,
    )

    return {
        "strategy": strategy,
        "drafts": drafts,
        "revision_count": revision_count + 1,
        # Clear auditor feedback after consuming it
        "auditor_feedback": "",
        "is_cringe": False,
    }


# ---------------------------------------------------------------------------
# Node 3: auditor_node — quality evaluator
# ---------------------------------------------------------------------------


# Structured output schema for per-reply evaluation
class ReplyVerdict(BaseModel):
    reply_index: int = Field(description="0-based index of the reply being evaluated.")
    passes: bool = Field(description="true if this reply is good enough to ship.")
    issue: str = Field(
        default="",
        description=(
            "If passes=false, a specific 1-sentence description of what's wrong. "
            "Be precise: 'Reply 2 uses sarcasm for a SOFT/TRADITIONAL archetype' "
            "not 'Reply 2 is bad'."
        ),
    )


class AuditorNodeOutput(BaseModel):
    """Structured auditor evaluation of all 4 replies."""

    overall_passes: bool = Field(
        description="true if ALL replies are good enough to ship without rewrite."
    )
    verdicts: list[ReplyVerdict] = Field(
        description="One verdict per reply. Must have exactly 4 entries."
    )
    summary: str = Field(
        description=(
            "If overall_passes=false, a 2-3 sentence summary of the main issues "
            "and what the generator should fix on rewrite. If overall_passes=true, "
            "write 'All replies pass quality check.'"
        ),
    )


_AUDITOR_SYSTEM_PROMPT = """
You are a quality auditor for AI-generated dating reply suggestions.
You receive the conversation analysis and 4 generated replies.
Your job: evaluate whether each reply is good enough to show to the user.

NOTE: Punctuation, capitalization, and formatting are fixed automatically by code
after your review. Do NOT evaluate or fail replies for style/punctuation issues.
Focus ONLY on substantive quality:

1. CONTEXT FIT: Does the reply actually respond to what she said (transcript_text)?
   A reply that ignores her message or talks about something unrelated = FAIL.

2. ARCHETYPE MATCH: Does the tone match the detected archetype?
   - BANTER GIRL → cocky, teasing, sparring. NOT sincere/serious.
   - INTELLECTUAL → witty, thoughtful, depth. NOT shallow one-liners.
   - WARM/STEADY → confident but warm, light teasing ok. NOT full cocky or overly serious.
   - GUARDED/TESTER → honest, direct, sincere. NOT evasive, deflecting, or sarcastic.
   - EAGER/DIRECT → decisive, warm, leading. NOT playing games or creating artificial tension.
   - LOW-INVESTMENT → unbothered, high-standard. NOT chasing or over-explaining.
   Wrong energy for the archetype = FAIL.

3. DIRECTION COMPLIANCE: Does the reply fulfill the requested direction?
   - "get_number" → at least one reply must include a move-off-app line
   - "opener" → must reference a visual detail, NOT a generic greeting
   - "ask_out" → must include a concrete plan (place/time/activity)
   - "de_escalate" → must NOT be sarcastic, defensive, or dismissive
   - "tease" → must be playful, not mean or generic
   Direction violated = FAIL.

4. CRINGE / GENERIC: Would a real person actually send this?
   - Corporate jargon, therapy speak, motivational quotes = FAIL
   - Overly eager ("I'd love to get to know you more!") = FAIL
   - Generic ("What are you up to?", "How's your day?") = FAIL for most directions

5. DIVERSITY: Are all 4 replies using clearly different angles?
   If 3+ replies feel like variations of the same approach = FAIL the weakest one.

6. DIALECT MATCH: If detected_dialect is HINGLISH, replies must be in Hinglish.
   If ENGLISH, replies must NOT contain Hindi words. Mismatch = FAIL.

BE STRICT BUT FAIR:
- A reply doesn't need to be perfect. It needs to be good enough to send.
- If 2+ replies have substantive issues, fail overall with clear rewrite instructions.
- Do NOT fail replies for punctuation, capitalization, or formatting — code handles that.
- Do NOT fail replies just because you'd write them differently. Fail only for
  objective rule violations listed above.

Return your evaluation as structured output.
"""


def auditor_node(state: AgentState) -> dict:
    """
    Evaluates the quality of generated replies against context, archetype,
    direction, and style rules.

    Returns:
      - is_cringe: True if replies need a rewrite
      - auditor_feedback: Specific instructions for the generator on what to fix
    """
    t0 = time.monotonic()
    user_id = state.get("user_id", "")
    revision_count = state.get("revision_count", 0)

    analysis = state.get("analysis")
    if isinstance(analysis, dict):
        analysis = AnalystOutput(**analysis)
    elif isinstance(analysis, str):
        analysis = AnalystOutput(**json.loads(analysis))

    drafts = state.get("drafts")
    if drafts is None:
        logger.warning("auditor_node_no_drafts", user_id=user_id)
        return {"is_cringe": False, "auditor_feedback": ""}

    if isinstance(drafts, dict):
        drafts = WriterOutput(**drafts)
    elif isinstance(drafts, str):
        drafts = WriterOutput(**json.loads(drafts))

    # Safety valve: if we've already rewritten max times, approve regardless
    if revision_count > _MAX_REWRITES:
        logger.info(
            "auditor_node_max_rewrites_reached",
            user_id=user_id,
            revision_count=revision_count,
        )
        return {"is_cringe": False, "auditor_feedback": ""}

    direction = state.get("direction", "quick_reply")

    # Build a concise evaluation payload (don't send the whole kitchen sink)
    eval_payload = {
        "detected_archetype": getattr(analysis, "detected_archetype", ""),
        "detected_dialect": getattr(analysis, "detected_dialect", "ENGLISH"),
        "their_tone": getattr(analysis, "their_tone", ""),
        "their_effort": getattr(analysis, "their_effort", ""),
        "conversation_temperature": getattr(analysis, "conversation_temperature", ""),
        "stage": getattr(analysis, "stage", ""),
        "transcript_text": getattr(analysis, "their_last_message", ""),
        "key_detail": getattr(analysis, "key_detail", ""),
        "direction": direction,
        "replies": [
            {
                "index": i,
                "text": r.text,
                "strategy_label": r.strategy_label,
                "is_recommended": r.is_recommended,
                "coach_reasoning": r.coach_reasoning,
            }
            for i, r in enumerate(drafts.replies[:4])
        ],
    }

    llm = _build_llm(
        model=_AUDITOR_MODEL,
        temperature=0,  # Deterministic judgment
        structured_output=AuditorNodeOutput,
    )

    t_call = time.monotonic()
    try:
        result = llm.invoke(
            [
                SystemMessage(content=_AUDITOR_SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(eval_payload)),
            ]
        )
        audit = cast(AuditorNodeOutput, result)
    except Exception as e:
        # Auditor failure should never block the response — approve and ship
        logger.error(
            "auditor_node_llm_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {"is_cringe": False, "auditor_feedback": ""}

    llm_ms = int((time.monotonic() - t_call) * 1000)

    failed_verdicts = [v for v in audit.verdicts if not v.passes]

    logger.info(
        "agent_v2_auditor_done",
        user_id=user_id,
        llm_ms=llm_ms,
        overall_passes=audit.overall_passes,
        failed_count=len(failed_verdicts),
        failed_indices=[v.reply_index for v in failed_verdicts],
        summary=_truncate(audit.summary, max_len=200),
        revision_count=revision_count,
    )

    if audit.overall_passes:
        return {"is_cringe": False, "auditor_feedback": ""}

    # Build structured feedback for the generator
    feedback_lines = [audit.summary, ""]
    for v in failed_verdicts:
        feedback_lines.append(f"- Reply {v.reply_index}: {v.issue}")

    return {
        "is_cringe": True,
        "auditor_feedback": "\n".join(feedback_lines),
    }


# ---------------------------------------------------------------------------
# Deterministic post-processor — runs after auditor approves, before shipping
# ---------------------------------------------------------------------------


def _post_process_replies(drafts: WriterOutput) -> WriterOutput:
    """
    Deterministic mechanical fixes applied after auditor approval.
    Zero latency cost, 100% enforcement of style rules.
    """
    fixed_replies = []
    for r in drafts.replies:
        text = r.text
        # Strip forbidden punctuation
        for ch in ["'", ",", ".", "!", "?", '"', ";"]:
            text = text.replace(ch, "")
        # Force lowercase
        text = text.lower().strip()
        # Collapse double spaces from punctuation removal
        while "  " in text:
            text = text.replace("  ", " ")
        fixed_replies.append(r.model_copy(update={"text": text}))
    return WriterOutput(replies=fixed_replies)
