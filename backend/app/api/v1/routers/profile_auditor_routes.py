import asyncio
import json
import time

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    AuditedPhotoItem,
    AuditedPhotoListResponse,
    AuditJobStatusResponse,
    AuditJobSubmitResponse,
)
from app.config import settings
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, AuditJob, BlueprintSlot, User
from app.infrastructure.oci_storage import (
    delete as oci_delete,
    get_signed_url as oci_get_signed_url,
    upload as oci_upload,
)
from app.models.profile_auditor import AuditResponse
from app.services.audit_worker import process_audit_job
from app.services.quota_manager import QuotaExceededException, QuotaManager

logger = structlog.get_logger()

router = APIRouter(prefix="/profile-audit", tags=["Profile Auditor"])

# Endpoint-specific rate limiter (stricter than the global 120/min default)
limiter = Limiter(key_func=get_remote_address)


# ─── Endpoints ────────────────────────────────────────────────────────


@router.post("", response_model=AuditJobSubmitResponse)
@limiter.limit("10/minute")
async def profile_audit(
    request: Request,
    background_tasks: BackgroundTasks,
    images: list[UploadFile] = File(
        ..., description="Up to 12 profile photos for brutal auditing"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Query(
        "English", description="Language/dialect for feedback and roasts"
    ),
    x_idempotency_key: str | None = Header(default=None),
) -> AuditJobSubmitResponse:
    """Submit photos for async audit. Returns a job_id immediately.

    The client should then connect to GET /profile-audit/{job_id}/stream (SSE)
    or poll GET /profile-audit/{job_id}/status to track progress and receive results.
    """
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required.")

    # Idempotency: return cached job only if it's still active or succeeded.
    # Failed jobs are ignored so the client can retry with the same key.
    if x_idempotency_key:
        existing_job = await db.execute(
            select(AuditJob).where(
                AuditJob.user_id == user.id,
                AuditJob.idempotency_key == x_idempotency_key,
                AuditJob.status.in_(["pending", "processing", "completed"]),
            ).limit(1)
        )
        cached_job = existing_job.scalar_one_or_none()
        if cached_job:
            logger.info("profile_audit_idempotent_hit", key=x_idempotency_key, job_id=cached_job.id)
            return AuditJobSubmitResponse(job_id=cached_job.id, status=cached_job.status)

    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])
    audits_per_week = tier_config["limits"]["profile_audits_per_week"]

    # Enforce weekly audit limit
    if audits_per_week > 0 and user.google_provider_id:
        qm = QuotaManager(db)
        try:
            await qm.check_and_increment_audits(
                user.google_provider_id,
                weekly_limit=audits_per_week,
            )
        except QuotaExceededException:
            raise HTTPException(
                status_code=429,
                detail=f"Weekly photo audit limit reached ({audits_per_week}/week). Resets on Monday.",
            )

    # Cap to 12 images
    upload_images = images[:12]

    # Read + validate sizes before any OCI upload to avoid wasting quota on
    # oversized files (worker would just drop them anyway).
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per image
    raw_images: list[tuple[int, bytes]] = []
    for i, upload in enumerate(upload_images):
        data = await upload.read()
        if not data:
            continue
        if len(data) > MAX_FILE_SIZE:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Image {i + 1} exceeds 5 MB limit.")
        raw_images.append((i, data))

    # Upload validated images to temp OCI storage.
    # On failure, clean up any already-uploaded keys before re-raising.
    image_keys: list[str] = []
    try:
        for i, data in raw_images:
            temp_key = f"temp-audits/{user.id}/{int(time.time() * 1000)}_{i}.jpg"
            await oci_upload(temp_key, data, content_type="image/jpeg")
            image_keys.append(temp_key)
    except Exception:
        for key in image_keys:
            await oci_delete(key)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upload images. Please try again.")

    if not image_keys:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Failed to read any image data.")

    # Create the job row. The partial unique index on (user_id, idempotency_key)
    # WHERE status != 'failed' prevents two concurrent POSTs from both succeeding.
    job = AuditJob(
        user_id=user.id,
        status="pending",
        progress_total=len(image_keys),
        lang=lang,
        idempotency_key=x_idempotency_key,
    )
    db.add(job)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        # Race: another request won the insert. Clean up our temp uploads
        # and return the existing job.
        for key in image_keys:
            await oci_delete(key)
        if x_idempotency_key:
            existing = await db.execute(
                select(AuditJob).where(
                    AuditJob.user_id == user.id,
                    AuditJob.idempotency_key == x_idempotency_key,
                    AuditJob.status.in_(["pending", "processing", "completed"]),
                ).limit(1)
            )
            winner = existing.scalar_one_or_none()
            if winner:
                return AuditJobSubmitResponse(job_id=winner.id, status=winner.status)
        raise HTTPException(status_code=409, detail="Duplicate audit request. Please retry.")
    await db.refresh(job)

    logger.info("profile_audit_job_created", job_id=job.id, images=len(image_keys))

    # Kick off background processing
    background_tasks.add_task(process_audit_job, job.id, image_keys)

    return AuditJobSubmitResponse(job_id=job.id, status="pending")


@router.get("/history", response_model=AuditedPhotoListResponse)
async def list_profile_audits(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditedPhotoListResponse:
    """Return previously audited photos for the current user with pagination."""
    # Get total count
    count_result = await db.execute(
        select(func.count(AuditedPhoto.id)).where(AuditedPhoto.user_id == user.id)
    )
    total_count = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user.id)
        .order_by(AuditedPhoto.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    items: list[AuditedPhotoItem] = []
    for row in rows:
        # Always return the row so pagination (limit/offset) stays consistent with
        # total_count. Empty image_url if signing fails — otherwise the client treats a
        # short page as the last page and never loads older audits.
        image_url = ""
        try:
            image_url = await oci_get_signed_url(row.storage_path)
        except Exception as e:
            logger.warning("history_par_failed", photo_id=row.id, error=str(e)[:200])
        items.append(
            AuditedPhotoItem(
                id=row.id,
                score=row.score,
                tier=row.tier,
                brutal_feedback=row.brutal_feedback,
                improvement_tip=row.improvement_tip,
                roast_summary=row.roast_summary,
                image_url=image_url,
                created_at=int(row.created_at.timestamp()),
            )
        )

    return AuditedPhotoListResponse(
        items=items, total_count=total_count, limit=limit, offset=offset
    )


@router.delete("/{photo_id}")
async def delete_profile_audit_photo(
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a profile audit photo. Verifies ownership and handles blueprint slots."""
    # Verify ownership
    result = await db.execute(
        select(AuditedPhoto).where(
            AuditedPhoto.id == photo_id, AuditedPhoto.user_id == user.id
        )
    )
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found or access denied.")

    # Check if photo is used in any blueprint slots
    slot_result = await db.execute(
        select(BlueprintSlot).where(BlueprintSlot.photo_id == photo_id)
    )
    slots = slot_result.scalars().all()

    if slots:
        # Set photo_id to NULL for all slots using this photo
        for slot in slots:
            slot.photo_id = None
        logger.info(
            "profile_audit_delete_cleared_slots",
            photo_id=photo_id,
            slots_cleared=len(slots),
        )

    storage_path = photo.storage_path  # keep path before deleting DB row

    # 1. Delete the database record FIRST and commit.
    await db.delete(photo)
    await db.commit()

    logger.info("profile_audit_delete_db_success", photo_id=photo_id, user_id=user.id)

    # 2. Delete from OCI Object Storage SECOND.
    await oci_delete(storage_path)

    return {"success": True, "message": "Photo deleted successfully."}


# ─── Job Progress Endpoints (parameterized — must come AFTER fixed routes) ────


@router.get("/{job_id}/stream")
async def stream_audit_progress(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE endpoint that streams real-time progress events for an audit job.

    Events:
      - event: progress  data: {"step": "analyzing", "current": 3, "total": 8}
      - event: complete  data: {full AuditResponse JSON}
      - event: error     data: {"message": "..."}
    """
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id, AuditJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found.")

    async def event_generator():
        """Yield SSE events by polling the job row until terminal state.

        Server-side timeout: 3 minutes max to prevent infinite SSE connections
        from stuck jobs (e.g. worker crash without updating status).
        """
        last_step = ""
        last_current = -1
        max_iterations = 180  # 180 * 1s = 3 minutes

        for _ in range(max_iterations):
            await db.expire_all()
            res = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
            current_job = res.scalar_one_or_none()

            if not current_job:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                return

            if current_job.progress_step != last_step or current_job.progress_current != last_current:
                last_step = current_job.progress_step
                last_current = current_job.progress_current
                progress_data = {
                    "step": current_job.progress_step,
                    "current": current_job.progress_current,
                    "total": current_job.progress_total,
                    "status": current_job.status,
                }
                yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"

            if current_job.status == "completed" and current_job.result_json:
                yield f"event: complete\ndata: {current_job.result_json}\n\n"
                return

            if current_job.status == "failed":
                error_msg = current_job.error or "Processing failed"
                yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
                return

            await asyncio.sleep(1)

        # Timed out server-side
        yield f"event: error\ndata: {json.dumps({'message': 'Processing timed out. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/status", response_model=AuditJobStatusResponse)
async def get_audit_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditJobStatusResponse:
    """Polling fallback: returns current status of an audit job."""
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id, AuditJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found.")

    audit_result = None
    if job.status == "completed" and job.result_json:
        try:
            audit_result = AuditResponse(**json.loads(job.result_json))
        except Exception as e:
            logger.error(
                "audit_status_result_parse_failed",
                job_id=job_id,
                error=str(e)[:200],
                result_preview=job.result_json[:200] if job.result_json else "N/A",
            )

    return AuditJobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        progress_step=job.progress_step,
        error=job.error,
        result=audit_result,
    )
