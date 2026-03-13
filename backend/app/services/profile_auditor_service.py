"""Service for brutally auditing dating profile photos using Gemini Vision.

Android clients already compress images before upload, so this service only
needs to base64-encode the received bytes and call Gemini with a strict schema.
"""

import base64
import json
import time
from pathlib import Path
from typing import Sequence

import structlog
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import AuditedPhoto, User
from app.llm.gemini_client import GeminiClient
from app.models.profile_auditor import AuditResponse

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
                    "tier": {
                        "type": "STRING",
                        "enum": ["GOD_TIER", "FILLER", "GRAVEYARD"],
                    },
                    "brutal_feedback": {"type": "STRING"},
                    "improvement_tip": {"type": "STRING"},
                },
                "required": [
                    "photo_id",
                    "score",
                    "tier",
                    "brutal_feedback",
                    "improvement_tip",
                ],
            },
        },
    },
    "required": ["total_analyzed", "passed_count", "is_hard_reset", "photos"],
}


_client: GeminiClient | None = None
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per image safety limit
STATIC_ROOT = Path("static")


def _get_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient(
            api_key=settings.gemini_api_key, default_model=settings.gemini_model
        )
    return _client


async def _encode_images(images: Sequence[UploadFile]) -> list[tuple[str, bytes]]:
    """Read and base64 encode uploaded images with size checks, keeping raw bytes."""
    encoded: list[tuple[str, bytes]] = []
    for upload in images:
        data = await upload.read()
        if not data:
            continue
        if len(data) > MAX_FILE_SIZE:
            raise ValueError("Image exceeds 5MB limit.")
        encoded.append((base64.b64encode(data).decode("utf-8"), data))
    return encoded


async def analyze_profile_photos(
    images: list[UploadFile],
    user: User,
    db: AsyncSession,
) -> AuditResponse:
    """Analyze up to 12 profile photos and return a brutal audit."""
    if not images:
        raise ValueError("At least one image is required for profile audit.")

    # Hard cap to 12 images at the service layer as well.
    images = images[:12]

    encoded_images = await _encode_images(images)
    base64_images = [b64 for b64, _ in encoded_images]
    logger.info("profile_audit_started", image_count=len(base64_images))
    if not base64_images:
        raise ValueError("Failed to read any image data for profile audit.")

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
        "Output must match the JSON schema exactly. Do NOT be polite. Give brutal, actionable feedback."
    )

    image_count = len(base64_images)
    user_prompt = (
        f"I am sending you exactly {image_count} dating profile photos.\n"
        "Audit these photos in the order they are provided.\n"
        "Return a JSON object that strictly matches the given schema.\n"
        f"- `total_analyzed` MUST be {image_count}.\n"
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
            base64_images=base64_images,
            temperature=0.2,
            model=settings.gemini_model,
            max_output_tokens=8192,
            response_schema=PROFILE_AUDIT_SCHEMA,
        )
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "profile_audit_llm_success",
            latency_ms=latency_ms,
            raw_length=len(raw),
        )
        parsed = json.loads(raw)
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error("profile_audit_gemini_failed", error=str(e))
        raise ValueError("Failed to audit profile photos") from e

    try:
        parsed_response = AuditResponse(**parsed)

        # Persist audit results and images for history viewing
        STATIC_ROOT.mkdir(parents=True, exist_ok=True)
        audits_root = STATIC_ROOT / "audits" / user.id
        audits_root.mkdir(parents=True, exist_ok=True)

        for photo_feedback in parsed_response.photos:
            # Map photo_id like "photo_1" back to the original image bytes
            try:
                idx = int(str(photo_feedback.photo_id).replace("photo_", "")) - 1
            except ValueError:
                continue
            if idx < 0 or idx >= len(encoded_images):
                continue

            _, raw_bytes = encoded_images[idx]
            filename = f"{photo_feedback.photo_id}_{int(time.time() * 1000)}.jpg"
            storage_rel_path = f"audits/{user.id}/{filename}"
            file_path = STATIC_ROOT / storage_rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(raw_bytes)

            db.add(
                AuditedPhoto(
                    user_id=user.id,
                    storage_path=storage_rel_path,
                    score=photo_feedback.score,
                    tier=photo_feedback.tier,
                    brutal_feedback=photo_feedback.brutal_feedback,
                    improvement_tip=photo_feedback.improvement_tip,
                )
            )

        await db.commit()

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
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(
            "profile_audit_parse_failed",
            error=str(e),
            raw_preview=str(parsed)[:500],
        )
        raise ValueError("Failed to parse profile audit response") from e
