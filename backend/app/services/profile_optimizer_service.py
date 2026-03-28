"""Service for generating an optimized dating profile blueprint from audited photos."""

import asyncio
import json
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.oci_storage import get_signed_url as oci_get_signed_url
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
    """Fetch up to MAX_BLUEPRINT_SLOTS audited photos (score >= 6) for blueprint generation.

    Prefer **most recently persisted** audits first, then higher score within the same
    recency window. This keeps Optimize aligned with the user's latest audit batch after
    deletes or new runs, instead of resurrecting old high-score rows from earlier sessions.
    """
    result = await db.execute(
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user_id, AuditedPhoto.score >= 6)
        .order_by(AuditedPhoto.created_at.desc(), AuditedPhoto.score.desc())
        .limit(MAX_BLUEPRINT_SLOTS)
    )
    return list(result.scalars().all())


def _derive_image_url(storage_path: str) -> str:
    """Derive a legacy static URL (used only when persisting slot rows).

    Audited photos live in OCI; API responses use signed URLs via
    ``_resolve_slot_image_url`` instead of this path.
    """
    return f"{settings.base_url.rstrip('/')}/static/{storage_path.lstrip('/')}"


async def _resolve_slot_image_url(slot: BlueprintSlot) -> str:
    """Return a client-loadable URL for the slot photo (OCI PAR, same as audit history)."""
    if not slot.storage_path:
        return slot.image_url or ""
    try:
        return await oci_get_signed_url(slot.storage_path)
    except Exception as exc:  # pragma: no cover - OCI/network
        logger.warning(
            "blueprint_slot_signed_url_failed",
            slot_id=slot.id,
            error=str(exc)[:200],
        )
        return slot.image_url or ""


async def build_blueprint_response(
    db_blueprint: ProfileBlueprintDB,
    *,
    slots: list[BlueprintSlot] | None = None,
    universal_prompts: list[BlueprintUniversalPrompt] | None = None,
) -> ProfileBlueprintResponse:
    """Construct a ProfileBlueprintResponse from a fully-loaded ORM object.

    Pass ``slots`` / ``universal_prompts`` when building right after insert so we
    never touch lazy-loaded relationships in the async session. Otherwise expects
    relationships loaded via selectinload (e.g. list/idempotency paths).
    """
    slot_models = slots if slots is not None else db_blueprint.slots
    up_models = (
        universal_prompts
        if universal_prompts is not None
        else db_blueprint.universal_prompts
    )

    slot_dicts = await asyncio.gather(*[_slot_dict_async(s) for s in slot_models])
    slot_responses = sorted(slot_dicts, key=lambda x: x["slot_number"])

    universal_prompts_out = [
        {"category": up.category, "suggested_text": up.suggested_text}
        for up in up_models
    ] or None

    return ProfileBlueprintResponse(
        id=db_blueprint.id,
        user_id=db_blueprint.user_id,
        overall_theme=db_blueprint.overall_theme,
        bio=db_blueprint.bio,
        created_at=db_blueprint.created_at,
        slots=slot_responses,
        universal_prompts=universal_prompts_out,
    )


async def _slot_dict_async(s: BlueprintSlot) -> dict[str, Any]:
    image_url = await _resolve_slot_image_url(s)
    return {
        "id": s.id,
        "photo_id": s.photo_id,
        "slot_number": s.slot_number,
        "role": s.role,
        "caption": s.caption,
        "universal_hook": s.universal_hook,
        "hinge_prompt": s.hinge_prompt,
        "aisle_prompt": s.aisle_prompt,
        "image_url": image_url,
    }


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
            logger.info(
                "profile_blueprint_llm_skipped_idempotent",
                user_id=user_id,
                idempotency_key=idempotency_key,
                blueprint_id=existing.id,
            )
            return await build_blueprint_response(existing)

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
        "You are an elite Cross-Platform Dating Profile Architect (Tinder, Bumble, Hinge, Aisle).\n"
        f"DIALECT ENFORCEMENT: The requested language/dialect is {lang}. You MUST write the `caption`, `hinge_prompt`, `aisle_prompt`, `bio`, and `universal_prompts` entirely in this exact dialect.\n"
        "* If Hinglish: Weave Romanized Hindi into EVERY single sentence (e.g., yaar, bhai, matlab, samajh, waisa, bilkul, desi). ZERO purely standard-English sentences are allowed. If a generated prompt can be read naturally by an American, you failed.\n"
        "* If Gen-Z Slang: Use modern TikTok-era phrasing.\n"
        "* Match cultural tone exactly. Never use corporate or AI-sounding filler."
    )

    user_prompt = (
        "CRITICAL CONSTRAINT:\n"
        "* You CANNOT see the photos. This call includes no image pixels — only the JSON metadata below.\n"
        "* You MUST rely entirely on each entry's `score`, `tier`, and `brutal_feedback`. Do not invent faces, poses, lighting, outfits, or settings you were not told about.\n"
        "* Any copy must be grounded in those fields only; never hallucinate visual facts.\n\n"
        f"Design a dating profile blueprint using these {available_count} audited photos.\n\n"
        "RULES:\n"
        f"* Use ALL {available_count} photos. `slot_number` MUST be 1 to {available_count} (no gaps/repeats).\n"
        "* `photo_id`: For every slot, set `photo_id` to the EXACT `id` string copied verbatim from one object in AUDITED PHOTOS JSON below. Do NOT invent, truncate, reformat, or guess IDs — only the provided UUID strings are valid. Each listed `id` must appear exactly once across slots.\n"
        "* Slot 1 (`slot_number` 1): Assign to the photo with the highest `score`. If multiple photos share the top score, pick the one whose `brutal_feedback` best indicates an attractive, clear-face, or strong first-impression shot (infer only from that text, not from imagined images).\n"
        "* Vibe: High-status, charismatic, social proof. No try-hard/desperate energy.\n"
        '* Context: Use `brutal_feedback` as creative fuel — spin it into confident, playful framing in captions and prompts; do not fabricate a "better angle" you cannot see.\n\n'
        "SLOT REQUIREMENTS:\n"
        "* `caption`: Short, high-status.\n"
        "* `contextual_hook`: Short label (e.g., 'Parent Approval', 'Adventure Flex').\n"
        "* `hinge_prompt`: Ready-to-paste, conversational (max 150 chars). Include prompt + answer (e.g., 'My most controversial opinion → Brunch is just breakfast for people who overslept.').\n"
        "* `aisle_prompt`: Ready-to-paste, relationship-focused. Warm, genuine, showing depth.\n"
        "* `coach_reasoning`: Brief explanation for this slot choice.\n\n"
        "GLOBAL REQUIREMENTS:\n"
        "* `overall_theme`: 1-sentence vibe summary.\n"
        "* `bio`: Punchy cross-platform bio (max 500 chars). Blend 2-3 specific fun facts with a confident, low-investment tone.\n"
        "* `universal_prompts`: Exactly 3 hooks usable on ANY app. Each needs a `category` (e.g., 'Low-Key Flex') and concrete `suggested_text`.\n\n"
        "AUDITED PHOTOS JSON:\n"
        f"{photos_json}"
    )

    # --- LLM call -----------------------------------------------------------
    client = _get_client()

    logger.info(
        "profile_blueprint_llm_input",
        user_id=user_id,
        lang=lang,
        idempotency_key=idempotency_key,
        available_count=available_count,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

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
        logger.info(
            "profile_blueprint_llm_output",
            user_id=user_id,
            idempotency_key=idempotency_key,
            raw_chars=len(raw),
            raw=raw,
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
    # Server-generated columns (e.g. created_at) are not present on the instance
    # until refreshed; accessing them triggers implicit IO and MissingGreenlet
    # under AsyncSession.
    await db.refresh(db_blueprint, attribute_names=["created_at"])

    return await build_blueprint_response(
        db_blueprint,
        slots=db_slots,
        universal_prompts=db_universal_prompts,
    )
