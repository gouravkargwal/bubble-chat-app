"""Service for generating an optimized dating profile blueprint from audited photos."""

import json
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import (
    AuditedPhoto,
    BlueprintSlot,
    BlueprintUniversalPrompt,
    ProfileBlueprint as ProfileBlueprintDB,
)
from app.llm.gemini_client import GeminiClient
from app.models.profile_optimizer import ProfileBlueprint
from app.schemas.profile_blueprint import ProfileBlueprintResponse

logger = structlog.get_logger()

# Allowlist guards against prompt injection via the lang query parameter.
ALLOWED_LANGS: frozenset[str] = frozenset(
    {
        "English",
        "Hindi",
        "Hinglish",
        "Gen-Z Slang",
        "Spanish",
        "French",
        "Portuguese",
        "Tamil",
        "Telugu",
    }
)

# Absolute maximum slots — kept in sync with the JSON schema and Pydantic model.
MAX_BLUEPRINT_SLOTS = 6

PROFILE_BLUEPRINT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "slots": {
            "type": "ARRAY",
            "minItems": 1,
            "maxItems": MAX_BLUEPRINT_SLOTS,
            "items": {
                "type": "OBJECT",
                "properties": {
                    "photo_id": {"type": "STRING"},
                    "slot_number": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": MAX_BLUEPRINT_SLOTS,
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


def _validate_lang(lang: str) -> str:
    """Return lang if it is in the allowlist, otherwise fall back to English.

    This prevents prompt injection via the lang query parameter.
    """
    if lang not in ALLOWED_LANGS:
        logger.warning("blueprint_lang_rejected", lang=lang)
        return "English"
    return lang


async def _fetch_top_audited_photos(
    user_id: str, db: AsyncSession
) -> list[AuditedPhoto]:
    """Fetch up to MAX_BLUEPRINT_SLOTS highest-scoring audited photos (score >= 6).

    The fetch limit is capped at MAX_BLUEPRINT_SLOTS so the LLM receives exactly
    as many photos as the schema allows slots — no schema/prompt contradiction.
    """
    result = await db.execute(
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user_id, AuditedPhoto.score >= 6)
        .order_by(AuditedPhoto.score.desc(), AuditedPhoto.created_at.desc())
        .limit(MAX_BLUEPRINT_SLOTS)
    )
    return list(result.scalars().all())


def _derive_image_url(storage_path: str) -> str:
    """Derive a full image URL from a storage path at read time.

    Deriving at read time (rather than baking in base_url at write time) means
    URL records stay valid across domain changes and CDN migrations.
    """
    return f"{settings.base_url.rstrip('/')}/static/{storage_path.lstrip('/')}"


def _build_blueprint_response(db_blueprint: ProfileBlueprintDB) -> ProfileBlueprintResponse:
    """Construct a ProfileBlueprintResponse from a fully-loaded ORM object.

    Expects db_blueprint.slots and db_blueprint.universal_prompts to be loaded
    (either via selectinload or because they were just added to the session).
    """
    slot_responses = sorted(
        [
            {
                "id": s.id,
                "photo_id": s.photo_id,
                "slot_number": s.slot_number,
                "role": s.role,
                "caption": s.caption,
                "universal_hook": s.universal_hook,
                "hinge_prompt": s.hinge_prompt,
                "aisle_prompt": s.aisle_prompt,
                # Re-derive from storage_path when available so the URL stays
                # fresh even if base_url has changed since the record was created.
                "image_url": (
                    _derive_image_url(s.storage_path)
                    if s.storage_path
                    else s.image_url
                ),
            }
            for s in db_blueprint.slots
        ],
        key=lambda x: x["slot_number"],
    )

    universal_prompts = (
        [
            {"category": up.category, "suggested_text": up.suggested_text}
            for up in db_blueprint.universal_prompts
        ]
        or None
    )

    return ProfileBlueprintResponse(
        id=db_blueprint.id,
        user_id=db_blueprint.user_id,
        overall_theme=db_blueprint.overall_theme,
        bio=db_blueprint.bio,
        created_at=db_blueprint.created_at,
        slots=slot_responses,
        universal_prompts=universal_prompts,
    )


async def generate_blueprint(
    user_id: str,
    db: AsyncSession,
    lang: str = "English",
    idempotency_key: str | None = None,
) -> ProfileBlueprintResponse:
    """Generate a ProfileBlueprint from a user's top audited photos using Gemini.

    If idempotency_key is provided and a blueprint with that key already exists,
    the existing blueprint is returned without calling the LLM again — protecting
    against double-charges on network retries or double-taps.

    The LLM receives up to MAX_BLUEPRINT_SLOTS previously audited photos and
    assigns each a slot number 1–N. The JSON response is validated against a
    strict schema and saved to DB within the caller's transaction.
    """
    # --- Idempotency check --------------------------------------------------
    if idempotency_key:
        existing_result = await db.execute(
            select(ProfileBlueprintDB)
            .where(ProfileBlueprintDB.idempotency_key == idempotency_key)
            .options(
                selectinload(ProfileBlueprintDB.slots),
                selectinload(ProfileBlueprintDB.universal_prompts),
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return _build_blueprint_response(existing)

    # --- Input validation ---------------------------------------------------
    lang = _validate_lang(lang)

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

    # --- LLM call -----------------------------------------------------------
    client = _get_client()

    try:
        raw = await client.vision_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            base64_images=[],
            temperature=0.4,
            model=settings.gemini_model,
            max_output_tokens=4096,
            response_schema=PROFILE_BLUEPRINT_SCHEMA,
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

    # --- Persist to DB (within caller's transaction) -----------------------
    photos_by_id = {photo.id: photo for photo in photos}

    db_blueprint = ProfileBlueprintDB(
        id=str(uuid.uuid4()),
        user_id=user_id,
        overall_theme=blueprint.overall_theme,
        bio=blueprint.bio,
        idempotency_key=idempotency_key,
    )
    db.add(db_blueprint)

    db_slots: list[BlueprintSlot] = []
    for slot in blueprint.slots:
        matching_photo = photos_by_id.get(slot.photo_id)
        if not matching_photo:
            # The LLM hallucinated a photo_id that was never sent — treat as a
            # hard error so the caller can rollback and refund quota.
            logger.warning(
                "blueprint_slot_unknown_photo",
                slot_photo_id=slot.photo_id,
                user_id=user_id,
                available_ids=list(photos_by_id.keys()),
            )
            raise ValueError(
                f"Blueprint references unknown photo '{slot.photo_id}'. "
                "Please try again."
            )

        db_slot = BlueprintSlot(
            id=str(uuid.uuid4()),
            blueprint_id=db_blueprint.id,
            photo_id=slot.photo_id,
            slot_number=slot.slot_number,
            role=slot.role,
            caption=slot.caption,
            universal_hook=slot.contextual_hook,
            hinge_prompt=slot.hinge_prompt,
            aisle_prompt=slot.aisle_prompt,
            coach_reasoning=slot.coach_reasoning,
            storage_path=matching_photo.storage_path,
            # image_url cached for backward compat; prefer deriving from storage_path at read time.
            image_url=_derive_image_url(matching_photo.storage_path),
        )
        db.add(db_slot)
        db_slots.append(db_slot)

    db_universal_prompts: list[BlueprintUniversalPrompt] = []
    for up in blueprint.universal_prompts:
        db_up = BlueprintUniversalPrompt(
            id=str(uuid.uuid4()),
            blueprint_id=db_blueprint.id,
            category=up.category,
            suggested_text=up.suggested_text,
        )
        db.add(db_up)
        db_universal_prompts.append(db_up)

    # Flush to validate DB constraints before we hand the response back.
    # We do NOT commit here — the caller controls the transaction so quota
    # and blueprint creation succeed or fail atomically.
    await db.flush()

    # Build response from in-memory objects — no extra DB round-trip needed.
    db_blueprint.slots = db_slots
    db_blueprint.universal_prompts = db_universal_prompts
    return _build_blueprint_response(db_blueprint)
