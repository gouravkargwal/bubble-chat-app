"""Service for generating an optimized dating profile blueprint from audited photos."""

import json
import time
from typing import Any

import structlog
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import AuditedPhoto
from app.llm.gemini_client import GeminiClient
from app.models.profile_optimizer import ProfileBlueprint

logger = structlog.get_logger()


PROFILE_BLUEPRINT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "slots": {
            "type": "ARRAY",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "OBJECT",
                "properties": {
                    "photo_id": {"type": "STRING"},
                    "slot_number": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 6,
                    },
                    "role": {"type": "STRING"},
                    "caption": {"type": "STRING"},
                    "hinge_prompt_question": {"type": "STRING"},
                    "hinge_prompt_answer": {"type": "STRING"},
                    "coach_reasoning": {"type": "STRING"},
                },
                "required": [
                    "photo_id",
                    "slot_number",
                    "role",
                    "caption",
                    "hinge_prompt_question",
                    "hinge_prompt_answer",
                    "coach_reasoning",
                ],
            },
        },
        "overall_theme": {"type": "STRING"},
    },
    "required": ["slots", "overall_theme"],
}


_client: GeminiClient | None = None


def _get_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient(
            api_key=settings.gemini_api_key,
            default_model=settings.gemini_model,
        )
    return _client


async def _fetch_top_audited_photos(user_id: str, db: AsyncSession) -> list[AuditedPhoto]:
    """Fetch up to 10 highest scoring audited photos for a user (score >= 6)."""
    stmt: Select[tuple[AuditedPhoto]] = (
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user_id, AuditedPhoto.score >= 6)
        .order_by(AuditedPhoto.score.desc(), AuditedPhoto.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    photos: list[AuditedPhoto] = list(result.scalars().all())
    return photos


async def generate_blueprint(user_id: str, db: AsyncSession) -> ProfileBlueprint:
    """Generate a ProfileBlueprint from a user's top audited photos using Gemini.

    The LLM receives only previously audited photos, and must select exactly six
    of them with slots 1–6. The JSON response is validated against a strict
    schema and then enriched with concrete storage URLs for each selected photo.
    """
    photos = await _fetch_top_audited_photos(user_id=user_id, db=db)
    if not photos:
        raise ValueError("No eligible audited photos found for this user.")

    # Serialize minimal photo data for the LLM (no URLs/paths needed).
    photo_payload = [
        {
            "id": photo.id,
            "score": photo.score,
            "tier": photo.tier,
            "brutal_feedback": photo.brutal_feedback,
        }
        for photo in photos
    ]
    photos_json = json.dumps(photo_payload, ensure_ascii=False)

    system_prompt = (
        "You are an elite dating profile creative director. "
        "Your job is to select exactly 6 photos from the provided list of previously audited photos "
        "to create a perfectly balanced dating profile. Assign each a slot (1-6). "
        "Slot 1 MUST be the best clear face shot. Provide a witty, high-status caption and a "
        "suggested Hinge prompt for each.\n\n"
        "You MUST respond with JSON that strictly matches the provided JSON schema. "
        "Do not include any commentary outside of the JSON."
    )

    user_prompt = (
        "You are given a JSON array of previously audited dating profile photos.\n"
        "- Each object has fields: id, score (1-10), tier (e.g. GOD_TIER / FILLER / GRAVEYARD), "
        "and brutal_feedback written by another coach.\n"
        "- You MUST select exactly 6 distinct photos using the `id` field.\n"
        "- `slot_number` must be 1 through 6 with no gaps or duplicates.\n"
        "- Slot 1 MUST be the single best clear face shot for first impression.\n"
        "- Optimize for status, charisma, social proof, and variety of settings while avoiding try-hard energy.\n"
        "- Use the brutal_feedback notes as context but feel free to disagree if you have a better framing.\n"
        "- For each chosen photo, write:\n"
        "  * A short, high-status caption that would sit under the photo.\n"
        "  * A Hinge prompt question that fits this slot and the overall vibe.\n"
        "  * A Hinge prompt answer in the user's voice that would pair well with the photo.\n"
        "  * A brief coach_reasoning explaining why you picked this photo for this slot.\n"
        "- Also include a single-sentence overall_theme summarizing the vibe of the whole profile.\n\n"
        "Return ONLY a JSON object that matches the schema. Do not include any extra keys.\n\n"
        "Audited photos JSON:\n"
        f"{photos_json}"
    )

    client = _get_client()
    start_time = time.monotonic()

    try:
        # Use the vision_generate helper in text-only mode with an empty image list
        # so we can take advantage of responseSchema + JSON mime type.
        raw = await client.vision_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            base64_images=[],
            temperature=0.4,
            model=settings.gemini_model,
            max_output_tokens=4096,
            response_schema=PROFILE_BLUEPRINT_SCHEMA,
        )
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "profile_blueprint_llm_success",
            latency_ms=latency_ms,
            raw_length=len(raw),
        )
        parsed = json.loads(raw)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("profile_blueprint_gemini_failed", error=str(exc))
        raise ValueError("Failed to generate profile blueprint") from exc

    try:
        blueprint = ProfileBlueprint(**parsed)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "profile_blueprint_parse_failed",
            error=str(exc),
            raw_preview=str(parsed)[:500],
        )
        raise ValueError("Failed to parse profile blueprint response") from exc

    # Enrich slots with storage URLs derived from audited_photos.
    photos_by_id = {photo.id: photo for photo in photos}
    for slot in blueprint.slots:
        matching = photos_by_id.get(slot.photo_id)
        if not matching:
            # If LLM referenced a non-existent id, leave storage_url empty but log it.
            logger.warning(
                "profile_blueprint_missing_photo",
                photo_id=slot.photo_id,
                user_id=user_id,
            )
            continue
        # Build absolute URL so the Android app can render images directly.
        slot.storage_url = f"{settings.base_url}/static/{matching.storage_path}"

    return blueprint

