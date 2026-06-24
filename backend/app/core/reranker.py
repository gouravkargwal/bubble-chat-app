"""
Cross-encoder reranker using FlashRank (CPU-only, zero API cost).

Runs a lightweight ms-marco-MiniLM-L-12-v2 model locally to score
retrieved passages against the original query.

Usage:
    from app.core.reranker import rerank_passages
    top_results = await rerank_passages(query, passages, top_k=8)

Dependencies:
    pip install flashrank

Fallback:
    If flashrank is not installed, returns passages in original order.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded singleton ranker
_ranker_instance = None


def _get_ranker():
    """Lazy-load the FlashRank Ranker singleton."""
    global _ranker_instance
    if _ranker_instance is not None:
        return _ranker_instance

    try:
        from flashrank import Ranker

        _ranker_instance = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
        logger.info(
            "flashrank_ranker_loaded",
            model="ms-marco-MiniLM-L-12-v2",
        )
        return _ranker_instance
    except ImportError:
        logger.warning(
            "flashrank_not_installed", message="Install with: pip install flashrank"
        )
        return None
    except Exception as e:
        logger.warning("flashrank_load_failed", error=str(e))
        return None


async def rerank_passages(
    query: str,
    passages: list[dict[str, Any]],
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """Rerank passages against the query using FlashRank cross-encoder.

    Args:
        query: The original user query string.
        passages: List of dicts with at least {"text": str, ...}
        top_k: Number of top results to return after reranking.

    Returns:
        Reranked passages sorted by relevance (most relevant first).
        Falls back to original order if FlashRank unavailable.
    """
    if not query or not passages:
        return passages

    ranker = _get_ranker()
    if ranker is None:
        logger.debug("flashrank_rerank_skipped", reason="ranker_unavailable")
        return passages[:top_k]

    try:
        from flashrank import RerankRequest

        # Format passages for FlashRank (needs 'id', 'text', optionally 'meta')
        formatted = []
        for idx, p in enumerate(passages):
            text = p.get("text", "") if isinstance(p, dict) else str(p)
            formatted.append(
                {
                    "id": idx,
                    "text": text,
                    "meta": p.get("meta", {}) if isinstance(p, dict) else {},
                }
            )

        request = RerankRequest(query=query, passages=formatted)
        reranked = ranker.rerank(request)

        # Take top_k results
        top = reranked[:top_k]

        # Map back to original passage format
        result_indices = {r["id"] for r in top}
        # Return in reranked order
        results = []
        seen_ids = set()
        for r in top:
            rid = r["id"]
            if rid not in seen_ids and rid < len(passages):
                seen_ids.add(rid)
                orig = passages[rid]
                if isinstance(orig, dict):
                    results.append(orig)
                else:
                    results.append({"text": str(orig)})

        # If any top passages were missed (shouldn't happen), append remaining
        if len(results) < len(top):
            for idx, p in enumerate(passages):
                if idx not in seen_ids:
                    if isinstance(p, dict):
                        results.append(p)
                    else:
                        results.append({"text": str(p)})

        logger.info(
            "flashrank_rerank_complete",
            input_count=len(passages),
            output_count=len(results),
            top_k=top_k,
        )
        return results

    except Exception as e:
        logger.warning("flashrank_rerank_failed", error=str(e))
        return passages[:top_k]
