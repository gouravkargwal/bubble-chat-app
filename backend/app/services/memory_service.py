from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import embed_text
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
      - core_lore (from conversations.lore if present; otherwise empty)
      - past_memories (formatted string of top-3 similarity snippets)
    """

    empty = {"person_name": "", "core_lore": "", "past_memories": ""}
    if not conversation_id:
        return empty

    # 1) Load core lore for the conversation.
    person_name: str = ""
    core_lore: str = ""
    try:
        # Lore column may or may not exist in the deployed schema;
        # the similarity pipeline must never crash.
        lore_row = await db.execute(
            text(
                """
                SELECT person_name, lore
                FROM conversations
                WHERE id = :conversation_id
                  AND user_id = :user_id
                  AND is_active = true
                """
            ),
            {"conversation_id": conversation_id, "user_id": user_id},
        )
        row_map: dict[str, Any] | None = lore_row.mappings().first()
        if row_map:
            person_name = str(row_map.get("person_name") or "")
            core_lore = str(row_map.get("lore") or "")
    except Exception:
        # Fallback: at minimum return person_name (even if lore isn't present).
        try:
            person_row = await db.execute(
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
            row_map = person_row.mappings().first()
            if row_map:
                person_name = str(row_map.get("person_name") or "")
        except Exception:
            # Keep empty values.
            pass

    # 2) Semantic snippet retrieval using embeddings + pgvector (<=>).
    try:
        if not current_text or not current_text.strip():
            return {
                "person_name": person_name,
                "core_lore": core_lore,
                "past_memories": "",
            }

        # Ensure query embeddings match the pgvector dimensionality configured
        # on `Interaction.embedding`.
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
        if not query_embedding:
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
                "query_embedding": query_embedding,
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

