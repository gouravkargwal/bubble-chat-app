from __future__ import annotations

import re
import uuid
import asyncio
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import embed_text
from app.core.reranker import rerank_passages
from app.infrastructure.database.models import Interaction
from app.services.rag_improvements import (
    calculate_adaptive_threshold,
    generate_query_variants,
    merge_contexts,
    rate_fact_importance,
)

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
            text("""
                SELECT person_name
                FROM conversations
                WHERE id = :conversation_id
                  AND user_id = :user_id
                  AND is_active = true
                """),
            {"conversation_id": conversation_id, "user_id": user_id},
        )
        row_map: dict[str, Any] | None = name_row.mappings().first()
        if row_map:
            person_name = str(row_map.get("person_name") or "")
    except Exception:
        pass

    # 2) Compute query embeddings — Multi-query retrieval
    #    Generate multiple query variants, embed each, and fuse results via RRF.
    query_embedding: list[float] | None = None
    emb_str: str | None = None
    all_query_embeddings: list[list[float]] = []
    all_query_emb_strs: list[str] = []

    if current_text and current_text.strip():
        try:
            expected_dim_raw = getattr(Interaction.embedding.type, "dim", None)
            expected_dim: int | None = None
            if expected_dim_raw is not None:
                try:
                    expected_dim = int(expected_dim_raw)
                except (TypeError, ValueError):
                    expected_dim = None

            # Prepend person_name early so all embeddings are automatically enriched
            query_base = current_text.strip()
            if person_name and person_name.strip():
                query_base = f"{person_name}: {query_base}"

            # Generate query variants for multi-query retrieval
            query_variants = [
                qv.strip()
                for qv in generate_query_variants(
                    current_text=query_base,
                    person_name="",
                    max_variants=3,
                )
                if qv.strip()
            ]

            # Fire all embedding network requests concurrently
            if query_variants:
                embedding_tasks = [
                    embed_text(
                        qv,
                        dimensions=(
                            expected_dim if expected_dim and expected_dim > 0 else None
                        ),
                    )
                    for qv in query_variants
                ]

                resolved_embeddings = await asyncio.gather(
                    *embedding_tasks, return_exceptions=True
                )

                for emb in resolved_embeddings:
                    if emb and isinstance(emb, list):
                        all_query_embeddings.append(emb)
                        all_query_emb_strs.append(f"[{','.join(str(x) for x in emb)}]")

            # Primary embedding is the averaged vector across all query variants
            if all_query_embeddings:
                num_emb = len(all_query_embeddings)
                if num_emb > 1:
                    avg_emb = [
                        sum(dims) / num_emb for dims in zip(*all_query_embeddings)
                    ]
                    query_embedding = avg_emb
                    emb_str = f"[{','.join(str(x) for x in avg_emb)}]"
                else:
                    query_embedding = all_query_embeddings[0]
                    emb_str = all_query_emb_strs[0]
            else:
                query_embedding = None
                emb_str = None
        except Exception:
            query_embedding = None
            emb_str = None

    # ── If no embedding, fall back to chronological fact load and return early ──
    if not emb_str:
        core_lore: str = ""
        pinned_facts: list[str] = []
        try:
            pinned_rows = await db.execute(
                text("""
                    SELECT fact_text FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND fact_category = 'identity'
                    ORDER BY created_at ASC
                    LIMIT 20
                """),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            pinned_facts = [
                r["fact_text"].strip()
                for r in pinned_rows.mappings().all()
                if r["fact_text"]
            ]
            facts_row = await db.execute(
                text("""
                    SELECT fact_text
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                    ORDER BY created_at ASC
                """),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            all_lore = [
                str(r["fact_text"])
                for r in facts_row.mappings().all()
                if r["fact_text"]
            ]
            seen_lore = set(all_lore)
            for pf in pinned_facts:
                if pf not in seen_lore:
                    all_lore.insert(0, pf)
            core_lore = "\n".join(all_lore)
        except Exception:
            pass
        return {
            "person_name": person_name,
            "core_lore": core_lore,
            "past_memories": "",
        }

    # ── Constants shared by both retrieval streams ──
    # Static top-K: FlashRank cross-encoder naturally trims the pool, so no
    # expensive COUNT(*) needed for dynamic K. Reduces one DB round-trip.
    _LORE_TOP_K = 8
    _RRF_K = 60
    _RERANK_POOL = 50
    _LORE_RECENCY_LAMBDA = 0.03
    _LORE_RECENCY_HALFLIFE_S = 14 * 86400  # 14 days

    # ═══════════════════════════════════════════════════════════════════════
    #  FIX 1 & 2: Run core_lore and past_memories CONCURRENTLY via gather.
    #  Also combines 3 sequential DB queries (vector + lexical + unranked)
    #  into a single CTE query — 1 network round-trip instead of 3.
    # ═══════════════════════════════════════════════════════════════════════

    async def _fetch_core_lore() -> str:
        """Retrieve and rerank query-aware facts from conversation_memories."""
        try:
            # --- Pinned identity facts (fast, independent) ---
            pinned_facts: list[str] = []
            try:
                pinned_rows = await db.execute(
                    text("""
                        SELECT fact_text FROM conversation_memories
                        WHERE user_id = :user_id
                          AND conversation_id = :conversation_id
                          AND superseded_at IS NULL
                          AND fact_category = 'identity'
                        ORDER BY created_at ASC
                        LIMIT 20
                    """),
                    {"user_id": user_id, "conversation_id": conversation_id},
                )
                pinned_facts = [
                    r["fact_text"].strip()
                    for r in pinned_rows.mappings().all()
                    if r["fact_text"]
                ]
            except Exception:
                pinned_facts = []

            # --- Combined CTE: fires vector + lexical + unranked in ONE round-trip ---
            # FIX 2: Reduces 3 sequential DB queries to 1 using CTEs + UNION ALL.
            # PostgreSQL executes the CTEs in parallel, saving 2 network round-trips.
            combined_sql = text("""
                WITH
                vector_results AS (
                    SELECT fact_text, importance_score,
                           ROW_NUMBER() OVER (ORDER BY (
                               (embedding <=> :emb)
                               - :lam * EXP(- EXTRACT(EPOCH FROM (now() - created_at)) / :hl)
                               - COALESCE(:importance_boost * (importance_score - 3), 0)
                           ) ASC) AS rank
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NOT NULL
                    ORDER BY (
                        (embedding <=> :emb)
                        - :lam * EXP(- EXTRACT(EPOCH FROM (now() - created_at)) / :hl)
                        - COALESCE(:importance_boost * (importance_score - 3), 0)
                    ) ASC
                    LIMIT :pool
                ),
                lexical_results AS (
                    SELECT fact_text,
                           ROW_NUMBER() OVER (ORDER BY ts_rank(
                               to_tsvector('simple', fact_text),
                               websearch_to_tsquery('simple', :q)
                           ) DESC) AS rank
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NOT NULL
                      AND to_tsvector('simple', fact_text)
                          @@ websearch_to_tsquery('simple', :q)
                    ORDER BY ts_rank(
                        to_tsvector('simple', fact_text),
                        websearch_to_tsquery('simple', :q)
                    ) DESC
                    LIMIT :pool
                ),
                unranked_results AS (
                    SELECT fact_text, 0 AS rank
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NULL
                    ORDER BY created_at ASC
                    LIMIT 5
                )
                SELECT 'vector' AS source, fact_text, importance_score, rank
                FROM vector_results
                UNION ALL
                SELECT 'lexical' AS source, fact_text, NULL::int AS importance_score, rank
                FROM lexical_results
                UNION ALL
                SELECT 'unranked' AS source, fact_text, NULL::int AS importance_score, rank
                FROM unranked_results
                ORDER BY source, rank
            """)

            combined_rows = await db.execute(
                combined_sql,
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "emb": emb_str,
                    "q": current_text,
                    "pool": _RERANK_POOL,
                    "lam": _LORE_RECENCY_LAMBDA,
                    "hl": _LORE_RECENCY_HALFLIFE_S,
                    "importance_boost": 0.02,
                },
            )
            combined = combined_rows.mappings().all()

            # Group by source for RRF (preserves order from CTE)
            vec_data = [r for r in combined if r["source"] == "vector"]
            lex_data = [r for r in combined if r["source"] == "lexical"]
            unranked_data = [r for r in combined if r["source"] == "unranked"]

            # --- Reciprocal Rank Fusion ---
            rrf_scores: dict[str, float] = {}
            rrf_order: list[str] = []
            for data in (vec_data, lex_data):
                for row in data:
                    ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
                    if not ft:
                        continue
                    rank = int(row["rank"])
                    if ft not in rrf_scores:
                        rrf_scores[ft] = 0.0
                        rrf_order.append(ft)
                    rrf_scores[ft] += 1.0 / (_RRF_K + rank)

            fused = sorted(rrf_order, key=lambda f: rrf_scores[f], reverse=True)[:_LORE_TOP_K]

            seen: set[str] = set(fused)
            lore_facts: list[str] = list(fused)

            # Append unranked facts (failed to embed at write time)
            for row in unranked_data:
                ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
                if ft and ft not in seen:
                    seen.add(ft)
                    lore_facts.append(ft)

            # Merge pinned facts first, then ranked — dedup preserving order
            merged: list[str] = []
            seen_lore: set[str] = set()
            for f in pinned_facts + lore_facts:
                if f not in seen_lore:
                    seen_lore.add(f)
                    merged.append(f)

            # --- FlashRank Cross-Encoder Reranker (CPU, offloaded via asyncio.to_thread) ---
            if merged and current_text.strip() and len(merged) > _LORE_TOP_K:
                try:
                    passages_for_rerank = [
                        {"text": f, "meta": {"original": f}} for f in merged
                    ]
                    reranked = await rerank_passages(
                        query=current_text.strip(),
                        passages=passages_for_rerank,
                        top_k=_LORE_TOP_K,
                    )
                    merged = [p["text"] for p in reranked if p.get("text")]
                    logger.info(
                        "cross_encoder_rerank",
                        before=len(passages_for_rerank),
                        after=len(merged),
                        top_k=_LORE_TOP_K,
                    )
                except Exception:
                    logger.warning("reranker_failed", exc_info=True)

            # --- MMR diversity ---
            if len(merged) > 2:
                diversified = [merged[0]]
                all_selected_word_sets = [set(merged[0].lower().split())]
                dropped = 0
                for fact in merged[1:]:
                    current_words = set(fact.lower().split())
                    max_overlap = 0.0
                    for selected_words in all_selected_word_sets:
                        union = len(selected_words | current_words)
                        overlap = len(selected_words & current_words) / max(union, 1)
                        max_overlap = max(max_overlap, overlap)
                    if max_overlap < 0.5:
                        diversified.append(fact)
                        all_selected_word_sets.append(current_words)
                    else:
                        dropped += 1
                if dropped:
                    logger.debug(
                        "mmr_dropped_facts",
                        count=dropped,
                        before=len(merged),
                        after=len(diversified),
                    )
                merged = diversified

            return "\n".join(merged)

        except Exception:
            logger.warning("core_lore_fetch_failed", exc_info=True)
            return ""

    async def _fetch_past_memories() -> str:
        """Retrieve query-aware snippet context from interactions."""
        try:
            _PM_RECENCY_LAMBDA = 0.1
            _PM_RECENCY_HALFLIFE_S = 3 * 86400  # 3 days

            rows = await db.execute(
                text("""
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
                    ORDER BY (
                        (i.embedding <=> :query_embedding)
                        - :lam * EXP(- EXTRACT(EPOCH FROM (now() - i.created_at)) / :hl)
                    ) ASC
                    LIMIT 10
                """),
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "query_embedding": emb_str,
                    "lam": _PM_RECENCY_LAMBDA,
                    "hl": _PM_RECENCY_HALFLIFE_S,
                },
            )

            results = rows.mappings().all()
            if not results:
                return ""

            distances = [float(r["cosine_distance"]) for r in results]
            adaptive_threshold = calculate_adaptive_threshold(
                distances,
                percentile=0.3,
                min_threshold=0.15,
                max_threshold=0.30,
            )

            filtered_results = [
                r for r in results if float(r["cosine_distance"]) < adaptive_threshold
            ][:3]

            past_mem_lines: list[str] = []
            for idx, r in enumerate(filtered_results, start=1):
                their_last_message = str(r.get("their_last_message") or "")
                user_organic_text = str(r.get("user_organic_text") or "")
                key_detail = str(r.get("key_detail") or "")

                snippet_parts: list[str] = []
                if their_last_message:
                    snippet_parts.append(f"her_last_message: {their_last_message}")
                if user_organic_text:
                    snippet_parts.append(f"your_organic_text: {user_organic_text}")
                if key_detail:
                    snippet_parts.append(f"key_detail: {key_detail}")

                past_mem_lines.append(f"{idx}. " + " | ".join(snippet_parts))

            return "\n".join(past_mem_lines)

        except Exception:
            logger.warning("past_memories_fetch_failed", exc_info=True)
            return ""

    # ── Fire both streams concurrently (FIX 1) ──
    core_lore, past_memories = await asyncio.gather(
        _fetch_core_lore(),
        _fetch_past_memories(),
    )

    # Merge contexts with deduplication and token budgeting
    merged_context = merge_contexts(
        core_lore=core_lore,
        past_memories=past_memories,
        max_lore_tokens=500,
        max_past_tokens=200,
    )

    return {
        "person_name": person_name,
        "core_lore": core_lore,
        "past_memories": past_memories,
        "merged_context": merged_context,
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

        # Improvement #2: tighter dedup — exact-match check first (free),
        # then semantic similarity at 0.20 (was 0.30) to catch near-duplicates
        # like "Lives in Bangalore" vs "Based in Bangalore" vs "From Bangalore".
        exact_row = await db.execute(
            text("""
                SELECT 1 FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                  AND lower(trim(fact_text)) = lower(trim(:fact_text))
                LIMIT 1
                """),
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "fact_text": fact_text,
            },
        )
        if exact_row.first():
            return  # exact duplicate — skip silently

        # Find existing active facts within tighter semantic neighbourhood.
        similar_rows = await db.execute(
            text("""
                SELECT id, fact_text,
                       (embedding <=> :emb) AS distance
                FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                  AND embedding IS NOT NULL
                  AND (embedding <=> :emb) < 0.20
                ORDER BY distance ASC
                LIMIT 5
                """),
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "emb": embedding_str,
            },
        )
        similar = similar_rows.mappings().all()

        skip_insert = False
        for row in similar:
            distance = float(row["distance"])
            # Very high similarity — likely a restatement of an existing fact; skip.
            if distance < 0.10:
                skip_insert = True

        # NLI-based contradiction supersession is DISABLED on purpose. The model
        # (cross-encoder/nli-deberta-v3-small) confidently mislabels COMPATIBLE facts
        # as contradictions — measured ~0.99-1.00 "contradiction" on "From Surat" vs
        # "Lives in Sachin" and "has a dog" vs "has a cat" — so it deleted TRUE facts
        # on essentially every multi-fact profile. NLI "contradiction" (premise
        # doesn't entail hypothesis) != our "this fact REPLACES that one". Correct
        # supersession needs attribute-scoping (only single-valued slots like
        # relationship-status / current-city). The NLI model was removed entirely;
        # this is now ADD-only memory + hybrid (lexical+vector) retrieval + recency
        # ranking — the newest fact floats to the top, stale facts simply linger
        # (rare, low-harm) rather than risk destroying true facts.

        if not skip_insert:
            # Improvement #6: Rate importance and categorize fact at write time
            try:
                importance_score, fact_category = await rate_fact_importance(
                    db, fact_text
                )
            except Exception:
                importance_score, fact_category = None, None

            await db.execute(
                text("""
                    INSERT INTO conversation_memories
                        (id, user_id, conversation_id, fact_text, embedding,
                         importance_score, fact_category, created_at)
                    VALUES
                        (:id, :user_id, :conversation_id, :fact_text, :embedding,
                         :importance_score, :fact_category, now())
                    """),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "fact_text": fact_text,
                    "embedding": embedding_str,
                    "importance_score": importance_score,
                    "fact_category": fact_category,
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
            text("""
                SELECT lore
                FROM conversations
                WHERE id = :conversation_id
                  AND user_id = :user_id
                  AND is_active = true
                """),
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
            text("""
                UPDATE conversations
                SET lore = :new_lore
                WHERE id = :conversation_id
                  AND user_id = :user_id
                """),
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
        return {
            "updated": True,
            "removed_lines": removed,
            "new_lore_chars": len(new_lore),
        }
    except Exception as e:
        # No hard-fail path: some deployments may not have `lore` column yet.
        logger.warning(
            "lore_memory_scrub_skipped",
            user_id=user_id,
            conversation_id=conversation_id,
            error=str(e),
        )
        return {"updated": False, "removed_lines": 0, "new_lore_chars": 0}
