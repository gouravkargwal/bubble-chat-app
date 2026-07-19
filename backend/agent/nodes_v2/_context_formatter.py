"""
Context formatter for the generator prompt.

Transforms raw RAG context (core_lore, tier_1, tier_2) into a well-structured,
importance-weighted, token-budgeted prompt section.

Pipeline (all improvements applied):
  1. Parse core_lore lines
  2. Sort by importance_score (improvement 2)
  3. Group by category (improvement 6)
  4. Add section headers and labels (improvement 1)
  5. Format tier_1/tier_2 with headers (improvement 5)
  6. Truncate to token budget (improvement 3)
  7. Return formatted string
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag_improvements import estimate_tokens

# Default token budget for each context section
_MAX_CORE_LORE_TOKENS = 800
_MAX_TIER_1_TOKENS = 400
_MAX_TIER_2_TOKENS = 300

# Category display names and priority order
_CATEGORY_LABELS: dict[str, str] = {
    "identity": "IDENTITY (confirmed facts about her)",
    "preference": "PREFERENCES",
    "opinion": "OPINIONS & GOALS",
    "factual": "GENERAL FACTS",
}

_CATEGORY_ORDER = ["identity", "preference", "opinion", "factual"]


def format_rag_context(
    core_lore: str,
    tier_1_raw: str = "",
    tier_2_summary: str = "",
    max_core_lore_tokens: int = _MAX_CORE_LORE_TOKENS,
    max_tier_1_tokens: int = _MAX_TIER_1_TOKENS,
    max_tier_2_tokens: int = _MAX_TIER_2_TOKENS,
    facts_meta: list[dict[str, Any]] | None = None,
) -> str:
    """Format RAG context into a structured, labeled prompt section.

    Args:
        core_lore: Raw facts from conversation_memories, one per line.
        tier_1_raw: Raw recent chat exchanges (Tier 1).
        tier_2_summary: Compressed narrative summary (Tier 2).
        max_core_lore_tokens: Max tokens for core_lore section.
        max_tier_1_tokens: Max tokens for tier_1 section.
        max_tier_2_tokens: Max tokens for tier_2 section.
        facts_meta: Optional list of dicts with 'text', 'category', 'importance'.
            When provided, enables category grouping and importance sorting.

    Returns:
        Formatted context string ready for prompt injection.
    """
    sections: list[str] = []

    # ── Core Lore: what we know about her ────────────────────────────────
    lore_lines = [
        ln.strip()
        for ln in core_lore.split("\n")
        if ln.strip() and not ln.startswith("===")
    ]
    if lore_lines:
        formatted_lore = _format_core_lore(
            lore_lines, max_core_lore_tokens, facts_meta
        )
        if formatted_lore:
            sections.append(formatted_lore)

    # ── Tier 1: recent raw exchanges ─────────────────────────────────────
    if tier_1_raw.strip():
        formatted_t1 = _format_tier_1(tier_1_raw, max_tier_1_tokens)
        if formatted_t1:
            sections.append(formatted_t1)

    # ── Tier 2: conversation arc summary ─────────────────────────────────
    if tier_2_summary.strip():
        formatted_t2 = _format_tier_2(tier_2_summary, max_tier_2_tokens)
        if formatted_t2:
            sections.append(formatted_t2)

    return "\n\n".join(sections)


# ── Improvement 1: Structured Section Labels ────────────────────────────────
# ── Improvement 2: Importance-Weighted Sorting ─────────────────────────────
# ── Improvement 6: Category Grouping ────────────────────────────────────────


def _format_core_lore(
    lines: list[str],
    max_tokens: int,
    facts_meta: list[dict[str, Any]] | None = None,
) -> str:
    """Format core lore facts with section header, category groups, and importance sorting.

    When facts_meta is provided (improvement 2+6):
      - Sorts facts by importance_score descending
      - Groups facts by category with labeled headers

    When facts_meta is None (fallback for backward compat):
      - Preserves original order
      - Bullet-points with section header only
    """
    if not lines:
        return ""

    if facts_meta:
        return _format_with_meta(lines, facts_meta, max_tokens)

    # Fallback: no metadata — just bullet-point in original order
    bullet_lines = [f"• {line}" for line in lines]
    truncated = _truncate_by_tokens(bullet_lines, max_tokens)
    return (
        "─── FACTS YOU KNOW ABOUT HER ───\n"
        f"{chr(10).join(truncated)}"
    )


def _format_with_meta(
    lines: list[str],
    facts_meta: list[dict[str, Any]],
    max_tokens: int,
) -> str:
    """Group facts by category, sort by importance within each group."""
    # Build lookup: fact text → metadata
    meta_lookup: dict[str, dict[str, Any]] = {}
    for m in facts_meta:
        text = (m.get("text") or "").strip()
        if text:
            meta_lookup[text] = m

    # Annotate each line with its metadata
    annotated: list[dict[str, Any]] = []
    for line in lines:
        meta = meta_lookup.get(line, {})
        annotated.append({
            "text": line,
            "importance": meta.get("importance", 3),
            "category": meta.get("category", "factual"),
        })

    # Sort: importance descending (improvement 2)
    annotated.sort(key=lambda x: -x["importance"])

    # Group by category (improvement 6)
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in annotated:
        cat = item["category"]
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)

    # Build section in category priority order
    parts: list[str] = []
    total_tokens = 0
    remaining = max_tokens

    # Add a "FACTS YOU KNOW ABOUT HER" header
    header = "─── FACTS YOU KNOW ABOUT HER ───"
    header_tokens = estimate_tokens(header)
    total_tokens += header_tokens
    parts.append(header)

    for cat in _CATEGORY_ORDER:
        if cat not in groups:
            continue
        cat_items = groups[cat]
        # Add category sub-header
        cat_label = _CATEGORY_LABELS.get(cat, cat.upper())
        label_line = f"\n  [{cat_label}]"
        label_tokens = estimate_tokens(label_line)
        if total_tokens + label_tokens > remaining and len(parts) > 1:
            break
        parts.append(label_line)
        total_tokens += label_tokens

        # Add fact lines (with confirmed/inferred labels — improvement 4)
        for item in cat_items:
            fact_text = item["text"]
            source = item.get("source", None)
            src_label = _label_source(fact_text, source)
            fl_labeled = f"• {src_label}{fact_text}"

            fl_tokens = estimate_tokens(fl_labeled)
            if total_tokens + fl_tokens > remaining and len(parts) > 2:
                break
            parts.append(fl_labeled)
            total_tokens += fl_tokens

    return "\n".join(parts)


def _format_tier_1(raw: str, max_tokens: int) -> str:
    """Format Tier 1 (recent chat exchanges) with section header."""
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    if not lines:
        return ""

    truncated = _truncate_by_tokens(lines, max_tokens)
    return (
        "─── RECENT CHAT (LAST EXCHANGES) ───\n"
        f"{chr(10).join(truncated)}"
    )


def _format_tier_2(raw: str, max_tokens: int) -> str:
    """Format Tier 2 (conversation arc) with section header."""
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    if not lines:
        return ""

    truncated = _truncate_by_tokens(lines, max_tokens)
    return (
        "─── CONVERSATION ARC SUMMARY ───\n"
        f"{chr(10).join(truncated)}"
    )


# ── Improvement 4: Confirmed vs Inferred Labels ──────────────────────────────

_CONFIRMED_KEYWORDS = [
    "said", "told", "mentioned", "confirmed", "is", "works as",
    "studied at", "lives in", "from ", "years old", "has a",
    "speaks", "owns", "adopted",
]
_INFERRED_KEYWORDS = [
    "seems", "appears", "likely", "probably", "might", "could be",
    "suggests", "implied", "gives the impression",
]


def _label_source(fact_text: str, fact_source: str | None = None) -> str:
    """Add [CONFIRMED] or [INFERRED] label based on source metadata or heuristic.

    Args:
        fact_text: The fact text to analyze.
        fact_source: Optional source from DB ('explicit' or 'inferred').
            If None, uses keyword heuristic.

    Returns:
        Label prefix string (e.g., "[CONFIRMED] ") or empty string.
    """
    if fact_source == "explicit":
        return "[CONFIRMED] "
    if fact_source == "inferred":
        return "[INFERRED] "

    # Heuristic fallback when source metadata is unavailable
    text_lower = fact_text.lower()
    if any(kw in text_lower for kw in _INFERRED_KEYWORDS):
        return "[INFERRED] "
    # Facts that state concrete attributes are likely confirmed
    if any(kw in text_lower for kw in _CONFIRMED_KEYWORDS):
        return "[CONFIRMED] "
    return "[CONFIRMED] "  # Default: assume confirmed


# ── Utility ──────────────────────────────────────────────────────────────────


def _truncate_by_tokens(lines: list[str], max_tokens: int) -> list[str]:
    """Truncate a list of lines to fit within a token budget."""
    if not lines:
        return []

    result: list[str] = []
    total = 0
    for line in lines:
        tokens = estimate_tokens(line)
        if total + tokens > max_tokens and result:
            break  # Don't stop if we haven't added anything yet
        result.append(line)
        total += tokens
    return result


# ── Fact Metadata Fetching ────────────────────────────────────────────────────


async def fetch_facts_meta(
    db: AsyncSession,
    user_id: str,
    conversation_id: str,
) -> list[dict[str, Any]]:
    """Fetch fact metadata from DB for importance sorting and category grouping.

    Queries conversation_memories for the given conversation and returns
    structured metadata for each active (non-superseded) fact.
    """
    if not conversation_id or not user_id:
        return []

    try:
        rows = await db.execute(
            text("""
                SELECT fact_text, fact_category, importance_score, fact_source
                FROM conversation_memories
                WHERE user_id = :user_id
                  AND conversation_id = :conversation_id
                  AND superseded_at IS NULL
                  AND embedding IS NOT NULL
                ORDER BY created_at ASC
            """),
            {"user_id": user_id, "conversation_id": conversation_id},
        )
        return [
            {
                "text": str(r.fact_text).strip(),
                "category": str(r.fact_category) if r.fact_category else "factual",
                "importance": int(r.importance_score) if r.importance_score else 3,
                "source": str(r.fact_source) if r.fact_source else "explicit",
            }
            for r in rows.mappings().all()
            if r.fact_text
        ]
    except Exception:
        return []
