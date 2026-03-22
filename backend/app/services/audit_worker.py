"""Background worker for async profile audit processing.

Runs as a FastAPI BackgroundTask. Reads raw image bytes from OCI temp storage,
calls Gemini Vision, persists results, and updates the AuditJob row so the
SSE / polling endpoints can stream progress to the client.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time

import structlog
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.engine import async_session
from app.infrastructure.database.models import AuditedPhoto, AuditJob
from app.infrastructure.oci_storage import (
    get_bytes as oci_get_bytes,
    upload as oci_upload,
    delete as oci_delete,
)
from app.llm.gemini_client import GeminiClient
from app.models.profile_auditor import AuditResponse, PhotoFeedback, PhotoTier
from app.services.profile_auditor_service import (
    MAX_FILE_SIZE,
    PROFILE_AUDIT_SCHEMA,
    _score_to_tier,
)

logger = structlog.get_logger(__name__)

_client: GeminiClient | None = None


def _get_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient(
            api_key=settings.gemini_api_key, default_model=settings.gemini_model
        )
    return _client


def _safe_error(exc: Exception, max_len: int = 200) -> str:
    """Extract a short, stable error message from an exception.

    OCI ServiceError payloads can be enormous; we log the full body
    server-side and only persist a truncated, user-safe string in the DB.
    """
    try:
        from oci.exceptions import ServiceError  # type: ignore[import-untyped]

        if isinstance(exc, ServiceError):
            return f"OCI {exc.status}: {exc.code or 'unknown'}"[:max_len]
    except ImportError:
        pass
    msg = str(exc)
    return msg[:max_len] if len(msg) > max_len else msg


async def _update_job(db: AsyncSession, job_id: str, **kwargs) -> None:
    """Update an AuditJob row with the given fields."""
    result = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
    job = result.scalar_one_or_none()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        await db.commit()


async def process_audit_job(job_id: str, image_keys: list[str]) -> None:
    """Process a queued audit job.  Called from BackgroundTasks.

    1. Read images from temp OCI storage
    2. Check dedup hashes
    3. Call Gemini for new images
    4. Persist AuditedPhoto rows + final images to OCI
    5. Update AuditJob with result JSON
    6. Clean up temp images
    """
    async with async_session() as db:
        try:
            # Load the job
            result = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error("audit_worker_job_not_found", job_id=job_id)
                return

            user_id = job.user_id
            lang = job.lang
            total = len(image_keys)

            await _update_job(
                db, job_id,
                status="processing",
                progress_step="reading",
                progress_current=0,
                progress_total=total,
            )

            # Step 1: Read images from temp storage and compute hashes
            images_data: list[tuple[str, bytes, str]] = []  # (b64, raw, hash)
            for i, key in enumerate(image_keys):
                raw = await oci_get_bytes(key)
                if not raw:
                    continue
                if len(raw) > MAX_FILE_SIZE:
                    continue
                img_hash = hashlib.sha256(raw).hexdigest()
                b64 = base64.b64encode(raw).decode("utf-8")
                images_data.append((b64, raw, img_hash))

                await _update_job(
                    db, job_id,
                    progress_step="reading",
                    progress_current=i + 1,
                )

            if not images_data:
                await _update_job(
                    db, job_id,
                    status="failed",
                    error="Failed to read any uploaded images.",
                )
                await _cleanup_temp_images(image_keys)
                return

            image_hashes = [h for _, _, h in images_data]

            # Step 2: Dedup check
            await _update_job(db, job_id, progress_step="dedup_check")

            existing_photos: dict[str, AuditedPhoto] = {}
            new_image_indices: list[int] = []
            new_base64_images: list[str] = []

            for idx, img_hash in enumerate(image_hashes):
                res = await db.execute(
                    select(AuditedPhoto)
                    .where(AuditedPhoto.user_id == user_id, AuditedPhoto.hash == img_hash)
                    .limit(1)
                )
                existing = res.scalar_one_or_none()
                if existing:
                    existing_photos[img_hash] = existing
                else:
                    new_image_indices.append(idx)
                    new_base64_images.append(images_data[idx][0])

            # Step 3: If all duplicates, return cached
            if not new_base64_images:
                cached_photos = []
                for idx, img_hash in enumerate(image_hashes):
                    ex = existing_photos[img_hash]
                    cached_photos.append(
                        PhotoFeedback(
                            photo_id=f"photo_{idx + 1}",
                            score=ex.score,
                            tier=ex.tier,
                            brutal_feedback=ex.brutal_feedback,
                            improvement_tip=ex.improvement_tip,
                        )
                    )
                latest = list(existing_photos.values())[-1]
                response = AuditResponse(
                    total_analyzed=len(image_hashes),
                    passed_count=sum(1 for p in cached_photos if p.tier == "GOD_TIER"),
                    is_hard_reset=all(p.tier == "GRAVEYARD" for p in cached_photos),
                    roast_summary=latest.roast_summary,
                    photos=cached_photos,
                )
                await _update_job(
                    db, job_id,
                    status="completed",
                    progress_step="done",
                    progress_current=total,
                    result_json=response.model_dump_json(),
                )
                await _cleanup_temp_images(image_keys)
                return

            # Step 4: Call Gemini
            await _update_job(
                db, job_id,
                progress_step="analyzing",
                progress_current=0,
            )

            system_prompt = _build_system_prompt(lang)
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
                raw_response = await client.vision_generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    base64_images=new_base64_images,
                    temperature=0.0,
                    model=settings.gemini_model,
                    max_output_tokens=8192,
                    response_schema=PROFILE_AUDIT_SCHEMA,
                )
                latency_ms = int((time.monotonic() - start_time) * 1000)
                logger.info("audit_worker_gemini_success", job_id=job_id, latency_ms=latency_ms)
            except Exception as e:
                logger.error("audit_worker_gemini_failed", job_id=job_id, error=str(e))
                await _update_job(db, job_id, status="failed", error="AI analysis failed. Please retry.")
                await _cleanup_temp_images(image_keys)
                return

            # Parse response
            try:
                parsed = json.loads(raw_response)
                new_parsed = AuditResponse(**parsed)
                for photo in new_parsed.photos:
                    photo.tier = _score_to_tier(photo.score)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error("audit_worker_parse_failed", job_id=job_id, error=str(e))
                await _update_job(db, job_id, status="failed", error="Failed to parse AI response.")
                await _cleanup_temp_images(image_keys)
                return

            # Step 5: Merge results and persist
            await _update_job(db, job_id, progress_step="saving")

            all_photos = []
            photo_idx = 0
            for idx, img_hash in enumerate(image_hashes):
                if img_hash in existing_photos:
                    ex = existing_photos[img_hash]
                    all_photos.append(
                        PhotoFeedback(
                            photo_id=f"photo_{idx + 1}",
                            score=ex.score,
                            tier=ex.tier,
                            brutal_feedback=ex.brutal_feedback,
                            improvement_tip=ex.improvement_tip,
                        )
                    )
                else:
                    new_photo = new_parsed.photos[photo_idx]
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

            final_response = AuditResponse(
                total_analyzed=len(image_hashes),
                passed_count=sum(1 for p in all_photos if p.tier == "GOD_TIER"),
                is_hard_reset=all(p.tier == "GRAVEYARD" for p in all_photos),
                roast_summary=new_parsed.roast_summary,
                photos=all_photos,
            )

            # Phase 1: Upload all permanent objects to OCI first.
            # Track uploaded keys so we can delete them if DB commit fails.
            uploaded_permanent_keys: list[str] = []
            photos_to_add: list[AuditedPhoto] = []
            photo_idx = 0

            try:
                for idx, img_hash in enumerate(image_hashes):
                    if img_hash in existing_photos:
                        continue
                    try:
                        original_idx = new_image_indices[photo_idx]
                        _, raw_bytes, _ = images_data[original_idx]

                        photo_feedback = None
                        for pf in final_response.photos:
                            if pf.photo_id == f"photo_{idx + 1}":
                                photo_feedback = pf
                                break

                        if not photo_feedback:
                            photo_idx += 1
                            continue

                        filename = f"{photo_feedback.photo_id}_{int(time.time() * 1000)}.jpg"
                        object_key = f"audits/{user_id}/{filename}"
                        await oci_upload(object_key, raw_bytes, content_type="image/jpeg")
                        uploaded_permanent_keys.append(object_key)

                        photos_to_add.append(
                            AuditedPhoto(
                                user_id=user_id,
                                storage_path=object_key,
                                hash=img_hash,
                                score=photo_feedback.score,
                                tier=photo_feedback.tier,
                                brutal_feedback=photo_feedback.brutal_feedback,
                                improvement_tip=photo_feedback.improvement_tip,
                                roast_summary=new_parsed.roast_summary,
                                idempotency_key=job.idempotency_key,
                            )
                        )
                        photo_idx += 1

                        await _update_job(
                            db, job_id,
                            progress_step="saving",
                            progress_current=idx + 1,
                        )
                    except (IndexError, ValueError) as e:
                        logger.warning("audit_worker_save_skip", job_id=job_id, error=str(e))
                        continue
            except Exception as e:
                # OCI upload failed mid-loop — clean up already-uploaded permanent objects
                logger.error("audit_worker_permanent_upload_failed", job_id=job_id, error=str(e))
                for key in uploaded_permanent_keys:
                    await oci_delete(key)
                await _update_job(db, job_id, status="failed", error="Failed to save photos.")
                await _cleanup_temp_images(image_keys)
                return

            # Phase 2: Atomic DB commit — add all photo rows + mark job complete
            # in the same transaction so we never have OCI objects without DB rows
            # or a "completed" job without committed photos.
            for photo in photos_to_add:
                db.add(photo)

            result = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
            job_row = result.scalar_one_or_none()
            if job_row:
                job_row.status = "completed"
                job_row.progress_step = "done"
                job_row.progress_current = total
                job_row.result_json = final_response.model_dump_json()

            try:
                await db.commit()
            except Exception as e:
                logger.error("audit_worker_commit_failed", job_id=job_id, error=str(e))
                # DB commit failed — clean up the permanent OCI objects we just uploaded
                for key in uploaded_permanent_keys:
                    await oci_delete(key)
                try:
                    async with async_session() as err_db:
                        await _update_job(err_db, job_id, status="failed", error="Failed to save results.")
                except Exception:
                    pass
                await _cleanup_temp_images(image_keys)
                return

            logger.info(
                "audit_worker_complete",
                job_id=job_id,
                total=final_response.total_analyzed,
                passed=final_response.passed_count,
            )

            # Cleanup temp images
            await _cleanup_temp_images(image_keys)

        except Exception as e:
            # Log full error server-side, persist only a short safe string in DB
            logger.error("audit_worker_unexpected_error", job_id=job_id, error=str(e))
            try:
                async with async_session() as err_db:
                    await _update_job(
                        err_db, job_id,
                        status="failed",
                        error=_safe_error(e),
                    )
            except Exception as inner_e:
                logger.error("audit_worker_fail_update_failed", job_id=job_id, error=str(inner_e))
            await _cleanup_temp_images(image_keys)


async def _cleanup_temp_images(image_keys: list[str]) -> None:
    """Delete temporary uploaded images from OCI."""
    for key in image_keys:
        try:
            await oci_delete(key)
        except Exception:
            pass


def _build_system_prompt(lang: str) -> str:
    """Build the system prompt for Gemini Vision audit."""
    return (
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
        "OVERALL ROAST LINE\n"
        "After analyzing all photos, fill `roast_summary` with ONE punchy sentence about their overall "
        "dating-photo vibe. Tone: 8/10 savage, funny, 2026 internet energy — playful, not bullying.\n"
        "Draw from what you actually see (lighting, posing, backgrounds, try-hard vs low effort), not a "
        "made-up persona label or title.\n\n"
        "Score each photo on a strict 1-10 integer scale using this rubric:\n"
        "  1-3: Face not visible, blurry, heavy filter, or group shot where subject is unclear.\n"
        "  4-5: Visible face but poor lighting, bad background, unflattering angle, or low effort.\n"
        "  6-7: Acceptable photo — decent lighting and background, presentable but nothing stands out.\n"
        "  8-9: Strong photo — good lighting, clear face, confident body language, clean background.\n"
        "  10: Exceptional — professional feel, magnetic presence, would make anyone stop scrolling.\n"
        "Apply this rubric consistently. Do NOT output a tier field — only output the score."
    )
