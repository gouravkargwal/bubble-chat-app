"""Conversation memory manager — auto-detects and tracks per-person conversations."""

import json
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AnalysisResult, ConversationContext
from app.infrastructure.database.models import (
    ArchetypeStrategyStat,
    Conversation,
    Interaction,
)


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


_DIMENSION_KEYS = ("warmth", "playfulness", "engagement", "traditionalism", "intent")
_DIMENSION_DEFAULTS = {
    "warmth": "neutral",
    "playfulness": "balanced",
    "engagement": "medium",
    "traditionalism": "mixed",
    "intent": "open",
}


def _derive_stable_dimensions(
    raw_counts: str | None,
) -> tuple[dict[str, str] | None, str | None, float]:
    """Phase 4: mode-smooth each personality dimension across scans.

    Dimensions are the primitive; the archetype is derived from the smoothed
    dimensions (never tallied directly). Returns (stable_dims, archetype,
    confidence). All None/0.0 until at least 3 scans exist, so a single noisy
    early scan never locks in a read. Confidence = mean per-dimension agreement.
    """
    try:
        counts = json.loads(raw_counts or "{}")
        if not isinstance(counts, dict) or not counts:
            return None, None, 0.0
        # total scans = the largest per-dimension count sum (dims tallied together)
        total = max(
            (sum(int(v) for v in (counts.get(k) or {}).values()) for k in _DIMENSION_KEYS),
            default=0,
        )
        if total < 3:
            return None, None, 0.0

        stable: dict[str, str] = {}
        fractions: list[float] = []
        for k in _DIMENSION_KEYS:
            bucket = counts.get(k) or {}
            if not isinstance(bucket, dict) or not bucket:
                continue
            value, top = max(bucket.items(), key=lambda kv: int(kv[1]))
            stable[k] = str(value)
            dim_total = sum(int(v) for v in bucket.values())
            if dim_total:
                fractions.append(int(top) / dim_total)
        if not stable:
            return None, None, 0.0

        confidence = round(sum(fractions) / len(fractions), 3) if fractions else 0.0
        from agent.nodes_v2._personality import derive_archetype
        archetype = derive_archetype(
            stable.get("warmth", _DIMENSION_DEFAULTS["warmth"]),
            stable.get("playfulness", _DIMENSION_DEFAULTS["playfulness"]),
            stable.get("engagement", _DIMENSION_DEFAULTS["engagement"]),
            stable.get("traditionalism", _DIMENSION_DEFAULTS["traditionalism"]),
            stable.get("intent", _DIMENSION_DEFAULTS["intent"]),
        )
        return stable, archetype, confidence
    except Exception:
        return None, None, 0.0


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


async def bump_archetype_strategy_stat(
    db: AsyncSession,
    archetype: str | None,
    strategy_label: str | None,
    *,
    shown: int = 0,
    landed: int = 0,
    flopped: int = 0,
) -> None:
    """Atomically increment the global (archetype, strategy_label) counters.

    Uses a single UPSERT rather than read-then-write: unlike per-conversation
    strategy_stats (naturally partitioned by conversation_id), this table can
    be hit concurrently by many different users' requests for the same
    archetype, so a Python-level read-modify-write would race.
    """
    if not archetype or not strategy_label or (shown, landed, flopped) == (0, 0, 0):
        return
    stmt = pg_insert(ArchetypeStrategyStat).values(
        archetype=archetype,
        strategy_label=strategy_label,
        shown=shown,
        landed=landed,
        flopped=flopped,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["archetype", "strategy_label"],
        set_={
            "shown": ArchetypeStrategyStat.shown + shown,
            "landed": ArchetypeStrategyStat.landed + landed,
            "flopped": ArchetypeStrategyStat.flopped + flopped,
            "updated_at": func.now(),
        },
    )
    await db.execute(stmt)


async def get_archetype_preferred_strategies(
    db: AsyncSession, archetype: str | None
) -> list[str]:
    """Rank strategies by conversion rate for a given archetype, aggregated
    across every conversation that's ever recorded a clean attribution for it.

    Mirrors _derive_preferred_strategies' minimum-sample gating (>= 2
    landed+flopped observations) so a strategy shown only once doesn't
    dominate the ranking on a fluke.
    """
    if not archetype:
        return []
    result = await db.execute(
        select(ArchetypeStrategyStat).where(
            ArchetypeStrategyStat.archetype == archetype
        )
    )
    ranked: list[tuple[float, str]] = []
    for row in result.scalars().all():
        conv_obs = row.landed + row.flopped
        if conv_obs < 2:
            continue
        score = row.landed / conv_obs
        if score > 0:
            ranked.append((score, row.strategy_label))
    ranked.sort(key=lambda t: t[0], reverse=True)
    return [label for _, label in ranked[:3]]


def _reply_option_text(raw: str | None) -> str:
    """Unwrap a stored reply (JSON {"text": ...} or a plain string) to its text."""
    if not raw:
        return ""
    try:
        loaded = json.loads(raw)
        if isinstance(loaded, dict) and "text" in loaded:
            return str(loaded["text"])
    except (json.JSONDecodeError, TypeError):
        pass
    return str(raw)


def _her_last_verbatim(interaction: Interaction) -> str:
    """Her newest verbatim message that turn, from the persisted turn transcript.

    Falls back to the stored paraphrase for rows saved before transcript_json existed.
    """
    raw = getattr(interaction, "transcript_json", None)
    if raw:
        try:
            pairs = json.loads(raw)
            them = [
                str(p.get("t", "")).strip()
                for p in pairs
                if isinstance(p, dict)
                and p.get("s") == "them"
                and str(p.get("t", "")).strip()
            ]
            if them:
                return them[-1]
        except (json.JSONDecodeError, TypeError):
            pass
    return (getattr(interaction, "their_last_message", "") or "").strip()


async def build_conversation_context(
    conversation: Conversation,
    db: AsyncSession,
    current_archetype: str | None = None,
) -> ConversationContext:
    """Build a ConversationContext domain object for prompt injection.

    current_archetype is the CURRENT turn's freshly-detected archetype (always
    available from the moment the first scan runs), used for the archetype-
    conditioned strategy lookup — stable_archetype below is a smoothed read
    that stays None until >= 3 scans exist, which is exactly when a brand-new
    conversation would benefit most from cross-user archetype data.
    """
    topics_worked = json.loads(conversation.topics_worked or "[]")
    topics_failed = json.loads(conversation.topics_failed or "[]")

    # Phase 4 + 5: derive learned signals from accumulated stats.
    stable_dimensions, stable_archetype, archetype_confidence = _derive_stable_dimensions(
        getattr(conversation, "dimension_counts", None)
    )
    preferred_strategies = _derive_preferred_strategies(
        getattr(conversation, "strategy_stats", None)
    )
    archetype_preferred_strategies = await get_archetype_preferred_strategies(
        db, current_archetype or stable_archetype
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

    # Build a VERBATIM recent thread (oldest → newest) so the generator reads the
    # real back-and-forth — her actual words + exactly what the user sent — instead
    # of lossy 60-char snippets. Her words come from the persisted turn transcript
    # (transcript_json); rows saved before it fall back to the paraphrase.
    prev_her = ""
    for interaction in reversed(recent_interactions):
        parts: list[str] = []
        her = _her_last_verbatim(interaction)
        if her and her != prev_her:
            parts.append(f'her: "{her}"')
            prev_her = her
        if interaction.copied_index is not None:
            copied_reply = getattr(
                interaction, f"reply_{interaction.copied_index}", None
            )
            if copied_reply:
                # Track the exact replies the user actually sent for freshness routing.
                recent_user_replies.append(copied_reply)
                sent_text = _reply_option_text(copied_reply)
                if sent_text:
                    parts.append(f'you sent: "{sent_text}"')
        if parts:
            summaries.append(f"[{interaction.direction}] " + " | ".join(parts))
        elif interaction.copied_index is None:
            summaries.append(f"[{interaction.direction}] you didn't send any suggestion")

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
        stable_dimensions=stable_dimensions,
        photo_persona=getattr(conversation, "photo_persona", "") or "",
        preferred_strategies=preferred_strategies,
        archetype_preferred_strategies=archetype_preferred_strategies,
    )
