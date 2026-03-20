from typing import cast, Any, Literal
import asyncio
import base64
import json
import time

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.prompts.temperature import calculate_temperature
from agent.state import (
    AgentState,
    AnalystOutput,
    StrategyOutput,
    WriterOutput,
    AuditorOutput,
    BouncerOutput,
)
from app.services.memory_service import get_match_context
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


logger = structlog.get_logger(__name__)


def _truncate(val: Any, max_len: int = 220) -> Any:
    """Truncate noisy strings/lists for logs (never touch base64/image)."""
    if isinstance(val, str):
        if len(val) <= max_len:
            return val
        return val[: max_len - 3] + "..."
    if isinstance(val, list):
        # keep list shape but truncate items
        return [_truncate(v, max_len=max_len) for v in val[:10]]
    if isinstance(val, dict):
        return {k: _truncate(v, max_len=max_len) for k, v in list(val.items())[:30]}
    return val


def _state_meta(state: AgentState) -> dict[str, Any]:
    analysis = state.get("analysis")
    return {
        "direction": state.get("direction"),
        "revision_count": state.get("revision_count", 0),
        "is_valid_chat": state.get("is_valid_chat", None),
        "is_cringe": state.get("is_cringe", None),
        "detected_archetype": getattr(analysis, "detected_archetype", None),
        "conversation_temperature": getattr(analysis, "conversation_temperature", None),
        "detected_dialect": getattr(analysis, "detected_dialect", None),
    }


def has_forbidden_punctuation(text: str) -> bool:
    forbidden = ["'", '"', ",", ".", "!", "?", ";"]
    return any(ch in text for ch in forbidden)


from pydantic import BaseModel, Field

class RawOcrTextItem(BaseModel):
    sender: Literal["user", "them"] = Field(
        description="Bubble anchor sender derived from horizontal alignment: left='them', right='user'."
    )
    actual_new_message: str = Field(
        description="Bold/solid fresh text below any quoted (faded) block."
    )
    quoted_context: str | None = Field(
        description="Top nested/faded quoted block text (or null if none)."
    )
    is_reply: bool = Field(
        description="true iff quoted_context is present for this bubble."
    )

class OcrExtractorOutput(BaseModel):
    # Strict schema used by downstream analyst_node.
    raw_ocr_text: list[RawOcrTextItem] = Field(
        description=(
            "List of extracted bubble objects. sender is absolute from bubble alignment. "
            "quoted_context is only the faded quoted block at the top of the bubble."
        )
    )


def _normalize_raw_ocr_text(raw_ocr_text: Any) -> list[dict[str, Any]]:
    """
    Convert `raw_ocr_text` into plain JSON-serializable dicts.

    The LLM structured output uses Pydantic models; the rest of the pipeline
    expects simple lists/dicts (for json.dumps and embeddings).
    """
    if raw_ocr_text is None:
        return []
    if isinstance(raw_ocr_text, str):
        # If a caller somehow passes a string, keep it as a single blob.
        return [{"sender": "them", "actual_new_message": raw_ocr_text, "quoted_context": None, "is_reply": False}]
    if isinstance(raw_ocr_text, list):
        normalized: list[dict[str, Any]] = []
        for item in raw_ocr_text:
            if hasattr(item, "model_dump"):
                normalized.append(cast(dict[str, Any], item.model_dump()))
            elif isinstance(item, dict):
                normalized.append(item)
        return normalized
    return []

OCR_EXTRACTOR_SYSTEM_PROMPT = """
You are a precise OCR extractor. Your ONLY job is to extract the text verbatim from the chat screenshot.

CRITICAL: Bubble ownership and quoted-reply splitting
Read the image from top to bottom. For each message bubble:

1) Identify the Anchor (sender) using ONLY horizontal alignment:
- LEFT-aligned bubble => sender = "them"
- RIGHT-aligned bubble => sender = "user"

This sender is the ABSOLUTE source of truth for that bubble.
Do NOT change sender because the quoted/faded text inside the bubble seems to belong to someone else.

2) Detect Quoted Layers (quoted_context):
- If there is a nested/grey/indented faded quoted block at the TOP of the bubble, extract that quoted block text.
- If there are multiple faded nested quote blocks at the top, extract all of them and join them with newline characters.
- If there is no quoted/faded block at the top, set quoted_context = null.

3) Actual Message (actual_new_message):
- Extract the bold/solid actual fresh message BELOW the quoted_context (the bottom-most solid text in the bubble).
- actual_new_message MUST NOT include any faded/quoted text.

4) is_reply:
- true iff quoted_context is not null and not empty.

Return ONLY data that matches this schema:
raw_ocr_text is a list of objects with keys: sender, actual_new_message, quoted_context, is_reply.

Do not translate or summarize. Extract the exact text, emojis, and punctuation as they appear on screen.
"""

ANALYST_SYSTEM_PROMPT = """
You are an expert social profiler. Use the Core Lore and Past Memories to interpret the Raw OCR Text. Do not just look at the words; look at the established relationship dynamic to determine the vibe (e.g., if the lore says they tease each other, label aggressive-sounding text as "playful/high-interest").

You are also provided the screenshot image. Use it strictly to extract `visual_hooks` (3-4 specific physical or environmental details from the photos). DO NOT read the text from the image for conversation analysis, use the provided Raw OCR Text instead.

From the image:
- Extract 3-4 visual_hooks (e.g. "Wearing a high-end watch", "In a library", "Holding a specific breed of dog").

From the Raw OCR Text:
- The Raw OCR Text is a JSON list of objects under `raw_ocr_text`.
- Build `visual_transcript` by mapping each object 1:1 into a `ChatBubble`:
  - `sender` = item.sender (absolute bubble alignment; do NOT infer from text)
  - `quoted_context` = item.quoted_context or "" if null
  - `actual_new_message` = item.actual_new_message
- Ownership rule for analysis:
  - `actual_new_message` always belongs to the bubble's `sender`.
  - `quoted_context` is past context and MUST NOT be used as the "latest actual message" for her last message.
- THEIR_LAST_MESSAGE: Use ONLY the most recent bubble in `visual_transcript` where `sender == "them"`, and paraphrase ONLY that bubble's `actual_new_message` (ignore quoted_context).
- DETECTED_DIALECT: ENGLISH, HINDI, or HINGLISH based on her most recent bubble's `actual_new_message` (ignore `quoted_context`).
- THEIR_TONE: excited / playful / flirty / neutral / dry / upset / testing / vulnerable / sarcastic (based on her most recent `actual_new_message`).
- THEIR_EFFORT: high / medium / low (based on her most recent `actual_new_message`).
- CONVERSATION_TEMPERATURE: hot / warm / lukewarm / cold (based on her most recent `actual_new_message`).
- KEY_DETAIL: One specific thing from her most recent `actual_new_message` to hook into.
- PERSON_NAME: First name if discernible, else "unknown" (from her most recent `actual_new_message`).
- STAGE: new_match / opening / early_talking / building_chemistry / deep_connection / relationship / stalled / argument.
- THEIR_LAST_MESSAGE: Short paraphrase of the other person's most recent message (use only the most recent sender=="them" bubble's `actual_new_message`, ignore `quoted_context`).

DETECTED_ARCHETYPE (CHOOSE EXACTLY ONE BASED ON HER BEHAVIOR):
- "THE BANTER GIRL": Uses sarcasm, witty comebacks, and tests you playfully.
- "THE INTELLECTUAL": Sends longer texts, jumps into deeper topics.
- "THE SOFT/TRADITIONAL": Polite, literal, often uses soft emojis like ✨.
- "THE LOW-INVESTMENT": Short, dry replies like "haha", "yeah", "Nahi".

ARCHETYPE_REASONING: One short sentence explaining WHY you chose that archetype, grounded in HER actual new message and recent behavior.

You must return a JSON object that matches the `AnalystOutput` schema exactly.
"""


STRATEGIST_SYSTEM_PROMPT = """
You are the Chef. Your ONLY job is to decide the psychological strategy, not to write any replies.

Match Identity: Respond to [person_name].

The Lore: Use the [core_lore] to maintain the established relationship dynamic
(for example: if she is bossy, be a playful brat).

The Memories: Use [past_memories] to reference inside jokes ONLY if they fit the
current topic naturally.

The Transcript: Base the immediate reply on the current screenshot text
(the latest transcript_text).

Tone: Ensure the final generated reply is in high-status 'Hinglish' and matches the
energy level found in the Lore.

You will be given:
- A structured analysis of the screenshot (`analysis`) including:
  - detected_dialect
  - their_tone
  - their_effort
  - conversation_temperature
  - detected_archetype
  - archetype_reasoning
  - key_detail
- A Librarian context dictionary (`librarian`) including:
  - person_name
  - core_lore
  - past_memories
- The user's requested direction (e.g. "get_number", "ask_out", "revive_chat", "change_topic")
- A conversation context dictionary with any extra metadata about stage, history, and prior tactics.
- The latest transcript_text (current screenshot text)

Use ONLY this information to decide:
- WRONG_MOVES: 2-3 things that would be bad to say right now.
- RIGHT_ENERGY: the single best tone/energy for the next message.
- HOOK_POINT: the specific detail or topic to build around.
- recommended_strategy_label: which core move the writer should prioritize.

ARCHETYPE-BASED STRATEGY ROUTING (STRICT GUARDRAILS):
- IF DETECTED_ARCHETYPE == "THE BANTER GIRL":
  - Prioritize PUSH-PULL and PATTERN INTERRUPT style replies. Most options should be labeled "PUSH-PULL" or "PATTERN INTERRUPT".
  - Tone: cocky, playful, unbothered. Tease her, misinterpret her in a funny way, or flip tests back on her.
  - Avoid overly sincere or needy reassurance; she enjoys sparring.
- IF DETECTED_ARCHETYPE == "THE INTELLECTUAL":
  - Prioritize VALUE ANCHOR and FRAME CONTROL. Most options should be labeled "VALUE ANCHOR" or "FRAME CONTROL".
  - Tone: witty, thoughtful, culturally aware. Reference ideas, books, or subtle observations instead of surface-level flirting.
  - Avoid low-effort one-liners; show depth without writing a lecture.
- IF DETECTED_ARCHETYPE == "THE SOFT/TRADITIONAL":
  - STRICT: Do NOT use dry sarcasm, negging, or aggressive teasing. Avoid replies that could be misread as mean or dismissive.
  - Prioritize warmth/safety and soft closes: use "SOFT CLOSE" strategy for gentle escalations, and use your wording to make her feel safe, seen, and respected.
  - Tone: clear, direct, comforting. Validate her feelings, be kind, and keep ambiguity low so she never has to guess if you are mocking her.
- IF DETECTED_ARCHETYPE == "THE LOW-INVESTMENT":
  - Prioritize PATTERN INTERRUPT style moves that shake her out of autopilot, or calmly "walk away" energy (low investment from the user).
  - Tone: unbothered, high-standard. Do NOT over-explain or chase; never reward low-effort one-word answers with big emotional investment.
  - At least one path should make it easy for the user to gracefully disengage if her effort stays low.

ESCALATION ROUTING WHEN CHAT IS HOT (CRITICAL):
- If conversation_temperature is "hot" AND her actual new message clearly mentions a specific meet-up activity or logistics
  (for example: coffee, drinks, a date, choosing a place/time, or her preferences about those),
  you MUST treat this as a logistics/closing moment, not a banter moment.
- In this case, you MUST prioritize SOFT CLOSE over pure teasing:
  - The recommended_strategy_label should usually be "SOFT CLOSE".
  - You should NOT choose a strategy whose primary energy is teasing/banter unless it still moves logistics forward instead of derailing.
- Once she starts discussing date logistics or concrete preferences (like coffee type, location, or timing),
  you MUST stop pure banter. Focus on clarity, comfort, and gently locking in plans instead of continuing playful tests.

THE INTENTIONS OVERRIDE (CRITICAL):
- If the transcript contains explicit talk about dating goals, casual vs serious, "no casual", "what are you looking for", or marriage,
  you MUST immediately drop all "cocky/mysterious/push-pull" banter as the dominant energy.
- Shift the strategy to "High-Status Sincerity":
  - Be clear and honest about intentions without oversharing or chasing.
  - Use grounded, relatable humor (e.g., joking about wedding costs, moving too fast) to release pressure while clearly respecting her boundaries.
  - NEVER be evasive when she asks direct questions about intentions; avoidance is low-status.
  - Your WRONG_MOVES should explicitly include being evasive, deflecting, or doubling down on mystery when she is asking about seriousness.

CONVERSION RULE (INVESTMENT THRESHOLD — CRITICAL):
DO NOT generate a "SOFT CLOSE" or ask for a number/WhatsApp unless `their_effort` is HIGH or `conversation_temperature` is HOT.
If the girl is "Low-Investment" or "Warm-Neutral", your ONLY goal is to spark curiosity and build tension.
Use "Pull" energy: Be slightly more detached. Make her feel like she has to work to keep your attention.
The ultimate "Win" is not you asking her out; it is her asking "So what do you do?" or "When are we meeting?"

Given the analysis, direction, and context:
- Choose 2–3 clear WRONG_MOVES that violate the archetype rules, the temperature, or the direction.
- Choose a single RIGHT_ENERGY phrase (e.g. "playful but grounded", "soft and reassuring", "high standard, unbothered").
- Set recommended_strategy_label to one of: "PUSH-PULL", "FRAME CONTROL", "SOFT CLOSE", "VALUE ANCHOR", "PATTERN INTERRUPT".

You MUST respond ONLY with a JSON object that matches the StrategyOutput schema exactly.
"""


WRITER_SYSTEM_PROMPT = """
You are a dating text coach and reply writer. Your ONLY job in this node is to generate 4 candidate replies based on:
- The structured analysis (`analysis`)
- The chosen psychological strategy (`strategy`)
- The user's direction (e.g. "get_number", "ask_out", "revive_chat", "change_topic")
- The conversation context and Voice DNA dictionaries.

══════════════════════════════════════
LANGUAGE LOCK
══════════════════════════════════════
- You MUST write your 4 replies in the EXACT language, script, and slang style identified in DETECTED_LANGUAGE_AND_VIBE / detected_dialect.
- If the chat uses Hinglish (Hindi written in English letters, like "meri yaad aari kya"), your replies MUST be natively written in Hinglish.
- DO NOT translate their non-English messages into English replies.
- Match their vocabulary. If they say "yaar", you can use "yaar".
- STRICT REQUIREMENT: If the detected_dialect is ENGLISH, you must write in casual, lowercase English. Do NOT use Hinglish words like "bada," "hai," or "kyun" if the profile suggests she does not speak Hindi. A "natural Indian vibe" for an English speaker means using Indian-English slang (e.g., "bro," "scene," "sorted"), not switching languages.
- STRICT REQUIREMENT: If detected_dialect is HINGLISH, you must use a mix of Hindi and English in roman script (e.g., "bada unique vibe hai"). If detected_dialect is ENGLISH, stay in lowercase, lazy English only.
- If she is speaking Hindi/Hinglish, you MUST reply in Hinglish. Use Romanized Hindi (e.g., "mera matlab tha..." instead of "i meant...") to make sure she actually gets the joke.

══════════════════════════════════════
STYLE RULE (FAILING THIS GETS YOU FIRED)
══════════════════════════════════════
- NO PROPER PUNCTUATION ALLOWED. NONE.
- YOU ARE STRICTLY FORBIDDEN FROM USING APOSTROPHES (').
- DO NOT write "don't", write "dont".
- DO NOT write "i'm", write "im".
- DO NOT write "can't", write "cant".
- DO NOT use exclamation marks (!), question marks (?), or quotation marks (" ") in the actual reply text.
- STYLE: No apostrophes, no commas, no periods. Just raw, high-status energy.
- Use lowercase letters ONLY. You are a lazy, high-status Indian texter, not an English professor.

CRITICAL: You are an Indian guy texting on 2% battery while walking.

YOU DO NOT HAVE THE TIME OR ENERGY FOR APOSTROPHES.

'you are' becomes 'youre' or 'u r'.

'don't' becomes 'dont'.

'I am' becomes 'im'.

IF YOU USE A COMMA OR AN APOSTROPHE, THE SYSTEM WILL CRASH.

WRITE IN RAW LOWERCASE ONLY.

══════════════════════════════════════
LENGTH & MIRRORING PROTOCOL
══════════════════════════════════════
- NEVER use explicit word counts. Instead, use structural constraints: your reply must be a single, punchy sentence or phrase.
- THE MIRROR RULE: Look at the length of her last message in the transcript. Your reply must roughly match her length or be slightly shorter.
- If she is giving low effort / short texts, you must be equally brief and unbothered.
- VISUAL RULE: The text should read like a quick, passing thought typed with one thumb while walking.

THE TENSION SUSPENSION RULE:
- If the match playfully accuses the user of something (e.g., being AI, a catfish, a player), NEVER confirm or deny it.
- Do NOT say "busted" or "you caught me" or clearly admit/deny the accusation.
- Your goal is to suspend the tension. Give an ambiguous, slightly cocky reply that leaves her guessing.
- Make her work to figure out if you are joking or serious.
- Example: If she says "You look like AI", reply with something like "wait till you see my real-world rendering" rather than "haha yes i am a bot".

══════════════════════════════════════
MAINTAIN VIBE CONTINUITY
══════════════════════════════════════
- You are optimizing for the USER'S established texting persona, not blindly mirroring every shift in her messages.
- You will be given RECENT HISTORY style information via `voice_dna_dict` and `conversation_context_dict`.
- If the RECENT HISTORY shows the user speaking in casual Hinglish, lowercase, with no periods, you MUST keep this exact dialect, casing, and punctuation pattern in ALL generated replies — even if the girl's actual_new_message is in more formal English.
- Do NOT suddenly switch to formal English or proper punctuation if that breaks the established high-status, casual Delhi/Indian vibe of the user.
- Do NOT mirror her language shifts if they conflict with this established persona. Your job is to keep the user's tone, slang, and swagger consistent across replies.

══════════════════════════════════════
FRESHNESS PENALTY & STRATEGY ROTATION (CRITICAL)
══════════════════════════════════════
- `conversation_context_dict` may include a "RECENT TACTICS USED" style list showing how the user recently replied.
- You MUST NOT copy-paste the same conversational structure or psychological strategy as those recent tactics.
- If the recent replies were teasing or heavy banter, you must pivot to validation, logistics, or a different frame (do NOT stack the same tease structure again).
- Do NOT reuse distinctive adjectives or metaphors (for example "chaotic", "dangerous", "trouble") if they appeared in the last few turns. Choose fresh descriptors.
- Force creative divergence across your 4 suggestions: each reply must use a clearly different psychological angle (e.g., one playful, one validating, one logistical, one challenging), not four minor rewrites of the same move.

══════════════════════════════════════
VOICE DNA & CONTEXT BLOCKS (FORMAT AWARENESS)
══════════════════════════════════════
Treat the following state dictionaries as if they had already been formatted using the PromptEngine helpers:
- `voice_dna_dict` → behaves like the _build_voice_dna_block output. Use it to match length, emojis, capitalization, punctuation style, and favorite words. Never violate hard dislikes.
- `conversation_context_dict` → behaves like a combination of:
  - _build_conversation_history_block (stage, trend, topics that worked/failed, recent exchanges, RECENT TACTICS USED),
  - _build_long_term_memory_block (LONG TERM MEMORY & PROFILE CONTEXT),
  - _build_topic_exhaustion_block (TOPIC EXHAUSTION MAP).
- Use these dictionaries to:
  - Reference earlier topics naturally if relevant.
  - Avoid repeating topics that historically failed or appear in the topic exhaustion map.
  - Keep the user's persona, slang, and boundaries consistent with past behavior.

══════════════════════════════════════
DIRECTION-SPECIFIC RULES
══════════════════════════════════════
- If direction == "opener":
  - You are strictly forbidden from sending a greeting. Do NOT say "hi", "hey", "hello", or any greeting.
  - Your goal is to generate a "Reaction Comment" for her profile for a specific photo.
  - Use the `visual_hooks` from the analysis. Pick the most interesting one and make a "Playful Assumption" about it.
  - A good match-winning comment is a playful assumption based on a visual detail.
  - Example: Instead of "you look nice", use "i bet you spent more time picking that camera than actually taking photos with it"
- If direction == "change_topic":
  - Use the LONG TERM MEMORY & PROFILE CONTEXT style information from `conversation_context_dict` as your ONLY source for new topics.
  - Strictly avoid overused dating app cliches or hypotheticals.
  - STRICTLY BANNED: pineapple on pizza, zombie apocalypse, teleportation, winning the lottery, generic travel questions.
  - Study any topic exhaustion-style data and do NOT repeat any themes, hooks, or stories listed there. Pivot to a genuinely fresh, specific, slightly edgy angle that still feels naturally grounded in their actual profile or earlier chemistry.
- If direction == "ask_out":
  - The goal is to ASK THEM OUT. Be specific and bold with a concrete plan (place and time) while still matching the user's vibe and the recommended strategy.
- If direction == "get_number":
  - TERMINAL DIRECTION: GET NUMBER / MOVE OFF APP (CRITICAL)
  - At least one reply MUST include a clear transition to moving off the app.
  - Use casual Hinglish/Indian texting style for the close, with phrasing like:
    - "whatsapp pe switch karein"
    - "drop your number"
    - "number de de fir waha stalk karunga"
  - This is not optional: at least one reply MUST explicitly ask to move to WhatsApp/number/IG in natural, low-pressure language.
  - If conversation_temperature is "hot", closes should be more direct and confident (e.g., clearly asking for number / WhatsApp in one line).
  - If conversation_temperature is "warm", make the close a softer suggestion (e.g., "chalo ye chat wa pe continue karein" or "lets move this to wa"), framed as a natural next step rather than a demand.
  - Teasing is allowed ONLY if it still leads to an explicit "move off app" line in that reply. Do NOT generate pure banter that ignores the close.
- If direction == "revive_chat":
  - Treat this as a dead chat. Do not reference their last text directly. Focus on a high-energy fresh restart aligned with the strategy.

INVESTMENT THRESHOLD (WRITER EXECUTION — CRITICAL):
- If the Strategist has NOT explicitly called for a Close (i.e., recommended_strategy_label is not "SOFT CLOSE"),
  focus 100% on witty observations and teases.
- If you feel the urge to ask for a number/WhatsApp, ignore it and send a "PATTERN INTERRUPT" instead.

══════════════════════════════════════
AUDITOR FEEDBACK (CRITICAL)
══════════════════════════════════════
If `auditor_feedback` exists and is non-empty in the state, you MUST apply this feedback to fix the previous failed drafts.
- Do NOT repeat the behaviors or patterns that the auditor called out as cringe or weak.
- Treat auditor_feedback as a hard constraint, not a suggestion.

══════════════════════════════════════
OUTPUT FORMAT
══════════════════════════════════════
You must return `replies` as an array of EXACTLY 4 objects, not plain strings. For each reply you generate, you MUST fill:
- `text`: the actual reply text (following all language + style rules above).
- `strategy_label`: ONE of exactly: "PUSH-PULL", "FRAME CONTROL", "SOFT CLOSE", "VALUE ANCHOR", "PATTERN INTERRUPT".
- `is_recommended`: true/false.
  - STRICT RULE: Exactly ONE reply MUST have `is_recommended` = true. This is the Wingman's Choice — the highest status, most context-aware and culturally tuned option. The other 3 MUST have `is_recommended` = false.
- `coach_reasoning`: ONE short sentence explaining the psychology or cultural context behind this reply.

You MUST respond ONLY with a JSON object that matches the WriterOutput schema exactly.
"""


AUDITOR_SYSTEM_PROMPT = """
You are a brutal cringe filter and quality auditor for dating app replies.

Your job:
- Read the 4 candidate replies in `drafts.replies`.
- Check them against:
  - The user's Voice DNA expectations (especially no proper punctuation, no exclamation marks).
  - Anti-patterns such as: try-hard pickup lines, generic dating app cliches, over-explaining, therapy-speak, fake vulnerability, or anything that sounds like a corporate AI instead of a real Indian texter.
- Decide if the set of replies is CRINGE or SAFE.

CRINGE RULES (NON-NEGOTIABLE):
- If ANY reply uses exclamation marks (!), quotation marks (" ") inside the actual reply text, or apostrophes (') in the actual reply text, mark is_cringe = true.
- If ANY reply obviously violates the lazy texter style (overly formal grammar, full sentences with proper punctuation everywhere), mark is_cringe = true.
- If ANY reply sounds like a generic dating app opener, a therapy session, corporate jargon, or motivational quote, mark is_cringe = true.
- Check the detected_dialect from the analysis. If the dialect is ENGLISH, and the replies are in HINDI or HINGLISH, you MUST mark is_cringe = true and provide feedback: "Language mismatch: The girl only speaks English, do not use Hindi/Hinglish words."
- If there is a language mismatch (e.g., Hinglish used for an English-only profile), it is CRINGE. Reject it immediately.

OPENER-SPECIFIC CRITICAL RULE:
- If direction is "opener", each reply MUST clearly reference a specific visual detail from analysis.visual_hooks.
- If the opener is generic (e.g., "hey", "hi", "you look nice") or does not map to a concrete visual hook, mark is_cringe = true and explain which reply numbers are generic and which hook they should reference.
- If the opener does not reference a specific visual detail from the visual_hooks, it is CRINGE. Reject it and tell the writer to be more specific to her photos.

PUNCTUATION VERIFICATION (SYSTEM-VERIFIED):
- The system will provide a boolean `has_forbidden_punctuation` (and per-reply flags) in your input.
- If `has_forbidden_punctuation` is False, DO NOT complain about punctuation.
- Only focus your feedback on the social vibe, cringe level, and visual hooks.

CRITICAL RULE ON VISUAL HOOKS:
- The system will provide `transcript_count` in your input.
- If transcript_count is 0 (this is a fresh opener), you MUST enforce the use of visual_hooks.
- If transcript_count > 0 (the girl has already replied), DO NOT require visual hooks. At this stage, focusing on the flow of the conversation and her specific questions is more important than her photos. Do NOT reject a good reply just because it doesn't mention her clothes once the chat has started.

LANGUAGE REALISM:
- Do not reject Hinglish if the girl is currently speaking Hindi/Hinglish in the transcript.
- If she says "Yeh kya bola," she clearly wants to talk in a mix of Hindi/English.
- The goal is to be understood, not to follow a profile tag blindly.

MANDATORY STATUS CHECK (ANTI-THIRST):
- If any reply contains a request for a number, WhatsApp/WA, or a date (e.g., "let's meet", "move to wa", "drop your digits"),
  you MUST check `their_effort` from the analysis.
- If `their_effort` is LOW or MEDIUM, mark is_cringe = true and provide feedback:
  "Premature Close: The girl has not shown enough investment yet. Do not ask for a number. Switch to a high-status tease or a pattern interrupt instead."

DESPERATION FILTER:
- Flag any language that sounds overly eager or explanatory (e.g., "I wanted to ask because...", "I think we'd get along...").
- High-status men do not explain their interest; they just observe and tease.
- If the reply feels like it's chasing her, reject it.

SAFE RULES:
- If all 4 replies:
  - Respect the no-punctuation style (especially no exclamation marks), and
  - Feel natural, high-status, and aligned with an Indian/Hinglish texting vibe
  then you may set is_cringe = false.

FEEDBACK:
- If you set is_cringe = true, you MUST provide specific, concrete feedback in `feedback`:
  - Call out which reply numbers are problematic and why.
  - Mention any punctuation / style / vibe violations explicitly.
- If you set is_cringe = false, `feedback` should briefly confirm that the set looks clean and aligned with the rules.

You MUST respond ONLY with a JSON object matching the AuditorOutput schema exactly.
"""


def _encode_image_from_state(state: AgentState) -> str:
    """
    Ensure image_bytes is passed to Gemini as a base64 data URL.
    Supports either raw bytes or an existing data URL string.
    """
    img = state.get("image_bytes")
    if img is None:
        raise ValueError("Analyst node requires 'image_bytes' in state.")

    # 1. If it's already a perfectly formatted data URI, return it
    if isinstance(img, str) and img.startswith("data:image"):
        return img

    # 2. If it's a string, assume it's already a base64 string from the frontend
    if isinstance(img, str):
        return f"data:image/jpeg;base64,{img}"

    # 3. If it's actual raw bytes, encode it
    if isinstance(img, (bytes, bytearray)):
        b64 = base64.b64encode(img).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    raise ValueError("Invalid image format provided.")


def ocr_extractor_node(state: AgentState) -> AgentState:
    """
    Extracts the verbatim text and participants out of the vision state.
    """
    t0 = time.monotonic()
    logger.info("agent_ocr_start", **_state_meta(state))
    image_url = _encode_image_from_state(state)

    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0).with_structured_output(OcrExtractorOutput)

    content = [
        {"type": "text", "text": "Extract the raw text and identify participants from this image."},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]

    t_call = time.monotonic()
    result = llm.invoke([
        SystemMessage(content=OCR_EXTRACTOR_SYSTEM_PROMPT),
        HumanMessage(content=content)
    ])
    out = cast(OcrExtractorOutput, result)

    logger.info("agent_ocr_done", llm_ms=int((time.monotonic() - t_call) * 1000))
    # Store plain dicts so downstream json.dumps + logging never fails.
    return {**state, "raw_ocr_text": _normalize_raw_ocr_text(out.raw_ocr_text)}


def analyst_node(state: AgentState) -> AgentState:
    """
    LangGraph node that runs the visual analysis on the screenshot and
    populates the `analysis` portion of the AgentState.
    """
    t0 = time.monotonic()
    logger.info("agent_analyst_start", **_state_meta(state))
    image_url = _encode_image_from_state(state)
    raw_ocr_text = state.get("raw_ocr_text", [])
    raw_ocr_text_str = json.dumps(
        _normalize_raw_ocr_text(raw_ocr_text), ensure_ascii=False
    )
    core_lore = state.get("core_lore", "")
    past_memories = state.get("past_memories", "")

    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0).with_structured_output(
        AnalystOutput
    )

    content = [
        {
            "type": "text",
                "text": (
                    "Raw OCR Text (JSON list of bubbles):\n"
                    f"{raw_ocr_text_str}\n\n"
                    f"Core Lore:\n{core_lore}\n\n"
                    f"Past Memories:\n{past_memories}\n\n"
                    "Analyze the conversation vibe based on this context and extract visual_hooks from the image."
                ),
        },
        {
            "type": "image_url",
            "image_url": {"url": image_url},
        },
    ]

    t_call = time.monotonic()
    result = llm.invoke(
        [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]
    )

    analysis = cast(AnalystOutput, result)

    logger.info("analyst_visual_hooks", hooks=getattr(analysis, "visual_hooks", []))

    logger.info(
        "agent_analyst_done",
        duration_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=int((time.monotonic() - t_call) * 1000),
        detected_dialect=analysis.detected_dialect,
        their_tone=analysis.their_tone,
        their_effort=analysis.their_effort,
        conversation_temperature=analysis.conversation_temperature,
        detected_archetype=analysis.detected_archetype,
        key_detail=analysis.key_detail,
        person_name=getattr(analysis, "person_name", "unknown"),
        stage=getattr(analysis, "stage", "early_talking"),
        their_last_message=_truncate(getattr(analysis, "their_last_message", "")),
        transcript_count=len(analysis.visual_transcript),
        transcript_preview=_truncate(
            [
                {
                    "sender": b.sender,
                    "quoted_context": b.quoted_context,
                    "actual_new_message": b.actual_new_message,
                }
                for b in analysis.visual_transcript
            ],
            max_len=120,
        ),
    )

    return {
        **state,
        "analysis": analysis,
        "transcript_count": len(analysis.visual_transcript),
        "revision_count": 0,
        "is_cringe": False,
    }

def bouncer_node(state: AgentState) -> AgentState:
    """
    Validates that the provided image is a chat/dating conversation screenshot.
    """
    t0 = time.monotonic()
    logger.info("agent_bouncer_start", **_state_meta(state))
    image_url = _encode_image_from_state(state)

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview", temperature=0
    ).with_structured_output(BouncerOutput)

    content = [
        {
            "type": "text",
            "text": (
                "Is this image a screenshot of a text message or dating app conversation? "
                "Return true if yes, false if it is a random picture, menu, dog, blank screen, etc. "
                "Provide a short reason."
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": image_url},
        },
    ]

    t_call = time.monotonic()
    result = llm.invoke(
        [
            SystemMessage(content="You are a strict validator for chat screenshots."),
            HumanMessage(content=content),
        ]
    )

    out = cast(BouncerOutput, result)

    logger.info(
        "agent_bouncer_done",
        duration_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=int((time.monotonic() - t_call) * 1000),
        is_valid_chat=out.is_valid_chat,
        reason=_truncate(out.reason, max_len=240),
        image_input_type=type(state.get("image_bytes")).__name__,
        image_input_len=(
            len(state.get("image_bytes")) if isinstance(state.get("image_bytes"), str) else None
        ),
    )

    return {
        **state,
        "is_valid_chat": out.is_valid_chat,
        "bouncer_reason": out.reason,
    }


def librarian_node(state: AgentState) -> AgentState:
    """
    Librarian node: fetch core lore + semantic memories for the match.
    Runs after `ocr_extractor_node` to use `raw_ocr_text` for indexing.
    """
    core_lore = state.get("core_lore", "") or ""
    past_memories = state.get("past_memories", "") or ""
    raw_ocr_text = state.get("raw_ocr_text", [])
    current_text = json.dumps(_normalize_raw_ocr_text(raw_ocr_text), ensure_ascii=False)

    conversation_id = state.get("conversation_id")
    user_id = state.get("user_id")
    if not (conversation_id and user_id and raw_ocr_text):
        return {**state, "core_lore": core_lore, "past_memories": past_memories}

    try:
        async def _fetch() -> dict[str, str]:
            # IMPORTANT:
            # `librarian_node` runs inside a background thread (via `asyncio.to_thread`)
            # and uses `asyncio.run()` internally (a separate event loop).
            #
            # To avoid SQLAlchemy async connection pool reuse across event loops
            # (which causes: "Future attached to a different loop"), we create a
            # short-lived engine/session here and dispose it immediately.
            engine = create_async_engine(
                settings.database_url,
                echo=False,
            )
            SessionMaker = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            try:
                async with SessionMaker() as local_db:
                    return await get_match_context(
                        local_db,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        current_text=current_text,
                    )
            finally:
                await engine.dispose()

        librarian = asyncio.run(_fetch())
        core_lore = librarian.get("core_lore") or ""
        past_memories = librarian.get("past_memories") or ""
    except Exception:
        # Retrieval must never break generation.
        core_lore = ""
        past_memories = ""

    return {**state, "core_lore": core_lore, "past_memories": past_memories}


def strategist_node(state: AgentState) -> AgentState:
    """
    LangGraph node that takes the prior analysis + direction + conversation context
    and decides the psychological strategy only (no actual reply text).
    """
    t0 = time.monotonic()
    logger.info("agent_strategist_start", **_state_meta(state))
    analysis = state.get("analysis")
    if analysis is None:
        raise ValueError("Strategist node requires 'analysis' in state.")

    direction = state.get("direction", "")
    context = state.get("conversation_context_dict", {})

    core_lore = state.get("core_lore", "") or ""
    past_memories = state.get("past_memories", "") or ""

    person_name = getattr(analysis, "person_name", None) or "unknown"
    convo_ctx_person = (state.get("conversation_context_dict", {}) or {}).get(
        "person_name", None
    )
    if convo_ctx_person and str(convo_ctx_person).lower() != "unknown":
        person_name = str(convo_ctx_person)

    transcript_text = ""
    for bubble in reversed(getattr(analysis, "visual_transcript", []) or []):
        if getattr(bubble, "sender", "") == "them":
            actual = getattr(bubble, "actual_new_message", "") or ""
            # Strategy decisions should be anchored to her latest ACTUAL new message only.
            # Quoted_context (faded reply blocks) is past context and can belong to the opposite person.
            transcript_text = actual
            break
    if not transcript_text:
        # Fallback: use the latest bubble content we can find.
        for bubble in reversed(getattr(analysis, "visual_transcript", []) or []):
            actual = getattr(bubble, "actual_new_message", "") or ""
            if actual:
                transcript_text = actual
                break

    librarian_context = {
        "person_name": person_name,
        "core_lore": core_lore,
        "past_memories": past_memories,
    }

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview", temperature=0.4
    ).with_structured_output(StrategyOutput)

    t_call = time.monotonic()
    result = llm.invoke(
        [
            SystemMessage(content=STRATEGIST_SYSTEM_PROMPT),
            HumanMessage(
                content=json.dumps(
                    {
                        "analysis": analysis.model_dump(),
                        "direction": direction,
                        "conversation_context": context,
                        "librarian": librarian_context,
                        "transcript_text": transcript_text,
                    }
                )
            ),
        ]
    )

    strategy = cast(StrategyOutput, result)

    logger.info(
        "agent_strategist_done",
        duration_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=int((time.monotonic() - t_call) * 1000),
        wrong_moves=strategy.wrong_moves,
        right_energy=strategy.right_energy,
        hook_point=strategy.hook_point,
        recommended_strategy_label=strategy.recommended_strategy_label,
    )

    return {
        **state,
        "strategy": strategy,
    }


def _compute_writer_temperature(state: AgentState) -> float:
    """
    Mirror the PromptEngine temperature logic as closely as possible using
    the available state fields. Fallback to 0.7 when information is missing.
    """
    try:
        analysis = state.get("analysis")
        ctx = state.get("conversation_context_dict") or {}

        direction = state.get("direction", "default")
        conversation_temperature = (
            getattr(analysis, "conversation_temperature", None) or "warm"
        )
        stage = ctx.get("stage", "early_talking")
        interaction_count = ctx.get("interaction_count", 0)

        temp = calculate_temperature(
            direction=direction,
            conversation_temperature=conversation_temperature,
            stage=stage,
            interaction_count=interaction_count,
        )
        return float(temp)
    except Exception:
        return 0.7


def writer_node(state: AgentState) -> AgentState:
    """
    LangGraph node that generates the actual reply text options using the
    analysis, strategy, direction, and rich context dictionaries.
    """
    t0 = time.monotonic()
    logger.info("agent_writer_start", **_state_meta(state))
    analysis = state.get("analysis")
    strategy = state.get("strategy")
    if analysis is None or strategy is None:
        raise ValueError("Writer node requires both 'analysis' and 'strategy' in state.")

    direction = state.get("direction", "")
    voice_dna = state.get("voice_dna_dict", {})
    conversation_context = state.get("conversation_context_dict", {})
    auditor_feedback = state.get("auditor_feedback", "")

    temperature = _compute_writer_temperature(state)
    logger.info(
        "agent_writer_temperature",
        **_state_meta(state),
        temperature=temperature,
    )
    writer_llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview", temperature=temperature
    ).with_structured_output(WriterOutput)

    t_call = time.monotonic()
    result = writer_llm.invoke(
        [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(
                content=json.dumps(
                    {
                        "analysis": analysis.model_dump(),
                        "strategy": strategy.model_dump(),
                        "direction": direction,
                        "voice_dna_dict": voice_dna,
                        "conversation_context_dict": conversation_context,
                        "auditor_feedback": auditor_feedback,
                    }
                )
            ),
        ]
    )

    drafts = cast(WriterOutput, result)

    logger.info(
        "agent_writer_done",
        duration_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=int((time.monotonic() - t_call) * 1000),
        reply_count=len(drafts.replies),
        strategy_labels=[r.strategy_label for r in drafts.replies],
        recommended_index=next(
            (i for i, r in enumerate(drafts.replies) if r.is_recommended), -1
        ),
        replies_preview=_truncate(
            [
                {
                    "text": r.text,
                    "strategy_label": r.strategy_label,
                    "is_recommended": r.is_recommended,
                    "coach_reasoning": r.coach_reasoning,
                }
                for r in drafts.replies
            ],
            max_len=140,
        ),
    )

    return {
        **state,
        "drafts": drafts,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def auditor_node(state: AgentState) -> AgentState:
    """
    LangGraph node that reviews the drafts as a brutal cringe filter and
    either approves them or returns concrete feedback for revision.
    """
    t0 = time.monotonic()
    logger.info("agent_auditor_start", **_state_meta(state))
    drafts = state.get("drafts")
    if drafts is None:
        raise ValueError("Auditor node requires 'drafts' in state.")

    transcript_count = int(
        state.get(
            "transcript_count",
            len(state.get("analysis").visual_transcript) if state.get("analysis") else 0,
        )
    )

    reply_texts = [r.text for r in drafts.replies]
    per_reply_has_forbidden_punctuation = [
        has_forbidden_punctuation(t) for t in reply_texts
    ]
    has_forbidden_punctuation_any = any(per_reply_has_forbidden_punctuation)

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview", temperature=0
    ).with_structured_output(AuditorOutput)

    t_call = time.monotonic()
    result = llm.invoke(
        [
            SystemMessage(content=AUDITOR_SYSTEM_PROMPT),
            HumanMessage(
                content=json.dumps(
                    {
                        "drafts": drafts.model_dump(),
                        "has_forbidden_punctuation": has_forbidden_punctuation_any,
                        "per_reply_has_forbidden_punctuation": per_reply_has_forbidden_punctuation,
                        "transcript_count": transcript_count,
                    }
                )
            ),
        ]
    )

    audit = cast(AuditorOutput, result)

    if audit.is_cringe:
        logger.warning(
            "auditor_rejection",
            revision=state.get("revision_count", 0),
            feedback=audit.feedback,
        )

    logger.info(
        "agent_auditor_done",
        duration_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=int((time.monotonic() - t_call) * 1000),
        is_cringe=audit.is_cringe,
        feedback=_truncate(audit.feedback, max_len=400),
        revision_count=state.get("revision_count", 0),
    )

    return {
        **state,
        "is_cringe": audit.is_cringe,
        "auditor_feedback": audit.feedback,
    }

