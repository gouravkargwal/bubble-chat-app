from __future__ import annotations

from functools import lru_cache
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings


# NOTE: Some google-genai / LangChain versions require model names without the
# "models/" prefix for embedContent. Keep this as the plain model id.
EMBEDDING_MODEL_NAME = "text-embedding-004"
EMBEDDING_DIMENSIONS = 1536


@lru_cache(maxsize=1)
def _get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Return a cached Gemini embeddings client."""
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL_NAME)


async def embed_text(text: str) -> List[float]:
    """Generate a 1536-dim embedding vector for the given text using Gemini.

    This uses LangChain's GoogleGenerativeAIEmbeddings wrapper under the hood.
    """
    # The underlying client is synchronous, so offload to a thread.
    import asyncio

    model = _get_embeddings_model()
    return await asyncio.to_thread(model.embed_query, text)


