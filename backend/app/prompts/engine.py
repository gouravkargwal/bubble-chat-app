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

        return f"""
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

        parts.append("")
        parts.append(
            "Use this history for continuity. Reference earlier topics naturally if relevant."
        )
        parts.append("Do NOT repeat topics that failed. Lean into topics that worked.")

        return "\n".join(parts)

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

        return "\n".join(parts)


# Global singleton
prompt_engine = PromptEngine()
