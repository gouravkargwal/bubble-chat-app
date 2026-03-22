from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

import structlog
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore[reportMissingImports]

logger = structlog.get_logger()

# The actual active 2026 model
EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
# We must strictly enforce this to match the Postgres pgvector schema
# Default embedding dimensionality.
#
# NOTE: pgvector's expected dimensionality comes from the `Interaction.embedding`
# column type at runtime. We still keep a default here, but callers should pass
# the expected dimension when they can.
EMBEDDING_DIMENSIONS = 768


@lru_cache(maxsize=1)
def _get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Return a cached Gemini embeddings client."""
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL_NAME)


async def embed_text(text: str, dimensions: int | None = None) -> Optional[List[float]]:
    """Generate an embedding vector for the given text.

    If `dimensions` is provided, we force Gemini to return exactly that output dimensionality.
    Otherwise we fall back to `EMBEDDING_DIMENSIONS`.

    This uses LangChain's GoogleGenerativeAIEmbeddings wrapper under the hood.
    """
    # The underlying client is synchronous, so offload to a thread.
    import asyncio

    model = _get_embeddings_model()
    try:
        dimensions_to_use = dimensions or EMBEDDING_DIMENSIONS

        # CRITICAL: output_dimensionality must be passed here, NOT in the constructor
        embedding = await asyncio.to_thread(
            model.embed_query, text, output_dimensionality=dimensions_to_use
        )

        if not embedding or len(embedding) != dimensions_to_use:
            logger.error(
                "embedding_dimension_mismatch",
                embedding_model=EMBEDDING_MODEL_NAME,
                expected_dim=dimensions_to_use,
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
