"""Conversation memory manager — auto-detects and tracks per-person conversations."""

import json
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AnalysisResult, ConversationContext
from app.infrastructure.database.models import Conversation, Interaction


async def find_or_create_conversation(
    user_id: str,
    person_name: str,
    db: AsyncSession,
) -> Conversation:
    """Find an existing conversation by person name or create a new one.

    Multiple active conversations are supported (one per person).
    If a conversation for this person already exists (active or inactive),
    reactivate it. Otherwise create a new one.
    """
    if not person_name or person_name == "unknown":
        convo = Conversation(user_id=user_id, person_name="unknown", is_active=True)
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        return convo

    # Search all conversations for this person (active or inactive), most recent first
    name_lower = person_name.lower().strip()
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            func.lower(Conversation.person_name) == name_lower,
        ).order_by(Conversation.last_interaction_at.desc().nullslast())
    )
    existing = result.scalars().first()

    if existing:
        if not existing.is_active:
            existing.is_active = True
            await db.commit()
        return existing

    # No existing conversation for this person — create one
    convo = Conversation(user_id=user_id, person_name=person_name, is_active=True)
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return convo


async def update_conversation_from_analysis(
    conversation: Conversation,
    analysis: AnalysisResult,
    copied_index: int | None,
    db: AsyncSession,
    copied_strategy_label: str | None = None,
) -> None:
    """Update conversation context after an interaction.

    Called from the /track/copy handler, so `copied_index` reflects the reply
    the user actually sent. `copied_strategy_label` is that reply's strategy, used
    to learn the user's selection preference (Phase 5 copy-rate signal).
    """
    # Update stage (clamp to DB column limit String(30))
    if analysis.stage and analysis.stage != "unknown":
        conversation.stage = analysis.stage[:30]

    # Phase 5: record the copied reply's strategy as a selection win.
    if copied_strategy_label:
        try:
            stats = json.loads(conversation.strategy_stats or "{}")
            if not isinstance(stats, dict):
                stats = {}
            entry = stats.get(copied_strategy_label) or {}
            entry = {
                "shown": int(entry.get("shown", 0)),
                "copied": int(entry.get("copied", 0)) + 1,
                "landed": int(entry.get("landed", 0)),
                "flopped": int(entry.get("flopped", 0)),
            }
            stats[copied_strategy_label] = entry
            conversation.strategy_stats = json.dumps(stats)
        except Exception:
            pass

    # Update person name if better detected
    if analysis.person_name and analysis.person_name != "unknown":
        conversation.person_name = analysis.person_name

    # Increment count
    conversation.interaction_count += 1
    conversation.last_interaction_at = datetime.now(timezone.utc)

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


def _derive_stable_archetype(raw_counts: str | None) -> tuple[str | None, float]:
    """Phase 4: mode archetype + confidence from accumulated observations.

    Returns (None, 0.0) until at least 3 observations exist, so a single noisy
    early scan never locks in an archetype.
    """
    try:
        counts = json.loads(raw_counts or "{}")
        if not isinstance(counts, dict) or not counts:
            return None, 0.0
        total = sum(int(v) for v in counts.values())
        if total < 3:
            return None, 0.0
        winner, top = max(counts.items(), key=lambda kv: int(kv[1]))
        return str(winner), round(int(top) / total, 3)
    except Exception:
        return None, 0.0


def _derive_preferred_strategies(raw_stats: str | None) -> list[str]:
    """Phase 5: rank strategies by a blend of copy-rate and conversion-rate.

    score = 0.5 * copy_rate + 0.5 * conversion_rate
      copy_rate       = copied / shown
      conversion_rate = landed / (landed + flopped)   [falls back to copy_rate
                        until at least 2 conversion observations exist]
    Only strategies shown >= 2 times qualify; only those with score > 0 are
    returned (a strategy that's never copied and never landed is not "preferred").
    """
    try:
        stats = json.loads(raw_stats or "{}")
        if not isinstance(stats, dict) or not stats:
            return []
        ranked: list[tuple[float, str]] = []
        for label, e in stats.items():
            if not isinstance(e, dict):
                continue
            shown = int(e.get("shown", 0))
            if shown < 2:
                continue
            copied = int(e.get("copied", 0))
            landed = int(e.get("landed", 0))
            flopped = int(e.get("flopped", 0))
            copy_rate = copied / shown if shown else 0.0
            conv_obs = landed + flopped
            if conv_obs >= 2:
                conversion_rate = landed / conv_obs
                score = 0.5 * copy_rate + 0.5 * conversion_rate
            else:
                score = copy_rate
            if score > 0:
                ranked.append((score, str(label)))
        ranked.sort(key=lambda t: t[0], reverse=True)
        return [label for _, label in ranked[:3]]
    except Exception:
        return []


async def build_conversation_context(
    conversation: Conversation,
    db: AsyncSession,
) -> ConversationContext:
    """Build a ConversationContext domain object for prompt injection."""
    topics_worked = json.loads(conversation.topics_worked or "[]")
    topics_failed = json.loads(conversation.topics_failed or "[]")

    # Phase 4 + 5: derive learned signals from accumulated stats.
    stable_archetype, archetype_confidence = _derive_stable_archetype(
        getattr(conversation, "archetype_counts", None)
    )
    preferred_strategies = _derive_preferred_strategies(
        getattr(conversation, "strategy_stats", None)
    )

    # Long-term memory: anchor to the very first interaction of this conversation.
    first_key_detail: str | None = None
    first_their_last_message: str | None = None

    first_result = await db.execute(
        select(Interaction)
        .where(Interaction.conversation_id == conversation.id)
        .order_by(Interaction.created_at.asc())
        .limit(1)
    )
    first_interaction = first_result.scalar_one_or_none()
    if first_interaction:
        first_key_detail = first_interaction.key_detail or None
        first_their_last_message = first_interaction.their_last_message or None

    # Recent flow: fetch the LAST 5 interactions for this conversation.
    # These power both the compact conversation history block and the
    # TOPIC EXHAUSTION MAP so the model sees what was just discussed.
    result = await db.execute(
        select(Interaction)
        .where(Interaction.conversation_id == conversation.id)
        .order_by(Interaction.created_at.desc())
        .limit(5)
    )
    recent_interactions = result.scalars().all()

    summaries: list[str] = []
    recent_user_replies: list[str] = []
    last_user_organic_texts: list[str] = []
    last_ai_replies_shown: list[str] = []

    # Build summaries from oldest → newest so the history reads chronologically.
    for interaction in reversed(recent_interactions):
        summary = f"[{interaction.direction}] "
        if interaction.copied_index is not None:
            copied_reply = getattr(
                interaction, f"reply_{interaction.copied_index}", None
            )
            if copied_reply:
                # Track the exact replies the user actually sent for freshness routing.
                recent_user_replies.append(copied_reply)
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

    # Topic exhaustion inputs: last 3 organic texts and last 3 reply options shown.
    # We walk the most recent interactions (limited to 5) from newest to oldest.
    for interaction in recent_interactions:
        if interaction.user_organic_text:
            last_user_organic_texts.append(interaction.user_organic_text)
        if len(last_user_organic_texts) >= 3:
            break

    # Flatten reply_0..reply_3 for each interaction until we collect 3 reply texts.
    for interaction in recent_interactions:
        for idx in range(4):
            raw_reply = getattr(interaction, f"reply_{idx}", "") or ""
            if not raw_reply:
                continue
            reply_text = raw_reply
            try:
                loaded = json.loads(raw_reply)
                if isinstance(loaded, dict) and "text" in loaded:
                    reply_text = str(loaded["text"])
            except json.JSONDecodeError:
                # If it's not JSON, treat the raw string as the text.
                pass
            last_ai_replies_shown.append(reply_text)
            if len(last_ai_replies_shown) >= 3:
                break
        if len(last_ai_replies_shown) >= 3:
            break

    return ConversationContext(
        person_name=conversation.person_name,
        stage=conversation.stage,
        tone_trend=conversation.tone_trend,
        topics_worked=topics_worked,
        topics_failed=topics_failed,
        interaction_count=conversation.interaction_count,
        recent_summaries=summaries,
        recent_user_replies=recent_user_replies[-3:],
        first_key_detail=first_key_detail,
        first_their_last_message=first_their_last_message,
        last_user_organic_texts=last_user_organic_texts[:3],
        last_ai_replies_shown=last_ai_replies_shown[:3],
        stable_archetype=stable_archetype,
        archetype_confidence=archetype_confidence,
        preferred_strategies=preferred_strategies,
    )
