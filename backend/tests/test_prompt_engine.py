"""Test the prompt engine builds correct prompts."""

import pytest

from app.domain.models import ConversationContext, VoiceDNA
from app.prompts.engine import prompt_engine


def test_default_prompt_contains_all_sections():
    """Default variant should include all template sections."""
    payload = prompt_engine.build(direction="quick_reply")
    prompt = payload.system_prompt

    assert "PHASE 1: ANALYZE" in prompt
    assert "PHASE 2: STRATEGIZE" in prompt
    assert "PHASE 3: GENERATE" in prompt
    assert "GOOD vs BAD REPLIES" in prompt  # few shots
    assert "NEVER USE THESE" in prompt  # anti patterns
    assert "FORK PRINCIPLE" in prompt
    assert "DIRECTION: QUICK REPLY" in prompt
    assert "SELF-CHECK" in prompt
    assert "OUTPUT FORMAT" in prompt


def test_minimal_variant_excludes_extras():
    """Minimal variant should only have base system + direction + output format."""
    payload = prompt_engine.build(direction="quick_reply", variant_id="minimal")
    prompt = payload.system_prompt

    assert "PHASE 1: ANALYZE" in prompt
    assert "GOOD vs BAD REPLIES" not in prompt
    assert "NEVER USE THESE" not in prompt
    assert "FORK PRINCIPLE" not in prompt
    assert "SELF-CHECK" not in prompt


def test_direction_specific_content():
    """Each direction should produce different instruction content."""
    quick = prompt_engine.build(direction="quick_reply").system_prompt
    number = prompt_engine.build(direction="get_number").system_prompt
    playful = prompt_engine.build(direction="keep_playful").system_prompt

    assert "DIRECTION: QUICK REPLY" in quick
    assert "DIRECTION: GET THEIR NUMBER" in number
    assert "DIRECTION: KEEP IT PLAYFUL" in playful


def test_voice_dna_injection():
    """Voice DNA should be injected when sample count >= 3."""
    voice = VoiceDNA(
        avg_reply_length=45.0,
        emoji_frequency=0.1,
        common_words=["ngl", "lowkey", "lol"],
        punctuation_style="no periods",
        capitalization="lowercase",
        preferred_length="short",
        sample_count=10,
    )
    payload = prompt_engine.build(
        direction="quick_reply", voice_dna=voice, variant_id="voice_dna_on"
    )
    assert "Voice DNA" in payload.system_prompt
    assert "ngl" in payload.system_prompt
    assert "lowercase" in payload.system_prompt


def test_voice_dna_not_injected_low_samples():
    """Voice DNA should NOT be injected when sample count < 3."""
    voice = VoiceDNA(sample_count=1)
    payload = prompt_engine.build(direction="quick_reply", voice_dna=voice)
    assert "Voice DNA" not in payload.system_prompt


def test_conversation_history_injection():
    """Conversation context should appear in prompt when available."""
    ctx = ConversationContext(
        person_name="Sarah",
        stage="building_chemistry",
        tone_trend="warming",
        topics_worked=["dogs", "hiking"],
        topics_failed=["work"],
        interaction_count=5,
        recent_summaries=["[quick_reply] Sent: 'your dog is so cute'"],
    )
    payload = prompt_engine.build(direction="quick_reply", conversation_context=ctx)
    assert "Sarah" in payload.system_prompt
    assert "dogs" in payload.system_prompt
    assert "warming" in payload.system_prompt


def test_temperature_varies_by_direction():
    """Different directions should produce different temperatures."""
    playful = prompt_engine.build(direction="keep_playful")
    deep = prompt_engine.build(direction="go_deeper")
    assert playful.temperature > deep.temperature


def test_custom_hint_in_user_prompt():
    """Custom hint should appear in user prompt."""
    payload = prompt_engine.build(direction="quick_reply", custom_hint="make it funny about cats")
    assert "make it funny about cats" in payload.user_prompt
