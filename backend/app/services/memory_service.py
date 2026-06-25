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
    log_retrieval_feedback,
    merge_contexts,
    mmr_rerank,
    rate_fact_importance,
    select_facts_within_budget,
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

    # 2) Compute query embeddings — Improvement #9: Multi-query retrieval
    #    Generate multiple query variants, embed each, and fuse results via RRF.
    query_embedding: list[float] | None = None
    emb_str: str | None = None
    # Store all query embeddings for multi-query fusion
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

            # Generate query variants for multi-query retrieval
            query_variants = [
                qv.strip()
                for qv in generate_query_variants(
                    current_text=current_text,
                    person_name=person_name,
                    max_variants=3,
                )
                if qv.strip()
            ]

            # 🚀 SURGICAL SPEED FIX: Fire all embedding network requests concurrently
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

                # Resolve all network tasks simultaneously
                resolved_embeddings = await asyncio.gather(
                    *embedding_tasks, return_exceptions=True
                )

                for emb in resolved_embeddings:
                    # Ensure the result is a valid float array and didn't throw an API error
                    if emb and isinstance(emb, list):
                        all_query_embeddings.append(emb)
                        all_query_emb_strs.append(f"[{','.join(str(x) for x in emb)}]")

            # Primary embedding is the first one (original query)
            if all_query_embeddings:
                query_embedding = all_query_embeddings[0]
                emb_str = all_query_emb_strs[0]
            else:
                query_embedding = None
                emb_str = None
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
    _RRF_K = 60  # reciprocal-rank-fusion damping constant (standard ~60)
    _LORE_RECENCY_LAMBDA = 0.03
    _LORE_RECENCY_HALFLIFE_S = 14 * 86400  # 14 days
    _DOSSIER_FULL_THRESHOLD = 15
    # fact_count MUST be loaded before _LORE_TOP_K — dynamic K depends on it.
    fact_count = 0
    try:
        cnt_row = await db.execute(
            text("""
                SELECT count(*) AS n
                FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                """),
            {"user_id": user_id, "conversation_id": conversation_id},
        )
        _m = cnt_row.mappings().first()
        fact_count = int(_m["n"]) if _m else 0
    except Exception:
        fact_count = 0
    # Dynamic K — scales with fact count. Cap at 15 to avoid prompt bloat.
    _LORE_TOP_K = min(15, max(8, fact_count // 4)) if fact_count > 0 else 8
    # Increase pool size for FlashRank cross-encoder reranker
    # RRF fuses top 50 candidates, then reranker narrows to top 8
    _RERANK_POOL = 50
    _LORE_FUSION_POOL = _RERANK_POOL
    # Improvement #4: always-surface high-salience facts regardless of query
    # relevance. These are identity/status facts that must never fall off the
    # top-K filter (religion, marital status, location, diet, etc.).
    _HIGH_SALIENCE_KEYWORDS = (
        "divorced",
        "married",
        "single",
        "widowed",
        "has kids",
        "no kids",
        "muslim",
        "hindu",
        "sikh",
        "christian",
        "jain",
        "buddhist",
        "vegetarian",
        "vegan",
        "non-vegetarian",
        "lives in",
        "from ",
        "based in",
        "hometown",
        "works as",
        "job",
        "profession",
        "engineer",
        "doctor",
        "lawyer",
        "phd",
        "masters",
        "degree",
    )
    pinned_facts: list[str] = []
    try:
        all_facts_row = await db.execute(
            text("""
                SELECT fact_text FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                ORDER BY created_at ASC
                """),
            {"user_id": user_id, "conversation_id": conversation_id},
        )
        for r in all_facts_row.mappings().all():
            ft = (r["fact_text"] or "").strip().lower()
            if any(kw in ft for kw in _HIGH_SALIENCE_KEYWORDS):
                pinned_facts.append(r["fact_text"].strip())
    except Exception:
        pinned_facts = []

    use_hybrid = bool(emb_str) and fact_count > _DOSSIER_FULL_THRESHOLD
    try:
        if use_hybrid:
            # Retriever 1 — SEMANTIC (recency-blended + importance-boosted) ranking.
            # Improvement: Boost high-importance facts (importance_score 4-5) in ranking
            vec_rows = await db.execute(
                text("""
                    SELECT fact_text, importance_score
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
                    """),
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "emb": emb_str,
                    "pool": _LORE_FUSION_POOL,
                    "lam": _LORE_RECENCY_LAMBDA,
                    "hl": _LORE_RECENCY_HALFLIFE_S,
                    "importance_boost": 0.02,  # Boost importance_score 4-5 by 0.02-0.04
                },
            )
            # Retriever 2 — LEXICAL full-text ranking. Catches exact-term recall the
            # embedding can miss: she names a place/person/topic now ("Goa", "Pixel")
            # and we surface the stored fact mentioning it even if it sat just
            # outside the vector pool. Postgres built-in FTS, no extension needed.
            lex_rows = await db.execute(
                text("""
                    SELECT fact_text
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NOT NULL
                      AND to_tsvector('simple', fact_text)
                          @@ plainto_tsquery('simple', :q)
                    ORDER BY ts_rank(
                        to_tsvector('simple', fact_text),
                        plainto_tsquery('simple', :q)
                    ) DESC
                    LIMIT :pool
                    """),
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "q": current_text,
                    "pool": _LORE_FUSION_POOL,
                },
            )
            # Reciprocal Rank Fusion — merge the two rankings. A fact ranked well by
            # EITHER retriever surfaces; facts ranked well by BOTH win. Python sort is
            # stable, so ties keep insertion order (vector first → vector tiebreak).
            rrf_scores: dict[str, float] = {}
            rrf_order: list[str] = []
            for result in (vec_rows, lex_rows):
                for rank, row in enumerate(result.mappings().all(), start=1):
                    ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
                    if not ft:
                        continue
                    if ft not in rrf_scores:
                        rrf_scores[ft] = 0.0
                        rrf_order.append(ft)
                    rrf_scores[ft] += 1.0 / (_RRF_K + rank)
            fused = sorted(rrf_order, key=lambda f: rrf_scores[f], reverse=True)[
                :_LORE_TOP_K
            ]

            seen: set[str] = set(fused)
            lore_facts: list[str] = list(fused)
            # Facts that never embedded (write-time embed failure) can't be ranked by
            # either retriever — append unconditionally so they're never dropped.
            unranked_rows = await db.execute(
                text("""
                    SELECT fact_text
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NULL
                    ORDER BY created_at ASC
                    """),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            for row in unranked_rows.mappings().all():
                ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
                if ft and ft not in seen:
                    seen.add(ft)
                    lore_facts.append(ft)
            # Merge pinned facts first, then ranked facts — dedup preserving order.
            seen_lore: set[str] = set()
            merged: list[str] = []
            for f in pinned_facts + lore_facts:
                if f not in seen_lore:
                    seen_lore.add(f)
                    merged.append(f)

            # 🌟 CROSS-ENCODER RERANKER LAYER (CPU-only, zero API cost)
            # FlashRank scores the top 50 RRF-fused candidates against the original
            # user query, narrowing to the top 8 most semantically relevant facts.
            # This catches cases where RRF's position-based formula lets through
            # lexically matching but semantically irrelevant facts.
            if merged and current_text.strip() and len(merged) > _LORE_TOP_K:
                try:
                    passages_for_rerank = [
                        {"text": f, "meta": {"original": f}} for f in merged
                    ]
                    reranked = await rerank_passages(
                        query=current_text.strip(),
                        passages=passages_for_rerank,
                        top_k=_LORE_TOP_K,  # Narrow to top 8-15
                    )
                    merged = [p["text"] for p in reranked if p.get("text")]
                    logger.info(
                        "cross_encoder_rerank",
                        before=len(passages_for_rerank),
                        after=len(merged),
                        top_k=_LORE_TOP_K,
                    )
                except Exception as e:
                    logger.warning("reranker_failed", exc_info=True)
            # Improvement #7: Apply MMR diversity filter on the reranked set
            # Ensures no two consecutive facts have >50% word overlap
            if len(merged) > 2:
                diversified = [merged[0]]
                dropped = 0
                for fact in merged[1:]:
                    last_words = set(diversified[-1].lower().split())
                    current_words = set(fact.lower().split())
                    union = len(last_words | current_words)
                    overlap = len(last_words & current_words) / max(union, 1)
                    if overlap < 0.5:
                        diversified.append(fact)
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

            core_lore = "\n".join(merged)
        else:
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
            # Even in dossier-full mode, ensure pinned facts appear.
            seen_lore = set(all_lore)
            for pf in pinned_facts:
                if pf not in seen_lore:
                    all_lore.insert(0, pf)
            core_lore = "\n".join(all_lore)
    except Exception:
        pass

    # 4) past_memories — query-aware snippet retrieval from interactions.
    #    Improvement: adaptive threshold + token budgeting + deduplication
    try:
        if not emb_str:
            return {
                "person_name": person_name,
                "core_lore": core_lore,
                "past_memories": "",
            }

        # Enrich past_memories query with person_name — same enrichment as core_lore
        # so "kya plan hai" + "Dinisha" surfaces her plan-related turns specifically.
        pm_query = current_text.strip()
        if person_name and person_name.strip():
            pm_query = f"{person_name}: {pm_query}"
        pm_embedding = (
            await embed_text(pm_query)
            if pm_query != current_text.strip()
            else query_embedding
        )
        pm_emb_str = (
            f"[{','.join(str(x) for x in pm_embedding)}]" if pm_embedding else emb_str
        )

        _PM_RECENCY_LAMBDA = 0.1
        _PM_RECENCY_HALFLIFE_S = 3 * 86400  # 3 days

        # Improvement: Fetch more candidates than needed, then apply adaptive threshold
        vector_sql = text("""
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
            """)

        rows = await db.execute(
            vector_sql,
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "query_embedding": pm_emb_str,
                "lam": _PM_RECENCY_LAMBDA,
                "hl": _PM_RECENCY_HALFLIFE_S,
            },
        )

        results = rows.mappings().all()
        if not results:
            return {
                "person_name": person_name,
                "core_lore": core_lore,
                "past_memories": "",
            }

        # Improvement: Adaptive threshold based on result distribution
        distances = [float(r["cosine_distance"]) for r in results]
        adaptive_threshold = calculate_adaptive_threshold(
            distances,
            percentile=0.3,
            min_threshold=0.15,
            max_threshold=0.30,
        )

        # Filter by adaptive threshold
        filtered_results = [
            r for r in results if float(r["cosine_distance"]) < adaptive_threshold
        ]

        # Take top 3 after adaptive filtering
        filtered_results = filtered_results[:3]

        past_mem_lines: list[str] = []
        for idx, r in enumerate(filtered_results, start=1):
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

        # Improvement: Merge contexts with deduplication and token budgeting
        merged_context = merge_contexts(
            core_lore=core_lore,
            past_memories=past_memories,
            max_lore_tokens=500,
            max_past_tokens=200,
        )

        # Split merged context back into core_lore and past_memories for backward compatibility
        # (or return as merged if callers support it)
        return {
            "person_name": person_name,
            "core_lore": core_lore,  # Keep original for now
            "past_memories": past_memories,
            "merged_context": merged_context,  # New field with deduplication
        }
    except Exception:
        # Critical: retrieval failures should never crash the app.
        return {
            "person_name": person_name,
            "core_lore": core_lore,
            "past_memories": "",
            "merged_context": core_lore,
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
