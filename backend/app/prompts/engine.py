"""Prompt engine — assembles the full system prompt from all context layers."""

from app.domain.models import ConversationContext, PromptPayload, VoiceDNA
from app.prompts.temperature import calculate_temperature
from app.prompts.variants import registry
from app.prompts.templates.base_system import BASE_SYSTEM_PROMPT
from app.prompts.templates.few_shots import FEW_SHOTS
from app.prompts.templates.anti_patterns import ANTI_PATTERNS
from app.prompts.templates.fork_principle import FORK_PRINCIPLE
from app.prompts.templates.directions import get_direction_prompt
from app.prompts.templates.playbooks import select_playbook
from app.prompts.templates.self_critique import SELF_CRITIQUE


class PromptEngine:
    """Builds the complete prompt by layering context in the right order.

    Assembly order matters — LLMs weight beginning and end most heavily:
    1. Identity + 3-phase instructions (set the standard)
    2. Few-shot examples (show what good looks like)
    3. Anti-patterns (show what to avoid)
    4. Fork principle + diversity rules
    5. Direction-specific instructions
    6. Situational playbook (auto-selected)
    7. Voice DNA (user's texting style)
    8. Conversation history
    9. Self-critique checklist (freshest in attention)
    """

    def build(
        self,
        direction: str,
        custom_hint: str | None = None,
        voice_dna: VoiceDNA | None = None,
        conversation_context: ConversationContext | None = None,
        variant_id: str = "default",
    ) -> PromptPayload:
        variant = registry.get(variant_id)
        parts: list[str] = []

        # 1. Base system prompt (identity + 3-phase instructions)
        parts.append(BASE_SYSTEM_PROMPT)

        # 2. Few-shot examples
        if variant.use_few_shots:
            content = variant.custom_few_shots or FEW_SHOTS
            parts.append(content)

        # 3. Anti-patterns kill list
        if variant.use_anti_patterns:
            content = variant.custom_anti_patterns or ANTI_PATTERNS
            parts.append(content)

        # 4. Fork principle + structural diversity
        if variant.use_fork_principle:
            parts.append(FORK_PRINCIPLE)

        # 5. Direction-specific instructions
        parts.append(get_direction_prompt(direction))

        # Special opener rule to enforce topic diversity and avoid tunnel vision
        if direction.lower() == "opener":
            parts.append(
                """
CRITICAL RULE FOR OPENERS: Since this is an opener, you MUST provide 4 completely distinct angles. DO NOT focus on the same topic twice. Tie each reply directly to the `analysis.notable_observations` array.
- Reply 1: Based strictly on observation #1.
- Reply 2: Based strictly on observation #2 (must be a visual photo detail).
- Reply 3: Based strictly on observation #3.
- Reply 4: Based strictly on observation #4.
Ensure high topic diversity and do not mix observations within a single reply."""
            )

        # Anti-cliché guardrail specifically for CHANGE_TOPIC requests.
        if direction.lower() == "change_topic":
            parts.append(
                """
CRITICAL: When changing the topic, you MUST ground the new topic in the [LONG TERM MEMORY & PROFILE CONTEXT]. DO NOT use generic, overused dating app cliches. STRICTLY BANNED TOPICS: Pineapple on pizza, zombie apocalypse, teleportation, winning the lottery, or generic travel questions. Generate highly specific, observational, and slightly edgy topics based ONLY on the user's actual profile data or earlier conversation themes."""
            )

        # Terminal direction guardrails for GET_NUMBER.
        if direction.lower() == "get_number":
            parts.append(
                """
TERMINAL DIRECTION: GET NUMBER / MOVE OFF APP (CRITICAL)
- The response MUST include a clear transition to moving off the app.
- Use casual Hinglish/Indian texting style for the close, with phrasing like:
  - "whatsapp pe switch karein"
  - "drop your number"
  - "number de de fir waha stalk karunga"
- This is not optional: at least one reply MUST explicitly ask to move to WhatsApp/number/IG in natural, low-pressure language.
- If CONVERSATION_TEMPERATURE is "hot", your closes should be more direct and confident (e.g., clearly asking for number / WhatsApp in one line).
- If CONVERSATION_TEMPERATURE is "warm", make the close a softer suggestion (e.g., "chalo ye chat wa pe continue karein" or "lets move this to wa"), framed as a natural next step rather than a demand.
- Teasing is allowed ONLY if it still leads to an explicit "move off app" line in that reply. Do NOT generate pure banter that ignores the close."""
            )

        # 6. Situational playbook (auto-selected based on conversation state)
        if variant.use_playbooks and conversation_context:
            playbook = select_playbook(
                stage=conversation_context.stage,
                temperature="warm",  # will be overridden by actual analysis
                tone="neutral",
                effort="medium",
            )
            if playbook:
                parts.append(playbook)

        # 7. Voice DNA (user's texting style)
        if variant.use_voice_dna and voice_dna and voice_dna.sample_count >= 3:
            parts.append(self._build_voice_dna_block(voice_dna))

        # 8. Conversation history
        if (
            variant.use_conversation_history
            and conversation_context
            and conversation_context.interaction_count > 0
        ):
            parts.append(self._build_conversation_history_block(conversation_context))

        # 8b. Long-term memory + profile context section to keep the model anchored
        # to the original profile scan and topics that have historically worked.
        if conversation_context:
            parts.append(
                self._build_long_term_memory_block(conversation_context)
            )

        # 8c. Topic exhaustion prevention: show the model exactly what has already
        # been discussed so it can avoid repeating the same themes.
        if conversation_context:
            topic_exhaustion_block = self._build_topic_exhaustion_block(
                conversation_context
            )
            if topic_exhaustion_block:
                parts.append(topic_exhaustion_block)

        # 9. Self-critique checklist
        if variant.use_self_critique:
            parts.append(SELF_CRITIQUE)

        system_prompt = "\n".join(parts)

        # Build user prompt
        user_prompt = self._build_user_prompt(
            direction, custom_hint, conversation_context
        )

        # Calculate temperature
        temp = calculate_temperature(
            direction=direction,
            conversation_temperature="warm",  # default — actual analysis happens in LLM
            stage=(
                conversation_context.stage if conversation_context else "early_talking"
            ),
            interaction_count=(
                conversation_context.interaction_count if conversation_context else 0
            ),
        )

        return PromptPayload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temp,
        )

    def _build_voice_dna_block(self, voice: VoiceDNA) -> str:
        length_desc = {
            "short": f"short (avg {voice.avg_reply_length:.0f} chars) — keep replies brief",
            "medium": f"medium length (avg {voice.avg_reply_length:.0f} chars)",
            "long": f"longer messages (avg {voice.avg_reply_length:.0f} chars) — can be more expressive",
        }.get(voice.preferred_length, "medium length")

        emoji_desc = {
            0.0: "never uses emojis — do NOT include any",
        }
        if voice.emoji_frequency == 0:
            emoji_text = "never — do NOT include any emojis"
        elif voice.emoji_frequency < 0.3:
            emoji_text = "rarely — 0-1 emoji max"
        elif voice.emoji_frequency < 0.7:
            emoji_text = "sometimes — 1 emoji is fine"
        else:
            emoji_text = "often — emojis are part of their style"

        words_text = (
            ", ".join(voice.common_words[:5])
            if voice.common_words
            else "none detected yet"
        )

        base_dna = f"""
══════════════════════════════════════
USER'S TEXTING STYLE (Voice DNA — match this closely)
══════════════════════════════════════
Length: {length_desc}
Emojis: {emoji_text}
Capitalization: {voice.capitalization}
Punctuation: {voice.punctuation_style}
Words they commonly use: {words_text}

IMPORTANT: Make every reply sound like THIS specific person wrote it.
If they never use emojis, you never use emojis.
If they say "lol" not "haha", you say "lol" not "haha".
If they text lowercase, every reply must be lowercase.
Their voice > your defaults."""

        # Add vibe preference instructions
        vibe_parts = []
        if voice.disliked_vibes:
            vibe_parts.append(
                f"\n\n🚫 CRITICAL: User HATES these vibes: {', '.join(voice.disliked_vibes)}. "
                f"Do NOT generate ANY replies with these tones. Avoid them completely."
            )

        if voice.top_vibes:
            vibe_parts.append(
                f"\n\n⭐ VIBE ALLOCATION: Focus all 4 replies on their preferred styles: {', '.join(voice.top_vibes)}. "
                f"Redistribute the standard vibe mix to match their personality. "
                f"For example, if they only like Witty and Smooth, give 2 Witty + 2 Smooth options."
            )

        if vibe_parts:
            base_dna += "".join(vibe_parts)

        if voice.recent_organic_messages:
            base_dna += "\n\n⭐ EXACT EXAMPLES OF HOW THEY TEXT (Mimic this cadence, slang, and capitalization perfectly):\n"
            for i, msg in enumerate(voice.recent_organic_messages, 1):
                base_dna += f'{i}. "{msg}"\n'

        return base_dna

    def _build_conversation_history_block(self, ctx: ConversationContext) -> str:
        parts = [
            "",
            "══════════════════════════════════════",
            f"CONVERSATION HISTORY (with {ctx.person_name})",
            "══════════════════════════════════════",
            f"Stage: {ctx.stage} ({ctx.interaction_count} previous interactions)",
            f"Trend: conversation is {ctx.tone_trend}",
        ]

        if ctx.topics_worked:
            parts.append(
                f"Topics that got good responses: {', '.join(ctx.topics_worked)}"
            )
        if ctx.topics_failed:
            parts.append(f"Topics that fell flat: {', '.join(ctx.topics_failed)}")

        if ctx.recent_summaries:
            parts.append("")
            parts.append("Recent exchanges:")
            for summary in ctx.recent_summaries[-3:]:
                parts.append(f"- {summary}")

        if ctx.recent_user_replies:
            parts.append("")
            parts.append("RECENT TACTICS USED (last 3 things the user actually sent):")
            for reply in ctx.recent_user_replies[-3:]:
                preview = reply if len(reply) <= 80 else reply[:77] + "..."
                parts.append(f"- {preview}")

        parts.append("")
        parts.append(
            "Use this history for continuity. Reference earlier topics naturally if relevant."
        )
        parts.append("Do NOT repeat topics that failed. Lean into topics that worked.")

        return "\n".join(parts)

    def _build_long_term_memory_block(self, ctx: ConversationContext) -> str:
        lines: list[str] = [
            "",
            "══════════════════════════════════════",
            "[LONG TERM MEMORY & PROFILE CONTEXT]",
            "══════════════════════════════════════",
        ]

        if ctx.first_key_detail:
            lines.append(f"Original key detail from first interaction: {ctx.first_key_detail}")
        if ctx.first_their_last_message:
            lines.append(
                f"Their very first meaningful message (paraphrased): {ctx.first_their_last_message}"
            )

        if ctx.topics_worked:
            lines.append(
                "Topics that historically got good responses (do NOT forget these): "
                + ", ".join(ctx.topics_worked)
            )
        if ctx.topics_failed:
            lines.append(
                "Topics that historically fell flat (avoid repeating these): "
                + ", ".join(ctx.topics_failed)
            )

        if len(lines) == 4:
            # No additional context beyond the header; still return the header so
            # the anti-cliché guardrail can reference it safely.
            lines.append("No long-term memory available yet for this conversation.")

        lines.append(
            "Treat this section as ground truth about the user's actual profile and prior chemistry. Do NOT hallucinate new traits."
        )
        return "\n".join(lines)

    def _build_topic_exhaustion_block(
        self, ctx: ConversationContext
    ) -> str:
        recent_org = ctx.last_user_organic_texts or []
        recent_replies = ctx.last_ai_replies_shown or []

        if not recent_org and not recent_replies:
            return ""

        lines: list[str] = [
            "",
            "══════════════════════════════════════",
            "TOPIC EXHAUSTION MAP (most recent first)",
            "══════════════════════════════════════",
        ]

        if recent_org:
            lines.append("Recent organic messages the user actually typed:")
            for i, msg in enumerate(recent_org[:3], 1):
                preview = msg if len(msg) <= 100 else msg[:97] + "..."
                lines.append(f"{i}. {preview}")

        if recent_replies:
            lines.append("")
            lines.append("Recent AI reply options already shown to the user:")
            for i, msg in enumerate(recent_replies[:3], 1):
                preview = msg if len(msg) <= 100 else msg[:97] + "..."
                lines.append(f"{i}. {preview}")

        lines.append(
            "CRITICAL: Do NOT repeat the same themes, hooks, or stories from this list. You must introduce genuinely new angles."
        )

        return "\n".join(lines)

    def _build_user_prompt(
        self,
        direction: str,
        custom_hint: str | None,
        conversation_context: ConversationContext | None,
    ) -> str:
        parts = ["Analyze this dating app screenshot and generate 4 reply suggestions."]

        if custom_hint:
            parts.append(f"\nUser's specific request: {custom_hint}")

        if conversation_context and conversation_context.person_name != "unknown":
            parts.append(
                f"\nYou're helping reply to: {conversation_context.person_name}"
            )

        # Direction-specific final instructions to leverage recency bias
        if direction == "change_topic":
            parts.append(
                "\n⚠️ IMPORTANT: The user wants to CHANGE THE TOPIC.\n"
                "- Use the [LONG TERM MEMORY & PROFILE CONTEXT] section as your ONLY source for new topics.\n"
                "- Strictly avoid overused dating app cliches or hypotheticals.\n"
                "- STRICTLY BANNED: pineapple on pizza, zombie apocalypse, teleportation, winning the lottery, generic travel questions.\n"
                "- Study the TOPIC EXHAUSTION MAP and do NOT repeat any themes, hooks, or stories listed there.\n"
                "Pivot to a genuinely fresh, specific, slightly edgy angle that still feels naturally grounded in their actual profile or earlier chemistry."
            )
        elif direction == "ask_out":
            parts.append(
                "\n⚠️ IMPORTANT: The goal is to ASK THEM OUT. Be specific and bold with a concrete plan (place and time)."
            )
        elif direction == "get_number":
            parts.append(
                "\n⚠️ IMPORTANT: The goal is to MOVE OFF THE APP.\n"
                "- Every reply must naturally steer the conversation toward exchanging WhatsApp / number / IG.\n"
                "- Use casual Hinglish phrasing like 'whatsapp pe switch karein?' or 'drop your number', not stiff English.\n"
                "- If the conversation feels hot, be direct and confident. If it feels just warm, make it a soft suggestion instead of a command."
            )
        elif direction == "revive_chat":
            parts.append(
                "\n⚠️ IMPORTANT: This is a dead chat. Do not reference their last text directly. Focus on a high-energy fresh restart."
            )

        return "\n".join(parts)


# Global singleton
prompt_engine = PromptEngine()
