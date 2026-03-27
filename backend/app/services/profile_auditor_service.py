"""Service for brutally auditing dating profile photos using Gemini Vision.

Android clients already compress images before upload, so this service only
needs to base64-encode the received bytes and call Gemini with a strict schema.
"""

import base64
import hashlib
import json
import time
from typing import Sequence

import structlog
from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import AuditedPhoto, User
from app.infrastructure.oci_storage import upload as oci_upload
from app.llm.gemini_client import GeminiClient
from app.models.profile_auditor import AuditResponse, PhotoFeedback, PhotoTier

logger = structlog.get_logger()


def build_profile_audit_system_prompt(lang: str) -> str:
    """Shared by `analyze_profile_photos` and `audit_worker.process_audit_job`."""
    return (
        "You are an elite, cynical dating coach. Your goal is to be a gatekeeper. "
        "Most users have terrible photos; your job is to tell them the truth so they stop failing.\n\n"
        "STRICT SCORING CEILINGS (DO NOT EXCEED):\n"
        "* MAX 2/10: Bathroom/Gym/Elevator mirror selfies, messy rooms, or dirty mirrors.\n"
        "* MAX 3/10: Hiding the face (sunglasses, masks, hands, looking away), or blurry/pixelated.\n"
        "* MAX 4/10: Car selfies, bed selfies, or 'stiff' headshots with no personality.\n"
        "* MAX 5/10: Group shots where it is not 100% clear who the user is within 1 second.\n\n"
        "SCORING RUBRIC:\n"
        "* 1-3: Immediate Left Swipe. Low status, high cringe, or lazy.\n"
        "* 4-6: The 'Friend Zone'. Fine for Instagram, but invisible on dating apps.\n"
        "* 7-8: Solid. Shows face, lifestyle, and effort. Clear 'Right Swipe' territory.\n"
        "* 9-10: Elite. Professional quality, magnetic energy, high social proof.\n\n"
        f"LANGUAGE/DIALECT: {lang}\n"
        "* Use savage 2026 internet slang. If Hinglish, use 'Chhapri', 'Larka', 'Bhai'.\n"
        "* Use 'I' statements. Be the person swiping, not a robot checking boxes.\n\n"
        "ROAST SUMMARY (`roast_summary`):\n"
        "* One devastatingly honest sentence. No 'keep trying' or 'you have potential'. Just the raw vibe."
    )


def build_profile_audit_user_prompt(new_image_count: int) -> str:
    """Shared by `analyze_profile_photos` and `audit_worker.process_audit_job`."""
    return (
        f"Audit these {new_image_count} photos. "
        "Be a hater. If it isn't an 8/10, it's a failure.\n"
        f"* `total_analyzed` MUST be {new_image_count}.\n"
        f"* `photos`: exactly {new_image_count} objects, in the SAME ORDER as the images were sent (first image = first object).\n"
        f"* `photo_id` MUST be exactly `photo_1`, `photo_2`, ... `photo_{new_image_count}` only. "
        "Never use filenames, hashes, or invented labels.\n"
        "* `passed_count`: ONLY count photos with a score of 8 or higher.\n"
        "* `brutal_feedback`: 100% roast. Why does this photo kill their attraction?\n"
        "* BANNED WORDS: Do not use 'decent', 'acceptable', 'not bad', or 'okay'. If a photo is not an 8, it is a failure. Explain the failure with zero sugar-coating.\n"
        "* `improvement_tip`: Exactly what to change physically to make it a 9/10."
    )


PROFILE_AUDIT_SCHEMA: dict = {
    "type": "OBJECT",
    "properties": {
        "total_analyzed": {"type": "INTEGER"},
        "passed_count": {"type": "INTEGER"},
        "is_hard_reset": {
            "type": "BOOLEAN",
            "description": "True if passed_count is 0.",
        },
        "roast_summary": {
            "type": "STRING",
            "description": "A single savage sentence summarizing the user's overall dating vibe.",
        },
        "photos": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "photo_id": {
                        "type": "STRING",
                        "description": (
                            "Exactly photo_1 for the first image, photo_2 for the second, etc. "
                            "Same order as input. No filenames, hashes, or descriptive slugs."
                        ),
                    },
                    "score": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "brutal_feedback": {"type": "STRING"},
                    "improvement_tip": {"type": "STRING"},
                },
                "required": [
                    "photo_id",
                    "score",
                    "brutal_feedback",
                    "improvement_tip",
                ],
            },
        },
    },
    "required": [
        "total_analyzed",
        "passed_count",
        "is_hard_reset",
        "roast_summary",
        "photos",
    ],
}


def _score_to_tier(score: int) -> PhotoTier:
    """Deterministic score → tier mapping. Keeps tier consistent across runs."""
    if score >= 8:
        return PhotoTier.GOD_TIER
    if score >= 6:
        return PhotoTier.FILLER
    return PhotoTier.GRAVEYARD


_client: GeminiClient | None = None
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per image safety limit


def _get_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient(
            api_key=settings.gemini_api_key, default_model=settings.gemini_model
        )
    return _client


async def _encode_images(images: Sequence[UploadFile]) -> list[tuple[str, bytes, str]]:
    """Read and base64 encode uploaded images with size checks, keeping raw bytes and hash."""
    encoded: list[tuple[str, bytes, str]] = []
    for upload in images:
        data = await upload.read()
        if not data:
            continue
        if len(data) > MAX_FILE_SIZE:
            raise ValueError("Image exceeds 5MB limit.")
        # Calculate SHA-256 hash
        image_hash = hashlib.sha256(data).hexdigest()
        encoded.append((base64.b64encode(data).decode("utf-8"), data, image_hash))
    return encoded


async def analyze_profile_photos(
    images: list[UploadFile],
    user: User,
    db: AsyncSession,
    lang: str = "English",
    idempotency_key: str | None = None,
) -> AuditResponse:
    """Analyze up to 12 profile photos and return a brutal audit."""
    if not images:
        raise ValueError("At least one image is required for profile audit.")

    # Hard cap to 12 images at the service layer as well.
    images = images[:12]

    encoded_images = await _encode_images(images)
    base64_images = [b64 for b64, _, _ in encoded_images]
    image_hashes = [img_hash for _, _, img_hash in encoded_images]

    if not base64_images:
        raise ValueError("Failed to read any image data for profile audit.")

    # Check for duplicate images by hash
    existing_photos: dict[str, AuditedPhoto] = {}
    new_image_indices: list[int] = []
    new_base64_images: list[str] = []

    for idx, img_hash in enumerate(image_hashes):
        result = await db.execute(
            select(AuditedPhoto)
            .where(AuditedPhoto.user_id == user.id, AuditedPhoto.hash == img_hash)
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing_photos[img_hash] = existing
        else:
            new_image_indices.append(idx)
            new_base64_images.append(base64_images[idx])

    # If all images are duplicates, return cached results
    if not new_base64_images:
        cached_photos = []
        for img_hash in image_hashes:
            existing = existing_photos[img_hash]
            cached_photos.append(
                PhotoFeedback(
                    photo_id=f"photo_{image_hashes.index(img_hash) + 1}",
                    score=existing.score,
                    tier=existing.tier,
                    brutal_feedback=existing.brutal_feedback,
                    improvement_tip=existing.improvement_tip,
                )
            )

        # Use roast line from the most recent matching photo if available.
        latest_existing = list(existing_photos.values())[-1]
        logger.info(
            "profile_audit_llm_skipped_cached_only",
            user_id=str(user.id),
            idempotency_key=idempotency_key,
            total_analyzed=len(image_hashes),
        )
        return AuditResponse(
            total_analyzed=len(image_hashes),
            passed_count=sum(1 for p in cached_photos if p.tier == "GOD_TIER"),
            is_hard_reset=all(p.tier == "GRAVEYARD" for p in cached_photos),
            roast_summary=latest_existing.roast_summary,
            photos=cached_photos,
        )

    # Only call Gemini for new images
    new_image_count = len(new_base64_images)
    system_prompt = build_profile_audit_system_prompt(lang)
    user_prompt = build_profile_audit_user_prompt(new_image_count)

    client = _get_client()

    logger.info(
        "profile_audit_llm_input",
        user_id=str(user.id),
        lang=lang,
        idempotency_key=idempotency_key,
        new_image_count=new_image_count,
        total_uploaded=len(image_hashes),
        base64_payload_chars_total=sum(len(b) for b in new_base64_images),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    try:
        raw = await client.vision_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            base64_images=new_base64_images,
            temperature=0.0,
            model=settings.gemini_model,
            max_output_tokens=8192,
            response_schema=PROFILE_AUDIT_SCHEMA,
        )
        logger.info(
            "profile_audit_llm_output",
            user_id=str(user.id),
            idempotency_key=idempotency_key,
            raw_chars=len(raw),
            raw=raw,
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(
            "profile_audit_gemini_failed",
            error=str(e),
            raw_preview=str(raw)[:500] if "raw" in locals() else "N/A",
        )
        raise ValueError("Failed to audit profile photos") from e

    # Parse JSON response
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(
            "profile_audit_json_parse_failed",
            error=str(e),
            raw_preview=str(raw)[:500],
        )
        raise ValueError("Failed to parse JSON response from AI") from e

    # Parse and validate Pydantic model
    try:
        new_parsed_response = AuditResponse(**parsed)
        for photo in new_parsed_response.photos:
            photo.tier = _score_to_tier(photo.score)
    except ValidationError as e:
        logger.error(
            "profile_audit_pydantic_validation_failed",
            error=str(e),
            error_type=type(e).__name__,
            raw_preview=str(parsed)[:500],
        )
        raise ValueError("Failed to validate audit response structure") from e
    except Exception as e:
        logger.error(
            "profile_audit_parse_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
            raw_preview=str(parsed)[:500] if "parsed" in locals() else "N/A",
        )
        raise ValueError("Failed to parse audit response") from e

    # Merge cached and new results
    all_photos = []
    photo_idx = 0
    for idx, img_hash in enumerate(image_hashes):
        if img_hash in existing_photos:
            # Use cached result
            existing = existing_photos[img_hash]
            all_photos.append(
                PhotoFeedback(
                    photo_id=f"photo_{idx + 1}",
                    score=existing.score,
                    tier=existing.tier,
                    brutal_feedback=existing.brutal_feedback,
                    improvement_tip=existing.improvement_tip,
                )
            )
        else:
            # Use new result (map back to original index)
            new_photo = new_parsed_response.photos[photo_idx]
            all_photos.append(
                PhotoFeedback(
                    photo_id=f"photo_{idx + 1}",
                    score=new_photo.score,
                    tier=_score_to_tier(new_photo.score),
                    brutal_feedback=new_photo.brutal_feedback,
                    improvement_tip=new_photo.improvement_tip,
                )
            )
            photo_idx += 1

    parsed_response = AuditResponse(
        total_analyzed=len(image_hashes),
        passed_count=sum(1 for p in all_photos if p.tier == "GOD_TIER"),
        is_hard_reset=all(p.tier == "GRAVEYARD" for p in all_photos),
        roast_summary=new_parsed_response.roast_summary,
        photos=all_photos,
    )

    # Persist audit results and images to OCI Object Storage
    photo_idx = 0
    for idx, img_hash in enumerate(image_hashes):
        if img_hash in existing_photos:
            continue

        try:
            original_idx = new_image_indices[photo_idx]
            _, raw_bytes, _ = encoded_images[original_idx]

            photo_feedback = None
            for pf in parsed_response.photos:
                if pf.photo_id == f"photo_{idx + 1}":
                    photo_feedback = pf
                    break

            if not photo_feedback:
                photo_idx += 1
                continue

            filename = f"{photo_feedback.photo_id}_{int(time.time() * 1000)}.jpg"
            object_key = f"audits/{user.id}/{filename}"
            await oci_upload(object_key, raw_bytes, content_type="image/jpeg")

            db.add(
                AuditedPhoto(
                    user_id=user.id,
                    storage_path=object_key,
                    hash=img_hash,
                    score=photo_feedback.score,
                    tier=photo_feedback.tier,
                    brutal_feedback=photo_feedback.brutal_feedback,
                    improvement_tip=photo_feedback.improvement_tip,
                    roast_summary=new_parsed_response.roast_summary,
                    idempotency_key=idempotency_key,
                )
            )
            photo_idx += 1
        except (IndexError, ValueError) as e:
            logger.warning("profile_audit_save_skip", error=str(e), idx=idx)
            continue

    return parsed_response
