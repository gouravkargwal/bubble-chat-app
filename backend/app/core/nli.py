from __future__ import annotations

import asyncio
from functools import lru_cache

import structlog

logger = structlog.get_logger(__name__)

# Labels returned by cross-encoder/nli-deberta-v3-small:
# 0 = contradiction, 1 = entailment, 2 = neutral
_CONTRADICTION_LABEL = 0


@lru_cache(maxsize=1)
def _get_nli_model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder("cross-encoder/nli-deberta-v3-small")


def _predict_sync(premise: str, hypothesis: str) -> bool:
    model = _get_nli_model()
    scores = model.predict([[premise, hypothesis]])
    return int(scores.argmax()) == _CONTRADICTION_LABEL


async def is_contradiction(existing_fact: str, new_fact: str) -> bool:
    """Return True if new_fact contradicts existing_fact.

    Runs the CPU-bound NLI model in a thread so the event loop stays free.
    Never raises — returns False on model errors so ingestion is never blocked.
    """
    try:
        return await asyncio.to_thread(_predict_sync, existing_fact, new_fact)
    except Exception as e:
        logger.warning("nli_check_failed", error=str(e))
        return False


def warmup() -> None:
    """Load the NLI model into memory. Call once at startup."""
    try:
        _get_nli_model()
        logger.info("nli_model_loaded")
    except Exception as e:
        logger.warning("nli_model_load_failed", error=str(e))
