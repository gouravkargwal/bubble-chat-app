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


PROFILE_AUDIT_SCHEMA: dict = {
    "type": "OBJECT",
    "properties": {
        "total_analyzed": {"type": "INTEGER"},
        "passed_count": {"type": "INTEGER"},
        "is_hard_reset": {
            "type": "BOOLEAN",
            "description": "True if passed_count is 0.",
        },
        "archetype_title": {
            "type": "STRING",
            "description": "A bold, 2-4 word dating archetype title (e.g., 'The Corporate NPC').",
        },
        "roast_summary": {
            "type": "STRING",
            "description": "A single savage sentence summarizing the user's overall dating vibe.",
        },
        "share_card_color": {
            "type": "STRING",
            "description": "Hex color code (e.g., #FF0055) that matches the overall archetype vibe.",
        },
        "photos": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "photo_id": {"type": "STRING"},
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
        "archetype_title",
        "roast_summary",
        "share_card_color",
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

    logger.info("profile_audit_started", image_count=len(base64_images))
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
            logger.info(
                "profile_audit_duplicate_found",
                photo_id=existing.id,
                hash=img_hash[:16],
            )
        else:
            new_image_indices.append(idx)
            new_base64_images.append(base64_images[idx])

    # If all images are duplicates, return cached results
    if not new_base64_images:
        logger.info("profile_audit_all_duplicates", total_images=len(image_hashes))

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

        # Use archetype/roast metadata from the most recent matching photo if available.
        # This keeps the viral share-card experience consistent for duplicate uploads.
        latest_existing = list(existing_photos.values())[-1]
        return AuditResponse(
            total_analyzed=len(image_hashes),
            passed_count=sum(1 for p in cached_photos if p.tier == "GOD_TIER"),
            is_hard_reset=all(p.tier == "GRAVEYARD" for p in cached_photos),
            archetype_title=latest_existing.archetype_title,
            roast_summary=latest_existing.roast_summary,
            share_card_color=latest_existing.share_card_color,
            photos=cached_photos,
        )

    # Only call Gemini for new images
    system_prompt = (
        "You are a brutally honest, elite dating profile auditor speaking in first person.\n"
        "Your job is to protect the user from looking desperate or cringey.\n"
        'Always use \'I\' statements (e.g. "I would swipe right...", "I can\'t see your face here...").\n'
        "Evaluate each photo across four axes: Vibe, Lighting, Grooming, and Background.\n"
        "- Vibe: body language, expression, confidence, try-hard vs relaxed.\n"
        "- Lighting: natural vs harsh, shadows, blown-out highlights.\n"
        "- Grooming: clothes, hair, hygiene, overall put-together-ness.\n"
        "- Background: clutter, bathroom mirrors, messy rooms, distracting objects.\n"
        "Be specific and visual in your feedback (e.g. \"You look like you're hiding from the sun in a basement. "
        'Get some natural light and stand up straight."), not generic checklists.\n'
        "Output must match the JSON schema exactly. Do NOT be polite. Give brutal, actionable feedback.\n\n"
        f"IMPORTANT: Generate all feedback, score explanations, and improvement tips in the following "
        f"language or dialect: {lang}.\n"
        "If the language is 'Hinglish', use the Latin script and include Indian slang like 'Bhai', 'Mast', "
        "'Cringe', or 'Chhapri' where it naturally fits the roast.\n"
        "If it is 'Gen-Z Slang', use modern internet slang and TikTok-era phrasing.\n"
        "Always match the cultural tone and norms of the requested language/dialect.\n\n"
        "THE ROAST MASTER PROTOCOL\n"
        "After analyzing the photos, you must categorize the user into a single overall DATING ARCHETYPE.\n"
        "Tone: 8/10 Savage. Be brutally honest, funny, and use 2026 internet subcultures "
        "(e.g., 'LinkedIn-maxing', 'Beige Flag Final Boss', 'Gym-Mirror Philosopher').\n"
        "Humor over politeness: the goal is to make the user laugh or feel called out enough to share this "
        "on social media.\n"
        "Archetype logic examples (use them as inspiration, not a strict list):\n"
        "- High effort but cringey posing or over-editing → label them some version of a 'Try-Hard'.\n"
        "- Zero effort, blurry pics, or chaotic lighting → label them some version of 'Witness Protection Program'.\n"
        "- Mostly or only gym shots → label them some version of 'Protein-Shake Narcissus' or 'Gym-Mirror Philosopher'.\n"
        "If the photos are genuinely excellent across the board, the archetype should feel like a "
        "'Backhanded Compliment' (e.g., 'The Ego Trip', 'Main Character Energy').\n"
        "ARACHETYPE_TITLE RULES:\n"
        "- Must be a bold, 2-4 word title (e.g., 'The Corporate NPC', 'Red Flag Legend', 'The Main Character').\n"
        "- Lean into meme-able, shareable phrasing.\n"
        "ROAST_SUMMARY RULES:\n"
        '- Write a single, punchy sentence that would make an influencer\'s audience go "OOF".\n'
        "- 8/10 savage, but still playful and entertaining, not bullying.\n"
        "SHARE_CARD_COLOR RULES:\n"
        "- Return a single hex color code (e.g., #FF0055) that matches the overall vibe.\n"
        "- Examples: neon red for chaotic red-flag energy, gold for 'unintentional rizz', cold blue for "
        "LinkedIn-maxxing energy, pastel for beige flag vibes.\n\n"
        "Score each photo on a strict 1-10 integer scale using this rubric:\n"
        "  1-3: Face not visible, blurry, heavy filter, or group shot where subject is unclear.\n"
        "  4-5: Visible face but poor lighting, bad background, unflattering angle, or low effort.\n"
        "  6-7: Acceptable photo — decent lighting and background, presentable but nothing stands out.\n"
        "  8-9: Strong photo — good lighting, clear face, confident body language, clean background.\n"
        "  10: Exceptional — professional feel, magnetic presence, would make anyone stop scrolling.\n"
        "Apply this rubric consistently. Do NOT output a tier field — only output the score."
    )

    new_image_count = len(new_base64_images)
    user_prompt = (
        f"I am sending you exactly {new_image_count} dating profile photos.\n"
        "Audit these photos in the order they are provided.\n"
        "Return a JSON object that strictly matches the given schema.\n"
        f"- `total_analyzed` MUST be {new_image_count}.\n"
        "- The `photos` array MUST contain exactly one object per input image: no more, no fewer.\n"
        "- Use `photo_id` values 'photo_1', 'photo_2', ..., in the same order as the images.\n"
        "- Do NOT invent extra photos, do NOT skip any, and do NOT reuse IDs.\n"
        "- `passed_count` should equal the number of photos you would actually recommend keeping on a profile.\n"
        "Focus your text on Vibe, Lighting, Grooming, and Background for each photo."
    )

    client = _get_client()
    start_time = time.monotonic()

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
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "profile_audit_llm_success",
            latency_ms=latency_ms,
            raw_length=len(raw),
            new_images=new_image_count,
            cached_images=len(existing_photos),
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
        archetype_title=new_parsed_response.archetype_title,
        roast_summary=new_parsed_response.roast_summary,
        share_card_color=new_parsed_response.share_card_color,
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
                    archetype_title=new_parsed_response.archetype_title,
                    roast_summary=new_parsed_response.roast_summary,
                    share_card_color=new_parsed_response.share_card_color,
                    idempotency_key=idempotency_key,
                )
            )
            photo_idx += 1
        except (IndexError, ValueError) as e:
            logger.warning("profile_audit_save_skip", error=str(e), idx=idx)
            continue

    score_summary = [
        {"id": p.photo_id, "score": p.score, "tier": p.tier}
        for p in parsed_response.photos
    ]
    logger.info(
        "profile_audit_complete",
        total=parsed_response.total_analyzed,
        passed=parsed_response.passed_count,
        is_hard_reset=parsed_response.is_hard_reset,
        scores=score_summary,
    )
    return parsed_response
