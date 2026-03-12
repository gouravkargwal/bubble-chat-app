"""Background tasks and services for Voice DNA and semantic profiling."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import UserVoiceDNA
from app.llm.gemini_client import GeminiClient


async def generate_semantic_profile_background(
    user_id: str, db: AsyncSession, messages: list[str]
) -> None:
    """Runs in the background to build a psychological style guide using Gemini Pro."""
    if len(messages) < 3:
        return

    system_prompt = (
        "You are an expert behavioral psychologist and linguist. "
        "Analyze the following text messages sent by a single user. "
        "Write a strict, 3-sentence 'Style Guide' defining their exact tone, humor style, punctuation habits, and specific slang. "
        "Focus on the 'vibe' (e.g., dry sarcasm, golden retriever energy, blunt, flirty). "
        "Do NOT output anything other than the 3-sentence guide."
    )

    user_prompt = "User's recent messages:\n" + "\n".join(
        [f"- {msg}" for msg in messages]
    )

    try:
        client = GeminiClient(api_key=settings.gemini_api_key)
        # Use the heavier reasoning model for profiling
        profile_text = await client.generate_content(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="gemini-3.1-pro",  # Premium Model
            temperature=0.3,
        )

        # Save to database
        result = await db.execute(
            select(UserVoiceDNA).where(UserVoiceDNA.user_id == user_id)
        )
        voice_db = result.scalar_one_or_none()
        if voice_db:
            # Store raw text; callers can treat it as plain string
            voice_db.semantic_profile = profile_text.strip()
            await db.commit()

    except Exception:
        # Silently fail in background, don't crash the app
        pass
