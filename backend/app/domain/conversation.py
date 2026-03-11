"""Conversation memory manager — auto-detects and tracks per-person conversations."""

import json
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AnalysisResult, ConversationContext
from app.infrastructure.database.models import Conversation, Interaction


async def find_or_create_conversation(
    user_id: str,
    person_name: str,
    db: AsyncSession,
) -> Conversation:
    """Find an existing conversation by person name or create a new one."""
    if not person_name or person_name == "unknown":
        # Create a transient conversation
        convo = Conversation(user_id=user_id, person_name="unknown")
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        return convo

    # Fuzzy match: case-insensitive search for active conversations
    name_lower = person_name.lower().strip()
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.is_active == True,  # noqa: E712
            func.lower(Conversation.person_name) == name_lower,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Create new conversation
    convo = Conversation(user_id=user_id, person_name=person_name)
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return convo


async def update_conversation_from_analysis(
    conversation: Conversation,
    analysis: AnalysisResult,
    copied_index: int | None,
    db: AsyncSession,
) -> None:
    """Update conversation context after an interaction."""
    # Update stage (clamp to DB column limit String(30))
    if analysis.stage and analysis.stage != "unknown":
        conversation.stage = analysis.stage[:30]

    # Update person name if better detected
    if analysis.person_name and analysis.person_name != "unknown":
        conversation.person_name = analysis.person_name

    # Increment count
    conversation.interaction_count += 1
    # Store naive UTC timestamp to match TIMESTAMP WITHOUT TIME ZONE column
    conversation.last_interaction_at = datetime.utcnow()

    # Track topics
    if analysis.key_detail:
        topics_worked = json.loads(conversation.topics_worked or "[]")
        topics_failed = json.loads(conversation.topics_failed or "[]")

        if copied_index is not None:
            # User copied a reply — this topic worked
            if analysis.key_detail not in topics_worked:
                topics_worked.append(analysis.key_detail)
                topics_worked = topics_worked[-10:]  # Keep last 10
        else:
            # User didn't copy anything — topic might have failed
            if analysis.key_detail not in topics_failed:
                topics_failed.append(analysis.key_detail)
                topics_failed = topics_failed[-10:]

        conversation.topics_worked = json.dumps(topics_worked)
        conversation.topics_failed = json.dumps(topics_failed)

    # Calculate tone trend from last 3 interactions
    result = await db.execute(
        select(Interaction.conversation_temperature)
        .where(Interaction.conversation_id == conversation.id)
        .order_by(Interaction.created_at.desc())
        .limit(3)
    )
    recent_temps = [r[0] for r in result.all() if r[0]]

    if len(recent_temps) >= 2:
        temp_values = {"hot": 4, "warm": 3, "lukewarm": 2, "cold": 1}
        scores = [temp_values.get(t, 2) for t in recent_temps]
        if scores[0] > scores[-1]:
            conversation.tone_trend = "warming"
        elif scores[0] < scores[-1]:
            conversation.tone_trend = "cooling"
        else:
            conversation.tone_trend = "stable"

    await db.commit()


async def build_conversation_context(
    conversation: Conversation,
    db: AsyncSession,
) -> ConversationContext:
    """Build a ConversationContext domain object for prompt injection."""
    topics_worked = json.loads(conversation.topics_worked or "[]")
    topics_failed = json.loads(conversation.topics_failed or "[]")

    # Get last 3 interaction summaries
    result = await db.execute(
        select(Interaction)
        .where(Interaction.conversation_id == conversation.id)
        .order_by(Interaction.created_at.desc())
        .limit(3)
    )
    recent_interactions = result.scalars().all()

    summaries = []
    for interaction in reversed(recent_interactions):
        summary = f"[{interaction.direction}] "
        if interaction.copied_index is not None:
            copied_reply = getattr(
                interaction, f"reply_{interaction.copied_index}", None
            )
            if copied_reply:
                summary += (
                    f'Sent: "{copied_reply[:60]}..."'
                    if len(copied_reply) > 60
                    else f'Sent: "{copied_reply}"'
                )
            else:
                summary += "Copied a reply"
        else:
            summary += "Didn't use any suggestion"
        summaries.append(summary)

    return ConversationContext(
        person_name=conversation.person_name,
        stage=conversation.stage,
        tone_trend=conversation.tone_trend,
        topics_worked=topics_worked,
        topics_failed=topics_failed,
        interaction_count=conversation.interaction_count,
        recent_summaries=summaries,
    )
