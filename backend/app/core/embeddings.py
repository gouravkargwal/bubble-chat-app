from __future__ import annotations

from typing import List, Optional

import structlog

from app.config import settings
from app.llm.genai import generate_embedding as _genai_embed

logger = structlog.get_logger()

# Default embedding dimensionality. pgvector column is 768d.
# text-embedding-005 outputs 768 by default.
EMBEDDING_DIMENSIONS = 768


async def embed_text(text: str, dimensions: int | None = None) -> Optional[List[float]]:
    """Generate an embedding vector using the google-genai SDK.

    If `dimensions` is provided, we force the model to return exactly that output
    dimensionality. Otherwise we fall back to `EMBEDDING_DIMENSIONS`.

    This replaces the old LangChain GoogleGenerativeAIEmbeddings wrapper.
    """
    import asyncio

    try:
        dimensions_to_use = dimensions or EMBEDDING_DIMENSIONS

        # The SDK's embed_content is synchronous, offload to thread.
        embedding = await asyncio.to_thread(
            _genai_embed,
            text=text,
            model=settings.gemini_embedding_model,
            dimensions=dimensions_to_use,
        )

        if embedding is None:
            return None

        if len(embedding) != dimensions_to_use:
            logger.error(
                "embedding_dimension_mismatch",
                embedding_model=settings.gemini_embedding_model,
                expected_dim=dimensions_to_use,
                actual_dim=len(embedding),
                text_preview=text[:120] if text else "",
            )
            return None

        return embedding

    except Exception as e:  # pragma: no cover - defensive against embedding outages
        logger.error(
            "embedding_api_failed",
            error=str(e),
            text_preview=text[:120] if text else "",
            embedding_model=settings.gemini_embedding_model,
        )
        # Important: embeddings are non-critical; callers should continue with None.
        return None
