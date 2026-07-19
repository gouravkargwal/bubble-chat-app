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
    build_tier1_raw_exchanges,
    build_tier2_narrative_summary,
    extract_graph_triples,
    generate_query_variants,
    generate_sparse_lexical_extensions,
    mmr_rerank,
    rate_fact_importance,
)

logger = structlog.get_logger(__name__)


async def get_match_context(
    db: AsyncSession,
    user_id: str,
    conversation_id: str,
    current_text: str,
    precomputed_queries: list[str] | None = None,
) -> dict[str, str]:
    """
    Librarian service: retrieve historical context for a match.

    Returns:
      - person_name
      - core_lore: query-aware top-K relevant facts from conversation_memories
        (falls back to a flat chronological load when no query is available)
      - tier_1_raw_exchanges: FIFO sliding window of last N raw message exchanges
      - tier_2_summary: compressed narrative of the recent conversation arc
    """

    empty = {
        "person_name": "",
        "core_lore": "",
        "tier_1_raw_exchanges": "",
        "tier_2_summary": "",
    }
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

    # 2) Compute query embeddings -- Multi-query retrieval
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

            # Generate query variants for multi-query retrieval.
            # Prefer Vision-generated queries (zero-latency, context-aware)
            # over local Python string manipulation.
            if precomputed_queries:
                query_variants = [q.strip() for q in precomputed_queries if q.strip()]
            else:
                query_variants = [
                    qv.strip()
                    for qv in generate_query_variants(
                        current_text=current_text.strip(),
                        person_name=person_name,
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

            # Keep all embeddings separate for multi-vector retrieval.
            # Each variant's embedding is used independently in the CTE,
            # avoiding the semantic dilution caused by averaging diverse vectors.
            if all_query_embeddings:
                query_embedding = all_query_embeddings[0]  # primary for MMR
                emb_str = all_query_emb_strs[0]  # primary for MMR
            else:
                query_embedding = None
                emb_str = None
        except Exception:
            query_embedding = None
            emb_str = None

    # -- If no embedding, fall back to chronological fact load and return early --
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
        # Even in no-embedding path, build Tier 1 + Tier 2 from recent interactions.
        tier_1 = ""
        tier_2 = ""
        try:
            recent_rows = await db.execute(
                text("""
                    SELECT transcript_json, their_last_message, direction,
                           copied_index, reply_0, reply_1, reply_2, reply_3,
                           key_detail, created_at
                    FROM interactions
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                    ORDER BY created_at DESC
                    LIMIT 5
                """),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            recent = list(reversed([dict(r) for r in recent_rows.mappings().all()]))
            tier_1 = build_tier1_raw_exchanges(recent)
            tier_2 = build_tier2_narrative_summary(recent)
        except Exception:
            pass

        return {
            "person_name": person_name,
            "core_lore": core_lore,
            "tier_1_raw_exchanges": tier_1,
            "tier_2_summary": tier_2,
        }

    # -- Constants shared by both retrieval streams --
    _LORE_TOP_K = 8
    _RRF_K = 60
    _RERANK_POOL = 150
    _LORE_RECENCY_LAMBDA = 0.03
    _LORE_RECENCY_HALFLIFE_S = 14 * 86400  # 14 days

    # --- Combined CTE query: fires vector + lexical + unranked in ONE
    #     round-trip, then runs graph traversal concurrently via gather. ---

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

            # --- Multi-vector CTE: one vector sub-query per variant ---
            vec_emb_strs = (
                all_query_emb_strs
                if all_query_emb_strs
                else ([emb_str] if emb_str else [])
            )

            # Build N vector CTEs dynamically
            vec_cte_parts: list[str] = []
            vec_select_parts: list[str] = []
            sql_params: dict[str, Any] = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "q": current_text,
                "pool": _RERANK_POOL,
                "lam": _LORE_RECENCY_LAMBDA,
                "hl": _LORE_RECENCY_HALFLIFE_S,
                "importance_boost": 0.02,
            }

            for idx, v_emb in enumerate(vec_emb_strs):
                cte_name = f"vector_{idx}"
                emb_param = f"emb_{idx}"
                sql_params[emb_param] = v_emb
                vec_cte_parts.append(f"""
                {cte_name} AS (
                    SELECT fact_text, importance_score,
                           ROW_NUMBER() OVER (ORDER BY (
                               (embedding <=> :{emb_param})
                               - :lam * EXP(- EXTRACT(EPOCH FROM (now() - created_at)) / :hl)
                               - COALESCE(:importance_boost * (importance_score - 3), 0)
                           ) ASC) AS rank
                    FROM conversation_memories
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                      AND superseded_at IS NULL
                      AND embedding IS NOT NULL
                    ORDER BY (
                        (embedding <=> :{emb_param})
                        - :lam * EXP(- EXTRACT(EPOCH FROM (now() - created_at)) / :hl)
                        - COALESCE(:importance_boost * (importance_score - 3), 0)
                    ) ASC
                    LIMIT :pool
                )""")
                vec_select_parts.append(
                    f"SELECT 'vector' AS source, fact_text, importance_score, rank FROM {cte_name}"
                )

            if not vec_cte_parts:
                vec_cte_parts = []
                vec_select_parts = [
                    "SELECT NULL::text AS source, NULL::text AS fact_text, NULL::int AS importance_score, NULL::int AS rank WHERE false"
                ]

            # Assemble the full SQL string, then wrap in text()
            lexical_cte = (
                "lexical_results AS (\n"
                "    SELECT fact_text,\n"
                "           ROW_NUMBER() OVER (ORDER BY ts_rank(\n"
                "               to_tsvector('simple', fact_text || ' ' || COALESCE(lexical_expansion, '')),\n"
                "               websearch_to_tsquery('simple', :q)\n"
                "           ) DESC) AS rank\n"
                "    FROM conversation_memories\n"
                "    WHERE user_id = :user_id\n"
                "      AND conversation_id = :conversation_id\n"
                "      AND superseded_at IS NULL\n"
                "      AND embedding IS NOT NULL\n"
                "      AND to_tsvector('simple', fact_text || ' ' || COALESCE(lexical_expansion, ''))\n"
                "          @@ websearch_to_tsquery('simple', :q)\n"
                "    ORDER BY ts_rank(\n"
                "        to_tsvector('simple', fact_text || ' ' || COALESCE(lexical_expansion, '')),\n"
                "        websearch_to_tsquery('simple', :q)\n"
                "    ) DESC\n"
                "    LIMIT :pool\n"
                "),\n"
            )
            unranked_cte = (
                "unranked_results AS (\n"
                "    SELECT fact_text, 0 AS rank\n"
                "    FROM conversation_memories\n"
                "    WHERE user_id = :user_id\n"
                "      AND conversation_id = :conversation_id\n"
                "      AND superseded_at IS NULL\n"
                "      AND embedding IS NULL\n"
                "    ORDER BY created_at ASC\n"
                "    LIMIT 5\n"
                ")\n"
            )
            vec_unions = "\nUNION ALL\n".join(vec_select_parts)
            if vec_cte_parts:
                sql_str = (
                    "WITH\n"
                    + ",\n".join(vec_cte_parts)
                    + ",\n"
                    + lexical_cte
                    + unranked_cte
                    + vec_unions
                    + "\n"
                    + "UNION ALL\nSELECT 'lexical' AS source, fact_text, NULL::int AS importance_score, rank FROM lexical_results\n"
                    + "UNION ALL\nSELECT 'unranked' AS source, fact_text, NULL::int AS importance_score, rank FROM unranked_results"
                )
            else:
                sql_str = (
                    "WITH\n"
                    + lexical_cte
                    + unranked_cte
                    + vec_unions
                    + "\n"
                    + "UNION ALL\nSELECT 'lexical' AS source, fact_text, NULL::int AS importance_score, rank FROM lexical_results\n"
                    + "UNION ALL\nSELECT 'unranked' AS source, fact_text, NULL::int AS importance_score, rank FROM unranked_results"
                )
            combined_sql = text(sql_str)

            combined_rows = await db.execute(combined_sql, sql_params)
            combined = combined_rows.mappings().all()

            vec_data = [r for r in combined if r["source"] == "vector"]
            lex_data = [r for r in combined if r["source"] == "lexical"]
            unranked_data = [r for r in combined if r["source"] == "unranked"]

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

            fused = sorted(rrf_order, key=lambda f: rrf_scores[f], reverse=True)[
                :_LORE_TOP_K
            ]

            seen: set[str] = set(fused)
            lore_facts: list[str] = list(fused)

            for row in unranked_data:
                ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
                if ft and ft not in seen:
                    seen.add(ft)
                    lore_facts.append(ft)

            merged: list[str] = []
            seen_lore: set[str] = set()
            for f in pinned_facts + lore_facts:
                if f not in seen_lore:
                    seen_lore.add(f)
                    merged.append(f)

            # --- FlashRank Cross-Encoder Reranker ---
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

            # --- Vector MMR diversity ---
            if len(merged) > 2:
                try:
                    diversified = await mmr_rerank(
                        db=db,
                        facts=merged,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        query_embedding=query_embedding,
                        lambda_param=0.7,
                    )
                    if diversified != merged:
                        logger.debug(
                            "mmr_rerank_applied",
                            before=len(merged),
                            after=len(diversified),
                        )
                    merged = diversified
                except Exception:
                    logger.warning("mmr_rerank_failed", exc_info=True)

            return "\n".join(merged)

        except Exception:
            logger.warning("core_lore_fetch_failed", exc_info=True)
            return ""

    async def _fetch_tier1_tier2() -> tuple[str, str]:
        """Tier 1 (raw FIFO) + Tier 2 (narrative summary) from recent interactions."""
        try:
            rows = await db.execute(
                text("""
                    SELECT transcript_json, their_last_message, direction,
                           copied_index, reply_0, reply_1, reply_2, reply_3,
                           key_detail, created_at
                    FROM interactions
                    WHERE user_id = :user_id
                      AND conversation_id = :conversation_id
                    ORDER BY created_at DESC
                    LIMIT 5
                """),
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            recent = list(reversed([dict(r) for r in rows.mappings().all()]))
            return (
                build_tier1_raw_exchanges(recent),
                build_tier2_narrative_summary(recent),
            )
        except Exception:
            logger.warning("tier1_tier2_fetch_failed", exc_info=True)
            return ("", "")

    # -- Fixed Graph Context Engine using path tracking arrays with ANSI CAST parsing --
    async def _fetch_graph_context() -> str:
        """Fetch Graph RAG subnetwork context via recursive CTE traversal."""
        try:
            query_words = [
                w.lower().strip() for w in current_text.split() if len(w.strip()) > 2
            ]
            if not query_words:
                return ""

            seeds = list(query_words)
            if person_name and person_name.lower() not in seeds:
                seeds.append(person_name.lower())

            graph_sql = text("""
                WITH RECURSIVE graph_traversal(
                    source_id, target_id, rel_type, depth, path
                ) AS (
                    -- Anchor: fuzzy-match entity nodes via pg_trgm trigram similarity
                    SELECT e.source_entity_id, e.target_entity_id,
                        e.relationship_type, 1 AS depth,
                        -- FIXED: Cast the initial array explicitly to an unconstrained varchar array
                        CAST(ARRAY[e.source_entity_id, e.target_entity_id] AS varchar[]) AS path
                    FROM conversation_memory_edges e
                    JOIN conversation_memory_entities ent
                        ON e.source_entity_id = ent.id
                    WHERE e.user_id = :user_id
                    AND e.conversation_id = :conversation_id
                    AND EXISTS (
                        -- Using ANSI CAST to avoid SQLAlchemy named parameter parsing conflicts
                        SELECT 1 FROM unnest(CAST(:seeds AS text[])) AS seed
                        WHERE similarity(ent.entity_name, seed) > 0.2
                    )

                    UNION

                    -- Recursive: discover connected sub-nodes (max 2 hops)
                    SELECT e.source_entity_id, e.target_entity_id,
                        e.relationship_type, gt.depth + 1,
                        gt.path || e.target_entity_id AS path
                    FROM conversation_memory_edges e
                    JOIN graph_traversal gt
                        ON e.source_entity_id = gt.target_id
                    WHERE gt.depth < 2
                    AND NOT (e.target_entity_id = ANY(gt.path))
                )
                SELECT DISTINCT
                    ent1.entity_name AS source_node,
                    gt.rel_type AS relationship,
                    ent2.entity_name AS target_node
                FROM graph_traversal gt
                JOIN conversation_memory_entities ent1
                    ON gt.source_id = ent1.id
                JOIN conversation_memory_entities ent2
                    ON gt.target_id = ent2.id
                LIMIT 15
            """)
            rows = await db.execute(
                graph_sql,
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "seeds": seeds,
                },
            )
            triples = rows.all()
            if not triples:
                return ""

            context_lines = [f"- ({r[0]}) -[{r[1]}]-> ({r[2]})" for r in triples]
            return "=== Network Knowledge Graph Context ===\n" + "\n".join(
                context_lines
            )
        except Exception as e:
            logger.warning("graph_context_traversal_failed", error=str(e))
            return ""

    core_lore, (tier_1_raw, tier_2_summary), graph_context = await asyncio.gather(
        _fetch_core_lore(),
        _fetch_tier1_tier2(),
        _fetch_graph_context(),
    )

    if graph_context:
        core_lore = f"{core_lore}\n\n{graph_context}" if core_lore else graph_context

    return {
        "person_name": person_name,
        "core_lore": core_lore,
        "tier_1_raw_exchanges": tier_1_raw,
        "tier_2_summary": tier_2_summary,
    }


async def upsert_conversation_memory(
    db: AsyncSession,
    *,
    user_id: str,
    conversation_id: str,
    fact_text: str,
    fact_source: str = "explicit",
) -> None:
    """Persist a single fact into conversation_memories.

    1. Embed the new fact.
    2. Exact-match dedup check (free).
    3. Semantic similarity check (< 0.20 cosine distance) -- skip if near-duplicate.
    4. Concurrently: importance scoring, lexical expansion, graph extraction.
    5. Insert fact + graph entities/edges.

    Args:
        fact_source: 'explicit' (user stated it) or 'inferred' (LLM guessed).
            Used by the context formatter to label facts [CONFIRMED] / [INFERRED].

    ADD-only memory -- no supersession. The newest fact floats to the top
    via recency-weighted retrieval. Never raises.
    """
    fact_text = (fact_text or "").strip()
    if not fact_text:
        return

    try:
        new_embedding = await embed_text(fact_text)
        if not new_embedding:
            return

        embedding_str = f"[{','.join(str(x) for x in new_embedding)}]"

        # Improvement #2: tighter dedup -- exact-match check first (free),
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
            return  # exact duplicate -- skip silently

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
            # Very high similarity -- likely a restatement of an existing fact; skip.
            if distance < 0.10:
                skip_insert = True

        # NLI-based contradiction supersession is DISABLED on purpose. The model
        # (cross-encoder/nli-deberta-v3-small) confidently mislabels COMPATIBLE facts
        # as contradictions -- measured ~0.99-1.00 "contradiction" on "From Surat" vs
        # "Lives in Sachin" and "has a dog" vs "has a cat" -- so it deleted TRUE facts
        # on essentially every multi-fact profile. NLI "contradiction" (premise
        # doesn't entail hypothesis) != our "this fact REPLACES that one". Correct
        # supersession needs attribute-scoping (only single-valued slots like
        # relationship-status / current-city). The NLI model was removed entirely;
        # this is now ADD-only memory + hybrid (lexical+vector) retrieval + recency
        # ranking -- the newest fact floats to the top, stale facts simply linger
        # (rare, low-harm) rather than risk destroying true facts.

        if not skip_insert:
            # Run importance scoring, lexical expansion, and graph extraction
            # concurrently to minimize write-path latency.
            importance_task = rate_fact_importance(fact_text)
            expansion_task = generate_sparse_lexical_extensions(fact_text)
            graph_task = extract_graph_triples(fact_text)

            (importance_score, fact_category), lexical_expansion, graph_data = (
                await asyncio.gather(
                    importance_task,
                    expansion_task,
                    graph_task,
                    return_exceptions=True,
                )
            )
            # Unpack exceptions gracefully
            if isinstance(importance_score, Exception):
                importance_score, fact_category = None, None
            if isinstance(lexical_expansion, Exception):
                lexical_expansion = ""
            if isinstance(graph_data, Exception):
                from app.services.rag_improvements import KnowledgeGraphTriples

                graph_data = KnowledgeGraphTriples()

            await db.execute(
                text("""
                    INSERT INTO conversation_memories
                        (id, user_id, conversation_id, fact_text, embedding,
                         importance_score, fact_category, lexical_expansion,
                         fact_source, created_at)
                    VALUES
                        (:id, :user_id, :conversation_id, :fact_text, :embedding,
                         :importance_score, :fact_category, :lexical_expansion,
                         :fact_source, now())
                    """),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "fact_text": fact_text,
                    "embedding": embedding_str,
                    "importance_score": importance_score,
                    "fact_category": fact_category,
                    "lexical_expansion": lexical_expansion,
                    "fact_source": fact_source,
                },
            )

            # --- Graph RAG ingestion: extract entities + edges ---
            # Use a savepoint to isolate graph ingestion from the outer transaction.
            # Without this, any DB error here (e.g. NULL FK violation) poisons the
            # asyncpg connection, causing *every* subsequent db.execute() on this
            # session to raise InFailedSQLTransactionError.
            await db.execute(text("SAVEPOINT graph_sp"))
            try:
                if graph_data.entities:
                    # 1. Insert entity nodes (upsert via ON CONFLICT)
                    inserted_entity_names: set[str] = set()
                    for entity in graph_data.entities:
                        entity_name = entity.name.strip().lower()
                        entity_type = entity.type.strip().lower()
                        if not entity_name or not entity_type:
                            continue
                        await db.execute(
                            text("""
                                INSERT INTO conversation_memory_entities
                                    (id, user_id, conversation_id, entity_name,
                                     entity_type, created_at)
                                VALUES
                                    (:id, :user_id, :conversation_id, :name,
                                     :type, now())
                                ON CONFLICT (conversation_id, entity_name)
                                DO UPDATE SET entity_type = EXCLUDED.entity_type
                            """),
                            {
                                "id": str(uuid.uuid4()),
                                "user_id": user_id,
                                "conversation_id": conversation_id,
                                "name": entity_name,
                                "type": entity_type,
                            },
                        )
                        inserted_entity_names.add(entity_name)

                    # 2. Insert directed edges — only when both endpoints exist
                    for rel in graph_data.relationships:
                        src = rel.source.strip().lower()
                        tgt = rel.target.strip().lower()
                        rel_type = rel.relationship.strip().upper()
                        if not src or not tgt or not rel_type:
                            continue
                        # Skip edges referencing entities not in the just-inserted set.
                        # The subquery below returns NULL for unknown names, violating
                        # source_entity_id/target_entity_id NOT NULL — poisoning the
                        # entire transaction.
                        if (
                            src not in inserted_entity_names
                            or tgt not in inserted_entity_names
                        ):
                            logger.warning(
                                "graph_edge_skipped_unknown_entity",
                                src=src,
                                tgt=tgt,
                                rel=rel_type,
                            )
                            continue
                        await db.execute(
                            text("""
                            INSERT INTO conversation_memory_edges
                                (id, user_id, conversation_id,
                                source_entity_id, target_entity_id,
                                relationship_type, weight, created_at)
                            VALUES (
                                :id,
                                :user_id,
                                CAST(:conversation_id AS VARCHAR),
                                (SELECT id FROM conversation_memory_entities
                                WHERE conversation_id = CAST(:conversation_id AS VARCHAR)
                                AND entity_name = :src LIMIT 1),
                                (SELECT id FROM conversation_memory_entities
                                WHERE conversation_id = CAST(:conversation_id AS VARCHAR)
                                AND entity_name = :tgt LIMIT 1),
                                :rel,
                                1.0,
                                now()
                            )
                            ON CONFLICT DO NOTHING
                        """),
                            {
                                "id": str(uuid.uuid4()),
                                "user_id": user_id,
                                "conversation_id": conversation_id,
                                "src": src,
                                "tgt": tgt,
                                "rel": rel_type,
                            },
                        )
                await db.execute(text("RELEASE SAVEPOINT graph_sp"))
            except Exception as graph_err:
                await db.execute(text("ROLLBACK TO SAVEPOINT graph_sp"))
                logger.warning("graph_db_ingestion_failed", error=str(graph_err))

        # NB: No db.commit() here -- transaction boundaries are managed by the
        # outer LangGraph workflow or FastAPI router request context.

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
        # No hard-fail path: some deployments may not have lore column yet.
        logger.warning(
            "lore_memory_scrub_skipped",
            user_id=user_id,
            conversation_id=conversation_id,
            error=str(e),
        )
        return {"updated": False, "removed_lines": 0, "new_lore_chars": 0}
