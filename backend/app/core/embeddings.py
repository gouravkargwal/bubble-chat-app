from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

import structlog
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore[reportMissingImports]

logger = structlog.get_logger()

# The actual active 2026 model
EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
# We must strictly enforce this to match the Postgres pgvector schema
EMBEDDING_DIMENSIONS = 768


@lru_cache(maxsize=1)
def _get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Return a cached Gemini embeddings client."""
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL_NAME)


async def embed_text(text: str) -> Optional[List[float]]:
    """Generate a 768-dim embedding vector for the given text using Gemini's MRL truncation.

    This uses LangChain's GoogleGenerativeAIEmbeddings wrapper under the hood.
    """
    # The underlying client is synchronous, so offload to a thread.
    import asyncio

    model = _get_embeddings_model()
    try:
        # CRITICAL: output_dimensionality must be passed here, NOT in the constructor
        embedding = await asyncio.to_thread(
            model.embed_query, text, output_dimensionality=EMBEDDING_DIMENSIONS
        )

        if not embedding or len(embedding) != EMBEDDING_DIMENSIONS:
            logger.error(
                "embedding_dimension_mismatch",
                embedding_model=EMBEDDING_MODEL_NAME,
                expected_dim=EMBEDDING_DIMENSIONS,
                actual_dim=len(embedding) if embedding else 0,
                text_preview=text[:120] if text else "",
            )
            return None

        return embedding

    except Exception as e:  # pragma: no cover - defensive against embedding outages
        logger.error(
            "embedding_api_failed",
            error=str(e),
            text_preview=text[:120] if text else "",
            embedding_model=EMBEDDING_MODEL_NAME,
        )
        # Important: embeddings are non-critical; callers should continue with None.
        return None
