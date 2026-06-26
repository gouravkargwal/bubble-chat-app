"""
RAG improvement utilities: token budgeting, deduplication, reranking, feedback tracking,
multi-query retrieval, and importance scoring.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np


# Lazy singleton for the Gemini client used by rate_fact_importance.
# Avoids creating a new httpx.AsyncClient (connection pool) per fact.
_llm_client: Any = None


def _get_llm_client():
    """Return a cached GeminiClient, creating it on first use."""
    global _llm_client
    if _llm_client is None:
        from app.llm.gemini_client import GeminiClient
        from app.config import settings

        _llm_client = GeminiClient(
            api_key=settings.gemini_api_key,
            default_model=settings.gemini_model,
        )
    return _llm_client

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Token estimation (rough but fast: ~4 chars per token for English/Hinglish)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken for accurate multi-lingual budgeting.

    Falls back to a ~4 chars/token heuristic if tiktoken is unavailable.
    """
    if not text:
        return 0
    try:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
        return len(_enc.encode(text))
    except Exception:
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
    """Rerank facts using NumPy-vectorized Maximal Marginal Relevance.

    Uses pre-computed embeddings from the DB and NumPy matrix operations
    to balance relevance and diversity with high-performance execution.
    """
    if len(facts) <= 2:
        return facts

    if not query_embedding:
        logger.warning("mmr_rerank_skipped", reason="no_query_embedding")
        return facts

    try:
        # Fetch pre-computed embeddings for all facts from DB
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

        fact_texts: list[str] = []
        fact_vectors: list[list[float]] = []
        for row in emb_rows.mappings().all():
            ft = str(row["fact_text"]).strip() if row["fact_text"] else ""
            emb_str = str(row["embedding"]) if row["embedding"] else ""
            if ft and emb_str:
                try:
                    fact_texts.append(ft)
                    fact_vectors.append(
                        [float(x) for x in emb_str.strip("[]").split(",")]
                    )
                except (ValueError, TypeError):
                    pass

        if len(fact_texts) < 2:
            return facts

        # Vectorized operations via NumPy
        q_vec = np.array(query_embedding)
        f_matrix = np.array(fact_vectors)

        # Vector unit-normalization for precise Cosine Similarity metrics
        q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)
        f_norms = f_matrix / (np.linalg.norm(f_matrix, axis=1, keepdims=True) + 1e-10)

        # Batch dot product scores relevance for all factors instantly
        relevance_scores = np.dot(f_norms, q_norm)

        # Track elements by matching string references
        fact_to_idx = {ft: i for i, ft in enumerate(fact_texts)}

        # Build strict lookup arrays for elements containing vector entries
        valid_indices = [i for i, f in enumerate(facts) if f in fact_to_idx]
        if not valid_indices:
            return facts

        # Vectorized tracking coordinates
        selected_indices = []
        remaining_indices = list(valid_indices)

        # Seed initial choice with the single highest relevance score element
        ordered_scores = np.array(
            [
                (
                    float(relevance_scores[fact_to_idx[facts[i]]])
                    if facts[i] in fact_to_idx
                    else 0.0
                )
                for i in range(len(facts))
            ]
        )

        best_initial = remaining_indices[
            int(np.argmax(ordered_scores[remaining_indices]))
        ]
        selected_indices.append(best_initial)
        remaining_indices.remove(best_initial)

        # Dynamic MMR Loop Execution
        while remaining_indices and len(selected_indices) < min(15, len(facts)):
            rem_relevance = ordered_scores[remaining_indices]

            # Map structural components out of matrix targets
            rem_matrix_vecs = f_norms[
                [fact_to_idx[facts[i]] for i in remaining_indices]
            ]
            sel_matrix_vecs = f_norms[[fact_to_idx[facts[i]] for i in selected_indices]]

            # Matrix cross-multiplication dots all selected vs remaining arrays instantly
            sim_matrix = np.dot(rem_matrix_vecs, sel_matrix_vecs.T)
            max_sim_to_selected = np.max(sim_matrix, axis=1)

            # Evaluate core MMR Equation: Maximize Relevance, Penalize Redundancy
            mmr_scores = (
                lambda_param * rem_relevance
                - (1.0 - lambda_param) * max_sim_to_selected
            )

            best_pos = int(np.argmax(mmr_scores))
            if mmr_scores[best_pos] < 0:
                break  # Drop loop execution early if similarity threshold breaks bounds

            best_idx = remaining_indices[best_pos]
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        # Stitch back any trailing structural facts lacking embeddings to prevent loss
        result = [facts[i] for i in selected_indices]
        seen_results = set(result)
        for f in facts:
            if f not in seen_results:
                result.append(f)

        logger.info(
            "mmr_rerank_complete",
            before=len(facts),
            after=len(result),
            lambda_param=lambda_param,
        )
        return result

    except Exception as e:
        logger.warning("mmr_rerank_failed", error=str(e), fact_count=len(facts))
        return facts


# ---------------------------------------------------------------------------
# Multi-query retrieval
# ---------------------------------------------------------------------------


def generate_query_variants(
    current_text: str,
    person_name: str = "",
    max_variants: int = 3,
) -> list[str]:
    """Generate multiple query variants for better recall.

    Produces up to ``max_variants`` query strings that capture different
    aspects of the user's input: the original, a person-name-enriched
    variant, and a keyword-only variant (content words > 2 chars).
    """
    text = current_text.strip()
    if not text:
        return [""]

    variants: list[str] = []
    seen: set[str] = set()

    variants.append(text)
    seen.add(normalize_for_dedup(text))

    if person_name and person_name.strip():
        enriched = f"{person_name}: {text}"
        norm = normalize_for_dedup(enriched)
        if norm not in seen and len(variants) < max_variants:
            variants.append(enriched)
            seen.add(norm)

    words = text.split()
    if len(words) >= 3 and len(variants) < max_variants:
        # Select content words by length heuristic (> 2 chars)
        content_words = [w for w in words if len(w) > 2][:3]
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
# 3-Tier Memory Buffer helpers
# ---------------------------------------------------------------------------


def build_tier1_raw_exchanges(
    interactions: list[dict[str, Any]],
    max_messages: int = 6,
) -> str:
    """Tier 1 — FIFO sliding window of the last N raw message exchanges.

    Extracts verbatim messages from ``transcript_json`` of the most recent
    interactions and formats them as a chronological exchange log.  Falls
    back to ``their_last_message`` when ``transcript_json`` is unavailable.
    """
    all_messages: list[tuple[str, str]] = []

    for interaction in interactions:  # already chronological (oldest → newest)
        transcript_raw = interaction.get("transcript_json")
        if transcript_raw:
            try:
                pairs = json.loads(transcript_raw)
                for pair in pairs:
                    if not isinstance(pair, dict):
                        continue
                    sender = pair.get("s", "")
                    text = (pair.get("t") or "").strip()
                    if not text:
                        continue
                    label = "them" if sender == "them" else "you"
                    all_messages.append((label, text))
                continue
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: use their_last_message
        their_msg = (interaction.get("their_last_message") or "").strip()
        if their_msg:
            all_messages.append(("them", their_msg))

    # Keep only the tail (most recent messages)
    all_messages = all_messages[-max_messages:]

    if not all_messages:
        return ""

    return "\n".join(f'{label}: "{text}"' for label, text in all_messages)


def build_tier2_narrative_summary(
    interactions: list[dict[str, Any]],
) -> str:
    """Tier 2 — Compressed narrative of the recent conversation arc.

    Formats the last 5 interactions as a compact chronological narrative
    showing what was discussed and how the conversation progressed, without
    requiring an LLM call.
    """
    if not interactions:
        return ""

    lines: list[str] = []
    for interaction in interactions:  # chronological (oldest → newest)
        direction = interaction.get("direction", "unknown")
        their_msg = (interaction.get("their_last_message") or "").strip()
        copied_index = interaction.get("copied_index")
        key_detail = (interaction.get("key_detail") or "").strip()

        # Extract what was actually sent
        sent_text = ""
        if copied_index is not None:
            raw_reply = interaction.get(f"reply_{copied_index}") or ""
            if raw_reply:
                try:
                    loaded = json.loads(raw_reply)
                    if isinstance(loaded, dict) and "text" in loaded:
                        sent_text = str(loaded["text"]).strip()
                except (json.JSONDecodeError, TypeError):
                    sent_text = str(raw_reply).strip()

        parts: list[str] = []
        if key_detail:
            parts.append(f"hook: {key_detail}")
        if their_msg:
            parts.append(f'her: "{their_msg}"')
        if sent_text:
            parts.append(f'you: "{sent_text}"')

        if parts:
            lines.append(f"[{direction}] {' | '.join(parts)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Graph RAG Extraction Schemas
# ---------------------------------------------------------------------------


class EntityNode(BaseModel):
    """A concrete noun/entity extracted from a conversational fact."""

    name: str = Field(
        ..., description="The concrete noun/entity name, e.g., 'Ragini', 'MAMC', 'Guitar'."
    )
    type: str = Field(
        ...,
        description=(
            "Category: 'person', 'profession', 'organization', 'hobby', "
            "'location', 'status'."
        ),
    )


class RelationshipEdge(BaseModel):
    """A directed edge between two entity nodes."""

    source: str = Field(..., description="The name of the source entity node.")
    target: str = Field(..., description="The name of the target entity node.")
    relationship: str = Field(
        ...,
        description=(
            "Action link in UPPERCASE snake_case, "
            "e.g., 'WORKS_AS', 'PLAYS', 'LIVES_IN'."
        ),
    )


class KnowledgeGraphTriples(BaseModel):
    """Schema enforced by Gemini Structured Outputs for graph extraction."""

    entities: list[EntityNode] = Field(default_factory=list)
    relationships: list[RelationshipEdge] = Field(default_factory=list)


_GEMINI_GRAPH_SCHEMA: dict = KnowledgeGraphTriples.model_json_schema()


# ---------------------------------------------------------------------------
# Learned Sparse Retrieval — Write-Time Token Expansion
# ---------------------------------------------------------------------------


class SparseTokenExpansion(BaseModel):
    """Schema for multi-lingual lexical expansion tokens."""

    expanded_tokens: list[str] = Field(
        ...,
        description=(
            "List of raw synonyms, hidden conceptual terms, context words, "
            "and explicit cross-lingual translations (English <-> Hinglish)."
        ),
    )


_GEMINI_SPARSE_SCHEMA: dict = SparseTokenExpansion.model_json_schema()


async def generate_sparse_lexical_extensions(fact_text: str) -> str:
    """Expand a fact into its semantic synonyms and cross-lingual equivalents.

    The result is stored in ``conversation_memories.lexical_expansion`` and
    fed into a combined GIN index so that PostgreSQL full-text search can
    match dialectal and romanized variants without a dedicated SPLADE service.
    """
    if not fact_text or not fact_text.strip():
        return ""

    try:
        client = _get_llm_client()

        result = await client.generate_structured(
            system_prompt=(
                "You are a search index expansion engine. Output alternative "
                "keywords, synonyms, and explicit English-to-Hinglish semantic "
                "translations. For example, if the text contains 'married', "
                "output ['shaadi', 'shuda', 'husband', 'wife', 'spouse']."
            ),
            user_prompt=(
                f'Generate search index keyword expansions for this text '
                f'fragment: "{fact_text}"'
            ),
            response_schema=_GEMINI_SPARSE_SCHEMA,
            temperature=0.0,
            max_output_tokens=256,
            usage_phase="sparse_lexical_expansion",
        )

        data = SparseTokenExpansion.model_validate(result)
        expanded = " ".join(data.expanded_tokens).lower()
        logger.info(
            "sparse_expansion_success",
            fact=fact_text[:50],
            token_count=len(data.expanded_tokens),
        )
        return expanded

    except Exception as e:
        logger.warning(
            "sparse_expansion_failed",
            error=str(e),
            fact=fact_text[:50],
        )
        return ""


# ---------------------------------------------------------------------------
# Structured Output Schemas for LLM-based fact classification
# ---------------------------------------------------------------------------


class FactCategory(str, Enum):
    """Semantic category for a user profile fact."""

    IDENTITY = "identity"  # Core data: job, hometown, relationship status
    PREFERENCE = "preference"  # Likes, dislikes, diet, habits
    OPINION = "opinion"  # Explicit views, relationship goals, philosophies
    FACTUAL = "factual"  # Informational, abstract text fragments


class StructuredFactAnalysis(BaseModel):
    """Schema enforced by Gemini Structured Outputs Mode."""

    importance_score: int = Field(
        ...,
        description="Value from 1 to 5. 5 = Critical identity/status, 1 = trivial fleeting details.",
        ge=1,
        le=5,
    )
    category: FactCategory = Field(
        ...,
        description="The semantic category that best fits this statement.",
    )


# JSON Schema that Gemini receives via responseSchema — avoids runtime
# dependency on google-genai SDK by using the existing REST client.
_GEMINI_FACT_SCHEMA: dict = StructuredFactAnalysis.model_json_schema()

# ---------------------------------------------------------------------------
# Graph RAG Extraction Utility
# ---------------------------------------------------------------------------


async def extract_graph_triples(fact_text: str) -> KnowledgeGraphTriples:
    """Extract semantic graph nodes and edges from raw text using Gemini.

    Returns structured entity-relationship triples that get persisted into
    the graph tables (conversation_memory_entities + conversation_memory_edges).
    """
    if not fact_text or not fact_text.strip():
        return KnowledgeGraphTriples()

    try:
        client = _get_llm_client()

        result = await client.generate_structured(
            system_prompt=(
                "You are a strict graph network data extractor. Break conversational "
                "information into isolated entities and clear directed logical "
                "predicate edges."
            ),
            user_prompt=(
                f'Extract all knowledge graph entities and relationships from '
                f'this text: "{fact_text}"'
            ),
            response_schema=_GEMINI_GRAPH_SCHEMA,
            temperature=0.0,
            max_output_tokens=512,
            usage_phase="graph_triple_extraction",
        )

        triples = KnowledgeGraphTriples.model_validate(result)
        logger.info(
            "graph_triple_extraction_success",
            fact=fact_text[:50],
            entity_count=len(triples.entities),
            relationship_count=len(triples.relationships),
        )
        return triples

    except Exception as e:
        logger.warning(
            "graph_triple_extraction_failed",
            error=str(e),
            text=fact_text[:50],
        )
        return KnowledgeGraphTriples()


# ---------------------------------------------------------------------------
# LLM-Based Importance Scoring & Categorization
# ---------------------------------------------------------------------------


async def rate_fact_importance(
    fact_text: str,
) -> tuple[int | None, str | None]:
    """Rate fact importance and categorize dynamically using Gemini Structured Outputs.

    Handles mixed multi-lingual inputs and romanized Hinglish/Hindi phrases
    without relying on brittle hardcoded keyword lists.

    Falls back to a lightweight heuristic chain when the LLM call fails
    (rate-limits, network errors, etc.).
    """
    if not fact_text or not fact_text.strip():
        return None, None

    try:
        client = _get_llm_client()

        result = await client.generate_structured(
            system_prompt=(
                "You are an expert user profiling metadata annotator. "
                "Accurately categorize facts and assign importance weights."
            ),
            user_prompt=(
                f'Analyze the following statement or profile trait extracted '
                f'from a user\'s conversational profile history:\n\n"{fact_text}"'
            ),
            response_schema=_GEMINI_FACT_SCHEMA,
            temperature=0.0,
            max_output_tokens=256,
            usage_phase="fact_importance_classification",
        )

        analysis = StructuredFactAnalysis.model_validate(result)

        logger.info(
            "llm_fact_categorization_success",
            fact=fact_text[:50],
            score=analysis.importance_score,
            category=analysis.category.value,
        )
        return analysis.importance_score, analysis.category.value

    except Exception as e:
        logger.warning(
            "llm_fact_categorization_failed",
            error=str(e),
            fact=fact_text[:50],
        )

        # Fallback heuristic chain — covers the common identity/preference
        # cases when the API is unreachable or rate-limited.
        text_lower = fact_text.lower()
        identity_kws = [
            "married", "divorced", "widowed", "single",
            "muslim", "hindu", "sikh", "christian", "jain", "buddhist",
            "lives in", "hometown", "from ", "based in",
            "works as", "job", "profession",
            # Hinglish / Hindi romanized equivalents
            "shaadi", "shuda", "married", "talaaq", "divorced",
            "hindu", "muslim", "sikh", "christian", "jain",
            "rahta hai", "rahiti hai", "rehti hai",  # lives in
            "kaam", "naukri", "padhai",  # job, work, studies
        ]
        if any(kw in text_lower for kw in identity_kws):
            return 5, "identity"

        preference_kws = [
            "has kids", "no kids", "vegetarian", "vegan",
            "non-vegetarian", "engineer", "doctor", "lawyer",
            "phd", "masters", "degree", "age", "born", "birthday",
            # Hinglish / Hindi romanized equivalents
            "bachche", "kids", "non-veg", "veg",
            "nakshatra", "zodiac", "rashi",
            "birthday", "janamdin", "age", "umra",
        ]
        if any(kw in text_lower for kw in preference_kws):
            return 4, "preference"

        opinion_kws = [
            "looking for", "want", "interested in", "love",
            "hate", "like", "enjoys", "hobby", "passionate", "goal",
            # Hinglish / Hindi romanized equivalents
            "chahti hai", "chahta hai",  # wants
            "pasand", "nafrat",  # like, hate
            "shauk", "hobby",  # hobby, interest
            "intention", "plan",  # goals
        ]
        if any(kw in text_lower for kw in opinion_kws):
            return 3, "opinion"

        if len(fact_text) > 30:
            return 2, "factual"

        return 1, "preference"
