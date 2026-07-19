"""
Shared seed helpers for RAG pipeline testing.

Extracted from scripts/seed_and_test_rag.py so both the seed+test script and
the eval-rag evaluator can reuse them without duplication.
"""

from __future__ import annotations

import json
import random
import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embeddings import embed_text

logger = structlog.get_logger(__name__)

# ── Default test identities ──────────────────────────────────────────────────
TEST_USER_ID = "test-user-rag-0000-0000-000000000001"
TEST_CONVERSATION_ID = "test-conv-rag-0000-0000-000000000001"
PERSON_NAME = "Priya"

# ── Default seed data ────────────────────────────────────────────────────────

SEED_INTERACTIONS = [
    {
        "their_last_message": "Hey! how r u?",
        "key_detail": "Says hi first — polite opener",
        "direction": "opener",
        "transcript_json": json.dumps([{"s": "them", "t": "Hey! how r u?"}]),
        "reply_0": json.dumps({"text": "hey priya, finally matched. took you long enough", "strategy_label": "FRAME CONTROL", "coach_reasoning": "You flipped the waiting dynamic"}),
        "reply_1": json.dumps({"text": "hey! was hoping youd text first but here we are", "strategy_label": "PATTERN INTERRUPT", "coach_reasoning": "You teased her for not texting first"}),
        "reply_2": json.dumps({"text": "hii priya, hows your day going? finally matched haha", "strategy_label": "SOFT CLOSE", "coach_reasoning": "Warm but not overeager opener"}),
        "reply_3": json.dumps({"text": "hey! your bio was way too interesting to swipe past", "strategy_label": "VALUE ANCHOR", "coach_reasoning": "You referenced her bio without being generic"}),
    },
    {
        "their_last_message": "haha im good! just came back from a trek in himachal, it was amazing",
        "key_detail": "She mentions trekking in Himachal — adventure angle",
        "direction": "quick_reply",
        "transcript_json": json.dumps([
            {"s": "them", "t": "Hey! how r u?"},
            {"s": "user", "t": "hey! finally matched haha, hows your day going"},
            {"s": "them", "t": "haha im good! just came back from a trek in himachal, it was amazing"},
        ]),
        "reply_0": json.dumps({"text": "himachal? okay flex. which trek — the one with chai stalls every km?", "strategy_label": "PUSH-PULL", "coach_reasoning": "You validated her adventurous side while keeping it playful"}),
        "reply_1": json.dumps({"text": "ah so youre one of those 'i went to himachal' people. cute", "strategy_label": "FRAME CONTROL", "coach_reasoning": "You framed her as adventure girl without asking a boring question"}),
        "reply_2": json.dumps({"text": "wait you actually go outside? rare breed", "strategy_label": "PATTERN INTERRUPT", "coach_reasoning": "You subverted her expectation by acting surprised"}),
        "reply_3": json.dumps({"text": "that sounds amazing ngl. which part of himachal did you go to?", "strategy_label": "SOFT CLOSE", "coach_reasoning": "Warm follow-up that invites her to share more"}),
    },
    {
        "their_last_message": "i went to tosh village! it was so peaceful, no network, just mountains",
        "key_detail": "Tosh village — offbeat, no network",
        "direction": "keep_playful",
        "transcript_json": json.dumps([
            {"s": "them", "t": "Hey! how r u?"},
            {"s": "user", "t": "hey! finally matched haha, hows your day going"},
            {"s": "them", "t": "haha im good! just came back from a trek in himachal, it was amazing"},
            {"s": "user", "t": "himachal? okay flex. which trek?"},
            {"s": "them", "t": "i went to tosh village! it was so peaceful, no network, just mountains"},
        ]),
        "reply_0": json.dumps({"text": "tosh? okay you actually have taste. most people just do kasol and call it a day", "strategy_label": "FRAME CONTROL", "coach_reasoning": "You separated her from the crowd with a compliment"}),
        "reply_1": json.dumps({"text": "no network? so you were unreachable. sounds like a flex tbh", "strategy_label": "PUSH-PULL", "coach_reasoning": "You teased the no-network detail"}),
        "reply_2": json.dumps({"text": "tosh is beautiful. did you find any good cafes or just raw nature?", "strategy_label": "SOFT CLOSE", "coach_reasoning": "Warm follow-up that shows awareness of the location"}),
        "reply_3": json.dumps({"text": "no network + mountains = you were forced to touch grass. love that for you", "strategy_label": "PATTERN INTERRUPT", "coach_reasoning": "You made the digital detox sound like a flex"}),
    },
    {
        "their_last_message": "i knowww but im a software engineer so being offline was scary at first \U0001f602",
        "key_detail": "She's a software engineer — job angle",
        "direction": "quick_reply",
        "transcript_json": json.dumps([
            {"s": "them", "t": "Hey! how r u?"},
            {"s": "user", "t": "hey! finally matched haha, hows your day going"},
            {"s": "them", "t": "haha im good! just came back from a trek in himachal, it was amazing"},
            {"s": "user", "t": "himachal? okay flex. which trek?"},
            {"s": "them", "t": "i went to tosh village! it was so peaceful, no network, just mountains"},
            {"s": "user", "t": "no network? sounds like a flex tbh"},
            {"s": "them", "t": "i knowww but im a software engineer so being offline was scary at first \U0001f602"},
        ]),
        "reply_0": json.dumps({"text": "software engineer who treks? you're fighting the stereotype and winning", "strategy_label": "PUSH-PULL", "coach_reasoning": "You validated both her job and hobby in one line"}),
        "reply_1": json.dumps({"text": "ah a dev. so you debug on weekends too or just weekdays?", "strategy_label": "FRAME CONTROL", "coach_reasoning": "You teased the engineer identity with an inside joke"}),
        "reply_2": json.dumps({"text": "ah a software engineer. so you spend all day fixing bugs and then go climb mountains to reset?", "strategy_label": "PATTERN INTERRUPT", "coach_reasoning": "You painted a funny contrast between desk job and adventure"}),
        "reply_3": json.dumps({"text": "fair. which stack do you work with?", "strategy_label": "SOFT CLOSE", "coach_reasoning": "Simple question that invites her to talk about her work"}),
    },
    {
        "their_last_message": "yeah! im a backend dev — python, go, all that. what about you?",
        "key_detail": "Backend dev — Python, Go — common ground",
        "direction": "keep_playful",
        "transcript_json": json.dumps([
            {"s": "them", "t": "Hey! how r u?"},
            {"s": "user", "t": "hey! finally matched haha, hows your day going"},
            {"s": "them", "t": "haha im good! just came back from a trek in himachal, it was amazing"},
            {"s": "user", "t": "himachal? okay flex. which trek?"},
            {"s": "them", "t": "i went to tosh village! it was so peaceful, no network, just mountains"},
            {"s": "user", "t": "no network? sounds like a flex tbh"},
            {"s": "them", "t": "i knowww but im a software engineer so being offline was scary at first \U0001f602"},
            {"s": "user", "t": "ah a dev. so you debug on weekends too?"},
            {"s": "them", "t": "yeah! im a backend dev — python, go, all that. what about you?"},
        ]),
        "reply_0": json.dumps({"text": "python and go? okay you actually know your stuff. that's... attractive ngl", "strategy_label": "PUSH-PULL", "coach_reasoning": "You validated her tech skills while keeping it flirty"}),
        "reply_1": json.dumps({"text": "so you write go and climb mountains? you're either superhuman or avoiding something", "strategy_label": "PATTERN INTERRUPT", "coach_reasoning": "You playfully accused her of being too impressive"}),
        "reply_2": json.dumps({"text": "backend dev who treks and is on a dating app? multi-threaded queen", "strategy_label": "FRAME CONTROL", "coach_reasoning": "You framed her as impressive without directly saying it"}),
        "reply_3": json.dumps({"text": "that's cool! i work with python too. what's your favorite go feature?", "strategy_label": "SOFT CLOSE", "coach_reasoning": "Common ground question that invites sharing"}),
    },
]

SEED_FACTS: list[dict] = [
    {"text": "Priya is 26 years old from Mumbai", "category": "identity", "importance": 5},
    {"text": "Priya works as a software engineer at a fintech startup", "category": "identity", "importance": 5},
    {"text": "She is a vegetarian", "category": "preference", "importance": 4},
    {"text": "She loves trekking and has been to Himachal 3 times", "category": "opinion", "importance": 3},
    {"text": "She has a younger sister who is studying in Delhi", "category": "identity", "importance": 4},
    {"text": "She speaks Marathi, Hindi, and English fluently", "category": "factual", "importance": 3},
    {"text": "She is looking for a serious relationship", "category": "opinion", "importance": 4},
    {"text": "She enjoys trying new cafes in Bandra", "category": "opinion", "importance": 3},
    {"text": "She recently adopted a stray puppy named Chiku", "category": "factual", "importance": 3},
    {"text": "She studied at NMIMS Mumbai", "category": "identity", "importance": 4},
]

SEED_ENTITIES: list[tuple[str, str]] = [
    ("priya", "person"),
    ("mumbai", "location"),
    ("software engineer", "profession"),
    ("fintech", "organization"),
    ("himachal", "location"),
    ("nmims mumbai", "organization"),
    ("chiku", "pet"),
    ("marathi", "language"),
    ("hindi", "language"),
    ("english", "language"),
    ("bandra", "location"),
    ("trekking", "hobby"),
]

SEED_EDGES: list[tuple[str, str, str]] = [
    ("priya", "mumbai", "LIVES_IN"),
    ("priya", "software engineer", "WORKS_AS"),
    ("priya", "fintech", "WORKS_AT"),
    ("priya", "nmims mumbai", "STUDIED_AT"),
    ("priya", "trekking", "ENJOYS"),
    ("priya", "marathi", "SPEAKS"),
    ("priya", "hindi", "SPEAKS"),
    ("priya", "english", "SPEAKS"),
    ("priya", "chiku", "OWNS"),
]


# ── Helpers ──────────────────────────────────────────────────────────────────


def mock_embedding(dim: int = 768) -> list[float]:
    """Deterministic mock 768d vector (for --no-llm mode or when API is down)."""
    rng = random.Random(42)
    vec = [rng.random() for _ in range(dim)]
    norm = (sum(x * x for x in vec)) ** 0.5
    return [x / norm for x in vec]


async def ensure_embedding(text: str, use_llm: bool) -> list[float] | None:
    """Get embedding — real if use_llm and API key available, else mock."""
    if use_llm and settings.gemini_api_key:
        emb = await embed_text(text)
        if emb:
            return emb
        logger.warning("embedding_api_returned_none", text=text[:50])
    return mock_embedding()


def embedding_to_str(embedding: list[float]) -> str:
    """Format embedding list as PG vector string literal."""
    return f"[{','.join(str(x) for x in embedding)}]"


# ── Seed functions ───────────────────────────────────────────────────────────


async def seed_user_and_conversation(
    db: AsyncSession,
    user_id: str = TEST_USER_ID,
    conversation_id: str = TEST_CONVERSATION_ID,
    person_name: str = PERSON_NAME,
) -> None:
    """Create test user + conversation (idempotent — ON CONFLICT DO NOTHING)."""
    await db.execute(
        text("""
            INSERT INTO users (id, device_id, tier, tier_source, bonus_replies, marketing_consent, created_at, last_seen_at)
            VALUES (:id, :device_id, :tier, 'signup', 0, true, now(), now())
            ON CONFLICT (id) DO NOTHING
        """),
        {"id": user_id, "device_id": f"rag-test-device-{user_id}", "tier": "free"},
    )
    await db.execute(
        text("""
            INSERT INTO conversations (
                id, user_id, person_name, stage, tone_trend,
                topics_worked, topics_failed, dimension_counts, strategy_stats,
                photo_persona, interaction_count, is_active,
                last_interaction_at, created_at
            ) VALUES (
                :id, :user_id, :person_name, 'building_chemistry', 'stable',
                '[]', '[]', '{}', '{}',
                '', 5, true,
                now(), now()
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {"id": conversation_id, "user_id": user_id, "person_name": person_name},
    )
    await db.commit()


async def seed_interactions(
    db: AsyncSession,
    user_id: str = TEST_USER_ID,
    conversation_id: str = TEST_CONVERSATION_ID,
    interactions: list[dict] | None = None,
) -> None:
    """Insert mock chat interactions (idempotent — ON CONFLICT)."""
    rows = interactions or SEED_INTERACTIONS
    for i, row in enumerate(rows):
        iid = f"test-int-rag-{i:04d}-0000-000000000000"
        await db.execute(
            text("""
                INSERT INTO interactions (
                    id, conversation_id, user_id, direction,
                    their_last_message, key_detail, transcript_json,
                    reply_0, reply_1, reply_2, reply_3,
                    llm_model, temperature_used, screenshot_count,
                    created_at
                ) VALUES (
                    :id, :conv_id, :user_id, :direction,
                    :their_last_message, :key_detail, :transcript_json,
                    :reply_0, :reply_1, :reply_2, :reply_3,
                    'test-seed', 0.7, 1, now() - :age * interval '1 hour'
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": iid,
                "conv_id": conversation_id,
                "user_id": user_id,
                "direction": row["direction"],
                "their_last_message": row["their_last_message"],
                "key_detail": row["key_detail"],
                "transcript_json": row["transcript_json"],
                "reply_0": row["reply_0"],
                "reply_1": row["reply_1"],
                "reply_2": row["reply_2"],
                "reply_3": row["reply_3"],
                "age": len(rows) - i,
            },
        )
    await db.commit()


async def seed_facts(
    db: AsyncSession,
    facts: list[dict],
    use_llm: bool = True,
    user_id: str = TEST_USER_ID,
    conversation_id: str = TEST_CONVERSATION_ID,
    prefix: str = "test-fact-rag",
) -> int:
    """Insert facts with embeddings into conversation_memories. Returns count."""
    count = 0
    for i, fact in enumerate(facts):
        fid = f"{prefix}-{i:04d}-0000-000000000000"
        existing = await db.execute(
            text("SELECT 1 FROM conversation_memories WHERE id = :id"),
            {"id": fid},
        )
        if existing.first():
            count += 1
            continue

        embedding = await ensure_embedding(fact["text"], use_llm)
        if not embedding:
            logger.warning("Skipping fact due to missing embedding", fact=fact["text"][:50])
            continue

        await db.execute(
            text("""
                INSERT INTO conversation_memories
                    (id, user_id, conversation_id, fact_text, embedding,
                     importance_score, fact_category, created_at)
                VALUES
                    (:id, :user_id, :conv_id, :fact_text, CAST(:embedding AS vector),
                     :importance, :category, now())
            """),
            {
                "id": fid,
                "user_id": user_id,
                "conv_id": conversation_id,
                "fact_text": fact["text"],
                "embedding": embedding_to_str(embedding),
                "importance": fact.get("importance", 3),
                "category": fact.get("category", "factual"),
            },
        )
        count += 1

    await db.commit()
    return count


async def seed_graph(
    db: AsyncSession,
    entities: list[tuple[str, str]] | None = None,
    edges: list[tuple[str, str, str]] | None = None,
    user_id: str = TEST_USER_ID,
    conversation_id: str = TEST_CONVERSATION_ID,
) -> int:
    """Insert entities + edges for graph RAG. Returns entity count."""
    ents = entities or SEED_ENTITIES
    edgs = edges or SEED_EDGES

    seen_names: set[str] = set()
    for name, etype in ents:
        raw = f"test-ent-rag-{name.replace(' ', '_')}"
        eid = raw[:36]
        await db.execute(
            text("""
                INSERT INTO conversation_memory_entities
                    (id, user_id, conversation_id, entity_name, entity_type, created_at)
                VALUES (:id, :uid, :cid, :name, :type, now())
                ON CONFLICT (conversation_id, entity_name) DO NOTHING
            """),
            {"id": eid, "uid": user_id, "cid": conversation_id, "name": name, "type": etype},
        )
        seen_names.add(name)

    for src, tgt, rel in edgs:
        raw = f"test-edg-rag-{src}_{rel}_{tgt}".replace(" ", "_")
        eid = raw[:36]
        await db.execute(
            text("""
                INSERT INTO conversation_memory_edges
                    (id, user_id, conversation_id,
                     source_entity_id, target_entity_id,
                     relationship_type, weight, created_at)
                VALUES (
                    :id, :uid, CAST(:cid AS VARCHAR),
                    (SELECT id FROM conversation_memory_entities
                     WHERE conversation_id = CAST(:cid AS VARCHAR) AND entity_name = :src LIMIT 1),
                    (SELECT id FROM conversation_memory_entities
                     WHERE conversation_id = CAST(:cid AS VARCHAR) AND entity_name = :tgt LIMIT 1),
                    :rel, 1.0, now()
                )
                ON CONFLICT DO NOTHING
            """),
            {"id": eid, "uid": user_id, "cid": conversation_id, "src": src, "tgt": tgt, "rel": rel},
        )

    await db.commit()
    return len(seen_names)


async def clean_test_data(
    db: AsyncSession,
    user_id: str = TEST_USER_ID,
    conversation_id: str = TEST_CONVERSATION_ID,
) -> None:
    """Remove all test data for a clean re-run. Deletes child tables first.

    Note: `conversations` and `users` don't have `conversation_id` — they ARE
    the parent, so we match by their `id` column directly.
    """
    tables_spec: list[tuple[str, bool]] = [
        ("conversation_memory_edges", True),   # has conversation_id
        ("conversation_memory_entities", True), # has conversation_id
        ("conversation_memories", True),        # has conversation_id
        ("interactions", True),                 # has conversation_id
        ("conversations", False),               # no conversation_id, matched by id
        ("users", False),                       # no conversation_id, matched by id
    ]
    for table, has_cid in tables_spec:
        clauses = []
        if has_cid:
            clauses.append(f"conversation_id = '{conversation_id}'")
            clauses.append(f"user_id = '{user_id}'")
        else:
            clauses.append(f"id = '{conversation_id}'")
            clauses.append(f"id = '{user_id}'")
        clauses.append("id::text LIKE 'test-%'")
        where = " OR ".join(clauses)
        await db.execute(text(f"DELETE FROM {table} WHERE {where}"))
    await db.commit()


async def seed_all_default(
    db: AsyncSession,
    use_llm: bool = True,
    user_id: str = TEST_USER_ID,
    conversation_id: str = TEST_CONVERSATION_ID,
    person_name: str = PERSON_NAME,
) -> dict[str, int]:
    """Convenience: seed user + conversation + interactions + facts + graph."""
    await seed_user_and_conversation(db, user_id, conversation_id, person_name)
    await seed_interactions(db, user_id, conversation_id)
    fact_count = await seed_facts(db, SEED_FACTS, use_llm, user_id, conversation_id)
    entity_count = await seed_graph(db, user_id=user_id, conversation_id=conversation_id)
    return {"facts": fact_count, "entities": entity_count}
