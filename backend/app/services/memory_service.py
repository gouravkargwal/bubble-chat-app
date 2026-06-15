from __future__ import annotations

import re
import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import embed_text
from app.core.nli import is_contradiction
from app.infrastructure.database.models import Interaction

logger = structlog.get_logger(__name__)


async def get_match_context(
    db: AsyncSession,
    user_id: str,
    conversation_id: str,
    current_text: str,
) -> dict[str, str]:
    """
    Librarian service: retrieve historical context for a match.

    Returns:
      - person_name
      - core_lore: query-aware top-K relevant facts from conversation_memories
        (falls back to a flat chronological load when no query is available)
      - past_memories (formatted string of top-3 similarity snippets)
    """

    empty = {"person_name": "", "core_lore": "", "past_memories": ""}
    if not conversation_id:
        return empty

    # 1) Load person_name.
    person_name: str = ""
    try:
        name_row = await db.execute(
            text(
                """
                SELECT person_name
                FROM conversations
                WHERE id = :conversation_id
                  AND user_id = :user_id
                  AND is_active = true
                """
            ),
            {"conversation_id": conversation_id, "user_id": user_id},
        )
        row_map: dict[str, Any] | None = name_row.mappings().first()
        if row_map:
            person_name = str(row_map.get("person_name") or "")
    except Exception:
        pass

    # 2) Compute the query embedding ONCE — reused for both query-aware lore
    #    ranking and past-memory snippet retrieval. Dimensionality is matched to
    #    the pgvector column configured on `Interaction.embedding`.
    query_embedding: list[float] | None = None
    emb_str: str | None = None
    if current_text and current_text.strip():
        try:
            expected_dim_raw = getattr(Interaction.embedding.type, "dim", None)
            expected_dim: int | None = None
            if expected_dim_raw is not None:
                try:
                    expected_dim = int(expected_dim_raw)
                except (TypeError, ValueError):
                    expected_dim = None
            query_embedding = await embed_text(
                current_text,
                dimensions=expected_dim if expected_dim and expected_dim > 0 else None,
            )
            if query_embedding:
                emb_str = f"[{','.join(str(x) for x in query_embedding)}]"
        except Exception:
            query_embedding = None
            emb_str = None

    # 3) core_lore — query-aware retrieval from conversation_memories.
    #    With a query embedding, fetch only the top-K most relevant facts
    #    (ordered by cosine distance) rather than dumping every fact, so the
    #    prompt stays focused as a conversation accumulates dozens of facts.
    #    Facts that never embedded (a write-time embed failure) can't be ranked,
    #    so they are appended unconditionally and never silently dropped.
    #    Without a query embedding we fall back to a flat chronological load.
    core_lore: str = ""
    _LORE_TOP_K = 8
    try:
        if emb_str:
            relevant_rows = await db.execute(
                text(
                    """
                    SELECT fact_text, (embedding <=> :emb) AS distance
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT :k
                    """
                ),
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "emb": emb_str,
                    "k": _LORE_TOP_K,
                },
            )
            unranked_rows = await db.execute(
                text(
                    """
                    SELECT fact_text
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NULL
                    ORDER BY created_at ASC
                    """
                ),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            seen: set[str] = set()
            lore_facts: list[str] = []
            for r in relevant_rows.mappings().all():
                ft = str(r["fact_text"]) if r["fact_text"] else ""
                if ft and ft not in seen:
                    seen.add(ft)
                    lore_facts.append(ft)
            for r in unranked_rows.mappings().all():
                ft = str(r["fact_text"]) if r["fact_text"] else ""
                if ft and ft not in seen:
                    seen.add(ft)
                    lore_facts.append(ft)
            core_lore = "\n".join(lore_facts)
        else:
            facts_row = await db.execute(
                text(
                    """
                    SELECT fact_text
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                    ORDER BY created_at ASC
                    """
                ),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            core_lore = "\n".join(
                str(r["fact_text"]) for r in facts_row.mappings().all() if r["fact_text"]
            )
    except Exception:
        pass

    # 4) past_memories — query-aware snippet retrieval from interactions.
    try:
        if not emb_str:
            return {
                "person_name": person_name,
                "core_lore": core_lore,
                "past_memories": "",
            }

        # Similarity bouncer: only return rows with cosine distance < 0.25.
        #
        # Note: pgvector's `<=>` operator returns the distance for the chosen metric.
        # In this codebase, we use cosine-distance style filtering as required.
        vector_sql = text(
            """
            SELECT
                i.their_last_message,
                i.user_organic_text,
                i.key_detail,
                i.created_at,
                (i.embedding <=> :query_embedding) AS cosine_distance
            FROM interactions AS i
            WHERE i.user_id = :user_id
              AND i.conversation_id = :conversation_id
              AND i.embedding IS NOT NULL
              AND (i.embedding <=> :query_embedding) < 0.25
            ORDER BY (i.embedding <=> :query_embedding) ASC
            LIMIT 3
            """
        )

        rows = await db.execute(
            vector_sql,
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "query_embedding": emb_str,
            },
        )

        results = rows.mappings().all()
        if not results:
            return {
                "person_name": person_name,
                "core_lore": core_lore,
                "past_memories": "",
            }

        past_mem_lines: list[str] = []
        for idx, r in enumerate(results, start=1):
            their_last_message = str(r.get("their_last_message") or "")
            user_organic_text = str(r.get("user_organic_text") or "")
            key_detail = str(r.get("key_detail") or "")

            # Build a concise snippet; callers can embed this as-is in RAG prompts.
            snippet_parts: list[str] = []
            if their_last_message:
                snippet_parts.append(f"her_last_message: {their_last_message}")
            if user_organic_text:
                snippet_parts.append(f"your_organic_text: {user_organic_text}")
            if key_detail:
                snippet_parts.append(f"key_detail: {key_detail}")

            past_mem_lines.append(f"{idx}. " + " | ".join(snippet_parts))

        past_memories = "\n".join(past_mem_lines)
        return {
            "person_name": person_name,
            "core_lore": core_lore,
            "past_memories": past_memories,
        }
    except Exception:
        # Critical: retrieval failures should never crash the app.
        return {
            "person_name": person_name,
            "core_lore": core_lore,
            "past_memories": "",
        }


async def upsert_conversation_memory(
    db: AsyncSession,
    *,
    user_id: str,
    conversation_id: str,
    fact_text: str,
) -> None:
    """Persist a single fact into conversation_memories.

    1. Embed the new fact.
    2. Find semantically similar existing facts (cosine distance < 0.30).
    3. For each similar fact, run NLI — supersede if contradiction detected,
       skip insert if entailment (same fact restated).
    4. Insert new fact with its embedding.

    Never raises — memory ingestion must not block the response.
    """
    fact_text = (fact_text or "").strip()
    if not fact_text:
        return

    try:
        new_embedding = await embed_text(fact_text)
        if not new_embedding:
            return

        embedding_str = f"[{','.join(str(x) for x in new_embedding)}]"

        # Find existing active facts within semantic neighbourhood.
        similar_rows = await db.execute(
            text(
                """
                SELECT id, fact_text,
                       (embedding <=> :emb) AS distance
                FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                  AND embedding IS NOT NULL
                  AND (embedding <=> :emb) < 0.30
                ORDER BY distance ASC
                LIMIT 5
                """
            ),
            {"user_id": user_id, "conversation_id": conversation_id, "emb": embedding_str},
        )
        similar = similar_rows.mappings().all()

        skip_insert = False
        for row in similar:
            existing_fact = str(row["fact_text"])
            distance = float(row["distance"])

            # Very high similarity — likely a restatement, not a new fact.
            if distance < 0.10:
                skip_insert = True
                continue

            contradicts = await is_contradiction(existing_fact, fact_text)
            if contradicts:
                await db.execute(
                    text(
                        "UPDATE conversation_memories SET superseded_at = now() WHERE id = :id"
                    ),
                    {"id": row["id"]},
                )
                logger.info(
                    "memory_contradiction_superseded",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    old_fact=existing_fact,
                    new_fact=fact_text,
                )

        if not skip_insert:
            await db.execute(
                text(
                    """
                    INSERT INTO conversation_memories
                        (id, user_id, conversation_id, fact_text, embedding, created_at)
                    VALUES
                        (:id, :user_id, :conversation_id, :fact_text, :embedding, now())
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "fact_text": fact_text,
                    "embedding": embedding_str,
                },
            )

        await db.commit()

    except Exception as e:
        logger.warning(
            "upsert_conversation_memory_failed",
            user_id=user_id,
            conversation_id=conversation_id,
            fact_text=fact_text[:120],
            error=str(e),
        )


def _line_should_be_scrubbed(line: str, contradictions: list[str]) -> bool:
    """
    Heuristic: scrub lore lines that match contradiction text signals.

    We keep this conservative to avoid deleting the whole lore blob.
    """
    line_l = line.lower()
    for contradiction in contradictions:
        c = (contradiction or "").strip().lower()
        if not c:
            continue
        if c in line_l:
            return True
        # Token overlap fallback when phrasing differs.
        tokens = [t for t in re.findall(r"[a-z0-9]+", c) if len(t) >= 4]
        if not tokens:
            continue
        overlap = sum(1 for t in tokens if t in line_l)
        if overlap >= 2:
            return True
    return False


async def scrub_lore_from_contradictions(
    db: AsyncSession,
    *,
    user_id: str,
    conversation_id: str,
    contradictions: list[str],
) -> dict[str, Any]:
    """
    Memory scrub for poisoned/stale lore.

    If lore exists, remove lines that appear to conflict with visual truth signals
    reported by vision_node. Safe no-op if lore column is absent.
    """
    if not conversation_id or not contradictions:
        return {"updated": False, "removed_lines": 0, "new_lore_chars": 0}

    try:
        row = await db.execute(
            text(
                """
                SELECT lore
                FROM conversations
                WHERE id = :conversation_id
                  AND user_id = :user_id
                  AND is_active = true
                """
            ),
            {"conversation_id": conversation_id, "user_id": user_id},
        )
        row_map = row.mappings().first()
        lore = str((row_map or {}).get("lore") or "")
        if not lore.strip():
            return {"updated": False, "removed_lines": 0, "new_lore_chars": 0}

        lines = lore.splitlines()
        kept = [ln for ln in lines if not _line_should_be_scrubbed(ln, contradictions)]
        removed = len(lines) - len(kept)
        if removed <= 0:
            return {"updated": False, "removed_lines": 0, "new_lore_chars": len(lore)}

        new_lore = "\n".join(kept).strip()
        await db.execute(
            text(
                """
                UPDATE conversations
                SET lore = :new_lore
                WHERE id = :conversation_id
                  AND user_id = :user_id
                """
            ),
            {
                "new_lore": new_lore,
                "conversation_id": conversation_id,
                "user_id": user_id,
            },
        )
        await db.commit()

        logger.warning(
            "lore_memory_scrub_applied",
            user_id=user_id,
            conversation_id=conversation_id,
            contradiction_count=len(contradictions),
            removed_lines=removed,
            new_lore_chars=len(new_lore),
        )
        return {"updated": True, "removed_lines": removed, "new_lore_chars": len(new_lore)}
    except Exception as e:
        # No hard-fail path: some deployments may not have `lore` column yet.
        logger.warning(
            "lore_memory_scrub_skipped",
            user_id=user_id,
            conversation_id=conversation_id,
            error=str(e),
        )
        return {"updated": False, "removed_lines": 0, "new_lore_chars": 0}

