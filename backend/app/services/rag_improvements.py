"""
RAG improvement utilities: token budgeting, deduplication, reranking, feedback tracking,
multi-query retrieval, and importance scoring.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Token estimation (rough but fast: ~4 chars per token for English/Hinglish)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string."""
    if not text:
        return 0
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def normalize_for_dedup(text: str) -> str:
    """Normalize text for deduplication comparison."""
    if not text:
        return ""
    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def deduplicate_facts(
    facts: list[str], existing_normalized: set[str] | None = None
) -> tuple[list[str], set[str]]:
    """Remove duplicate facts, preserving order."""
    seen = existing_normalized or set()
    unique_facts = []
    for fact in facts:
        norm = normalize_for_dedup(fact)
        if norm and norm not in seen:
            seen.add(norm)
            unique_facts.append(fact)
    return unique_facts, seen


# ---------------------------------------------------------------------------
# Token-budget-aware fact selection
# ---------------------------------------------------------------------------


def select_facts_within_budget(
    facts: list[str],
    max_tokens: int = 500,
    min_facts: int = 3,
) -> list[str]:
    """Select facts that fit within a token budget, prioritizing by position."""
    if not facts:
        return []
    selected = []
    current_tokens = 0
    for fact in facts:
        fact_tokens = estimate_tokens(fact)
        if len(selected) < min_facts:
            selected.append(fact)
            current_tokens += fact_tokens
            continue
        if current_tokens + fact_tokens > max_tokens:
            break
        selected.append(fact)
        current_tokens += fact_tokens
    return selected


# ---------------------------------------------------------------------------
# Maximal Marginal Relevance (MMR) for diversity
# ---------------------------------------------------------------------------


async def mmr_rerank(
    db: AsyncSession,
    facts: list[str],
    conversation_id: str,
    user_id: str,
    query_embedding: list[float] | None = None,
    lambda_param: float = 0.7,
) -> list[str]:
    """Rerank facts using Maximal Marginal Relevance for diversity.

    Uses pre-computed embeddings from the DB to balance relevance and diversity.
    lambda_param controls trade-off: 1.0 = pure relevance, 0.0 = pure diversity.

    This is O(n^2) in fact count but n is small (< 20 facts).
    """
    if len(facts) <= 2:
        return facts

    if not query_embedding:
        logger.warning("mmr_rerank_skipped", reason="no_query_embedding")
        return facts

    # Fetch pre-computed embeddings for all facts from DB
    try:
        emb_rows = await db.execute(
            text("""
                SELECT fact_text, embedding
                FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                  AND embedding IS NOT NULL
                  AND fact_text = ANY(:fact_texts)
            """),
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "fact_texts": facts,
            },
        )
        fact_embeddings: dict[str, list[float]] = {}
        for row in emb_rows.mappings().all():
            ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
            emb_str = str(row["embedding"]) if row["embedding"] else ""
            if ft and emb_str:
                try:
                    emb = [float(x) for x in emb_str.strip("[]").split(",")]
                    fact_embeddings[ft] = emb
                except (ValueError, TypeError):
                    pass

        if not fact_embeddings:
            return facts

        # Cosine similarity between two vectors
        def cosine_sim(a: list[float], b: list[float]) -> float:
            if not a or not b:
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        # Relevance scores: cosine similarity with query
        relevance: dict[str, float] = {}
        for fact in facts:
            emb = fact_embeddings.get(fact)
            if emb:
                relevance[fact] = cosine_sim(query_embedding, emb)
            else:
                relevance[fact] = 0.0

        # MMR selection: iteratively pick facts
        selected: list[str] = []
        remaining = list(facts)

        # First pick: highest relevance
        best = max(remaining, key=lambda f: relevance.get(f, 0.0))
        selected.append(best)
        remaining.remove(best)

        while remaining and len(selected) < 15:
            scores: dict[str, float] = {}
            for fact in remaining:
                rel = relevance.get(fact, 0.0)
                # Max similarity to any already-selected fact (for diversity)
                max_sim = max(
                    (
                        cosine_sim(
                            fact_embeddings.get(fact, []), fact_embeddings.get(sel, [])
                        )
                        for sel in selected
                        if fact in fact_embeddings and sel in fact_embeddings
                    ),
                    default=0.0,
                )
                # MMR = lambda * rel - (1 - lambda) * max_sim
                scores[fact] = lambda_param * rel - (1 - lambda_param) * max_sim

            best = max(remaining, key=lambda f: scores.get(f, 0.0))
            if scores.get(best, 0.0) < 0:
                break  # Remaining facts are all too similar
            selected.append(best)
            remaining.remove(best)

        logger.info(
            "mmr_rerank_complete",
            before=len(facts),
            after=len(selected),
            lambda_param=lambda_param,
        )
        return selected

    except Exception as e:
        logger.warning("mmr_rerank_failed", error=str(e), fact_count=len(facts))
        return facts  # Fallback: return original order


# ---------------------------------------------------------------------------
# Multi-query retrieval
# ---------------------------------------------------------------------------


def generate_query_variants(
    current_text: str,
    person_name: str = "",
    max_variants: int = 3,
) -> list[str]:
    """Generate multiple query variants for better recall.

    Returns up to `max_variants` query strings that capture different aspects
    of the user's input. These can be embedded separately and fused via RRF.
    """
    text = current_text.strip()
    if not text:
        return [""]

    variants: list[str] = []
    seen: set[str] = set()

    # Variant 0: Original query (always included)
    variants.append(text)
    seen.add(normalize_for_dedup(text))

    # Variant 1: Enriched with person name (helps disambiguate)
    if person_name and person_name.strip():
        enriched = f"{person_name}: {text}"
        norm = normalize_for_dedup(enriched)
        if norm not in seen and len(variants) < max_variants:
            variants.append(enriched)
            seen.add(norm)

    # Variant 2: Keywords only (strips stop words, focuses on content)
    words = text.split()
    if len(words) >= 3:
        # Take first 3 content words (skip common stop words)
        stop_words = {
            "what",
            "when",
            "where",
            "how",
            "are",
            "you",
            "your",
            "the",
            "a",
            "an",
            "is",
            "it",
            "to",
            "do",
            "did",
            "have",
        }
        content_words = [w for w in words if w.lower() not in stop_words][:3]
        if len(content_words) >= 2:
            kw_query = " ".join(content_words)
            norm = normalize_for_dedup(kw_query)
            if norm not in seen and len(variants) < max_variants:
                variants.append(kw_query)
                seen.add(norm)

    return variants


# ---------------------------------------------------------------------------
# Retrieval feedback tracking
# ---------------------------------------------------------------------------


async def log_retrieval_feedback(
    db: AsyncSession,
    *,
    interaction_id: str,
    fact_text: str,
    was_used: bool,
    user_rating: int | None = None,
) -> None:
    """Log whether a retrieved fact was actually used in generation."""
    try:
        check_sql = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'retrieval_feedback'
            )
        """)
        result = await db.execute(check_sql)
        table_exists = result.scalar()
        if not table_exists:
            logger.debug("retrieval_feedback_table_missing")
            return

        import uuid

        await db.execute(
            text("""
                INSERT INTO retrieval_feedback
                    (id, interaction_id, fact_text, was_used, user_rating, created_at)
                VALUES
                    (:id, :interaction_id, :fact_text, :was_used, :user_rating, now())
            """),
            {
                "id": str(uuid.uuid4()),
                "interaction_id": interaction_id,
                "fact_text": fact_text[:500],
                "was_used": was_used,
                "user_rating": user_rating,
            },
        )
        await db.commit()
    except Exception as e:
        logger.warning("retrieval_feedback_log_failed", error=str(e))


# ---------------------------------------------------------------------------
# Adaptive threshold calculation
# ---------------------------------------------------------------------------


def calculate_adaptive_threshold(
    distances: list[float],
    percentile: float = 0.2,
    min_threshold: float = 0.15,
    max_threshold: float = 0.35,
) -> float:
    """Calculate adaptive cosine distance threshold based on result distribution."""
    if not distances:
        return min_threshold
    sorted_distances = sorted(distances)
    idx = int(len(sorted_distances) * percentile)
    idx = min(idx, len(sorted_distances) - 1)
    threshold = sorted_distances[idx]
    threshold = max(min_threshold, min(max_threshold, threshold))
    logger.info(
        "adaptive_threshold_calculated",
        threshold=threshold,
        percentile=percentile,
        result_count=len(distances),
    )
    return threshold


# ---------------------------------------------------------------------------
# Context merging with deduplication
# ---------------------------------------------------------------------------


def merge_contexts(
    core_lore: str,
    past_memories: str,
    max_lore_tokens: int = 500,
    max_past_tokens: int = 200,
) -> str:
    """Merge core_lore and past_memories with deduplication and token budgeting."""
    lore_lines = (
        [line.strip() for line in core_lore.split("\n") if line.strip()]
        if core_lore
        else []
    )
    past_lines = (
        [line.strip() for line in past_memories.split("\n") if line.strip()]
        if past_memories
        else []
    )

    seen_normalized = set()
    unique_lore = []
    for line in lore_lines:
        norm = normalize_for_dedup(line)
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            unique_lore.append(line)

    unique_past = []
    for line in past_lines:
        norm = normalize_for_dedup(line)
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            unique_past.append(line)

    budgeted_lore = select_facts_within_budget(unique_lore, max_tokens=max_lore_tokens)
    budgeted_past = select_facts_within_budget(
        unique_past, max_tokens=max_past_tokens, min_facts=1
    )

    parts = []
    if budgeted_lore:
        parts.append("=== Core Facts ===")
        parts.extend(budgeted_lore)
    if budgeted_past:
        if parts:
            parts.append("")
        parts.append("=== Recent Context ===")
        parts.extend(budgeted_past)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Importance scoring for facts
# ---------------------------------------------------------------------------


async def rate_fact_importance(
    db: AsyncSession,
    fact_text: str,
) -> tuple[int, str]:
    """Rate the importance of a fact using a rule-based heuristic.

    Returns (importance_score 1-5, category).
    Requires no API call - pure heuristic matching.
    """
    text_lower = fact_text.lower()

    # Critical identity facts (5)
    identity_5_keywords = [
        "married",
        "divorced",
        "widowed",
        "single",
        "muslim",
        "hindu",
        "sikh",
        "christian",
        "jain",
        "buddhist",
        "lives in",
        "hometown",
        "from ",
        "based in",
        "works as",
        "job",
        "profession",
    ]
    if any(kw in text_lower for kw in identity_5_keywords):
        return 5, "identity"

    # Important preferences / life details (4)
    preference_4_keywords = [
        "has kids",
        "no kids",
        "vegetarian",
        "vegan",
        "non-vegetarian",
        "engineer",
        "doctor",
        "lawyer",
        "phd",
        "masters",
        "degree",
        "age",
        "born",
        "birthday",
    ]
    if any(kw in text_lower for kw in preference_4_keywords):
        return 4, "preference"

    # Explicit opinions / relationship goals (3)
    opinion_3_keywords = [
        "looking for",
        "want",
        "interested in",
        "love",
        "hate",
        "like",
        "enjoys",
        "hobby",
        "passionate",
        "goal",
    ]
    if any(kw in text_lower for kw in opinion_3_keywords):
        return 3, "opinion"

    # General facts (2)
    if len(fact_text) > 30:  # Substantial text
        return 2, "factual"

    # Minor details (1)
    return 1, "preference"
