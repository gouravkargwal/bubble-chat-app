"""Service for generating an optimized dating profile blueprint from audited photos."""

import json
import time
from typing import Any

import structlog
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import (
    AuditedPhoto,
    BlueprintSlot,
    ProfileBlueprint as ProfileBlueprintDB,
)
from app.llm.gemini_client import GeminiClient
from app.models.profile_optimizer import ProfileBlueprint
from app.schemas.profile_blueprint import ProfileBlueprintResponse

logger = structlog.get_logger()


PROFILE_BLUEPRINT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "slots": {
            "type": "ARRAY",
            "minItems": 1,
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
                    "contextual_hook": {"type": "STRING"},
                    "hinge_prompt": {"type": "STRING"},
                    "aisle_prompt": {"type": "STRING"},
                    "coach_reasoning": {"type": "STRING"},
                },
                "required": [
                    "photo_id",
                    "slot_number",
                    "role",
                    "caption",
                    "contextual_hook",
                    "hinge_prompt",
                    "aisle_prompt",
                    "coach_reasoning",
                ],
            },
        },
        "overall_theme": {"type": "STRING"},
        "bio": {
            "type": "STRING",
            "maxLength": 500,
        },
        "universal_prompts": {
            "type": "ARRAY",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "OBJECT",
                "properties": {
                    "category": {"type": "STRING"},
                    "suggested_text": {"type": "STRING"},
                },
                "required": ["category", "suggested_text"],
            },
        },
    },
    "required": [
        "slots",
        "overall_theme",
        "bio",
        "universal_prompts",
    ],
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


async def _fetch_top_audited_photos(
    user_id: str, db: AsyncSession
) -> list[AuditedPhoto]:
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


async def generate_blueprint(
    user_id: str,
    db: AsyncSession,
    lang: str = "English",
) -> ProfileBlueprintResponse:
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

    available_count = len(photos)
    system_prompt = (
        "You are now a Cross-Platform Rizz Architect. Your job is to design a dating profile system that "
        "works across Tinder, Bumble, Hinge, and Aisle — not just one app.\n\n"
        "You MUST respond with JSON that strictly matches the provided JSON schema. "
        "Do not include any commentary outside of the JSON.\n\n"
        f"IMPORTANT: Provide all captions, hooks, bios, prompts, and any other text in the following "
        f"language or dialect: {lang}.\n"
        "If the language is 'Hinglish', use a mix of Hindi and English in Latin script and lean extra sassy/savage.\n"
        "If it is 'Gen-Z Slang', use modern internet slang and TikTok-era phrasing.\n"
        "Always match the cultural tone and norms of the requested language/dialect."
    )

    user_prompt = (
        "You are given a JSON array of previously audited dating profile photos.\n"
        "- Each object has fields: id, score (1-10), tier (GOD_TIER / FILLER / GRAVEYARD), "
        "and brutal_feedback written by another coach.\n"
        f"- You have exactly {available_count} photo(s). Use ALL of them — one slot per photo, no repeats.\n"
        f"- `slot_number` must be 1 through {available_count} with no gaps or duplicates.\n"
        "- Slot 1 MUST be the single best clear face shot for first impression.\n"
        "- Optimize for status, charisma, social proof, and variety of settings while avoiding try-hard energy.\n"
        "- Use the brutal_feedback notes as context but feel free to disagree if you have a better framing.\n"
        "- For each photo, write:\n"
        "  * `caption`: A short, high-status caption to sit under the photo.\n"
        "  * `contextual_hook`: A short hook label for this photo (e.g. 'Parent Approval', 'Adventure Flex').\n"
        "  * `hinge_prompt`: A ready-to-paste Hinge prompt answer inspired by this photo (max 150 chars). "
        "Make it conversational and invite a reply. Include the prompt question and answer, e.g. "
        "'My most controversial opinion → Brunch is just breakfast for people who overslept.'\n"
        "  * `aisle_prompt`: A ready-to-paste Aisle prompt answer for this photo. "
        "Aisle is relationship-focused — be warm, genuine, show depth. "
        "e.g. 'A story behind this photo → Solo trip to Kyoto. Came back knowing I want someone to share the next one with.'\n"
        "  * `coach_reasoning`: Brief explanation of why this photo gets this slot.\n"
        "- Also include:\n"
        "  * `overall_theme`: one sentence summarizing the vibe of the whole profile.\n"
        "  * `bio`: a single punchy bio (max 500 chars) that works across Tinder, Bumble, Hinge, and Aisle. "
        "Blend 2-3 specific fun facts with a confident, low-investment tone. No cringe, no desperation.\n"
        "  * `universal_prompts`: exactly 3 hook objects usable on ANY app. Each has:\n"
        "      - `category`: short label (e.g. 'Parent Approval', 'Low-Key Flex', 'Wingman Energy').\n"
        "      - `suggested_text`: concrete text ready to paste into any prompt field.\n\n"
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
        logger.debug(
            "profile_blueprint_llm_raw",
            latency_ms=latency_ms,
            raw_preview=str(raw)[:1000],
            lang=lang,
            user_id=user_id,
        )
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
        logger.info(
            "profile_blueprint_parsed",
            user_id=user_id,
            lang=lang,
            slots=len(blueprint.slots),
            overall_theme=blueprint.overall_theme[:120],
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "profile_blueprint_parse_failed",
            error=str(exc),
            raw_preview=str(parsed)[:500],
        )
        raise ValueError("Failed to parse profile blueprint response") from exc

    # Build lookup map for storage URL construction
    photos_by_id = {photo.id: photo for photo in photos}

    # Save to database
    db_blueprint = ProfileBlueprintDB(
        user_id=user_id,
        overall_theme=blueprint.overall_theme,
        bio=blueprint.bio,
    )
    db.add(db_blueprint)
    await db.flush()  # Flush to get the blueprint.id

    # Create BlueprintSlot records (store image_url so history is recreatable even if photo is deleted)
    for slot in blueprint.slots:
        matching_photo = photos_by_id.get(slot.photo_id)
        if not matching_photo:
            continue  # Skip invalid photo references

        stored_image_url = f"{settings.base_url.rstrip('/')}/static/{matching_photo.storage_path.lstrip('/')}"
        db_slot = BlueprintSlot(
            blueprint_id=db_blueprint.id,
            photo_id=slot.photo_id,
            slot_number=slot.slot_number,
            role=slot.role,
            caption=slot.caption,
            universal_hook=slot.contextual_hook,
            hinge_prompt=slot.hinge_prompt,
            aisle_prompt=slot.aisle_prompt,
            image_url=stored_image_url,
        )
        db.add(db_slot)

    await db.commit()

    # Reload blueprint with slots relationship
    result = await db.execute(
        select(ProfileBlueprintDB)
        .where(ProfileBlueprintDB.id == db_blueprint.id)
        .options(selectinload(ProfileBlueprintDB.slots))
    )
    db_blueprint = result.scalar_one()

    # Build response schema (excludes coach_reasoning and other internal fields)
    slot_responses = []
    for db_slot in db_blueprint.slots:
        slot_responses.append(
            {
                "id": db_slot.id,
                "photo_id": db_slot.photo_id,
                "slot_number": db_slot.slot_number,
                "role": db_slot.role,
                "caption": db_slot.caption,
                "universal_hook": db_slot.universal_hook,
                "hinge_prompt": db_slot.hinge_prompt,
                "aisle_prompt": db_slot.aisle_prompt,
                "image_url": db_slot.image_url,
            }
        )

    # Sort slots by slot_number
    slot_responses.sort(key=lambda x: x["slot_number"])

    # Include universal_prompts from the LLM response (not saved to DB)
    universal_prompts_response = None
    if blueprint.universal_prompts:
        universal_prompts_response = [
            {"category": prompt.category, "suggested_text": prompt.suggested_text}
            for prompt in blueprint.universal_prompts
        ]

    return ProfileBlueprintResponse(
        id=db_blueprint.id,
        user_id=db_blueprint.user_id,
        overall_theme=db_blueprint.overall_theme,
        bio=db_blueprint.bio,
        created_at=db_blueprint.created_at,
        slots=slot_responses,
        universal_prompts=universal_prompts_response,
    )
