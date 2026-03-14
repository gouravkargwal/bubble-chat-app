from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    AuditedPhotoItem,
    AuditedPhotoListResponse,
)
from app.config import settings
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, BlueprintSlot, User
from app.models.profile_auditor import AuditResponse
from app.services.profile_auditor_service import analyze_profile_photos


logger = structlog.get_logger()

router = APIRouter(prefix="/profile-audit", tags=["Profile Auditor"])


@router.post("", response_model=AuditResponse)
async def profile_audit(
    images: list[UploadFile] = File(
        ..., description="Up to 12 profile photos for brutal auditing"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Query(
        "English", description="Language/dialect for feedback and roasts"
    ),
) -> AuditResponse:
    """Brutally audit up to 12 dating profile photos."""
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required.")

    try:
        return await analyze_profile_photos(images=images, user=user, db=db, lang=lang)
    except ValueError as e:
        logger.error("profile_audit_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=str(e) or "Failed to audit profile photos."
        ) from e
    except Exception as e:
        logger.error(
            "profile_audit_unexpected_error", error=str(e), error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while auditing photos.",
        ) from e


@router.get("/history", response_model=AuditedPhotoListResponse)
async def list_profile_audits(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditedPhotoListResponse:
    """Return previously audited photos for the current user with pagination."""
    from sqlalchemy import func, select

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

    base_static = settings.base_url.rstrip("/") + "/static/"
    items: list[AuditedPhotoItem] = []
    for row in rows:
        image_url = base_static + row.storage_path.lstrip("/")
        items.append(
            AuditedPhotoItem(
                id=row.id,
                score=row.score,
                tier=row.tier,
                brutal_feedback=row.brutal_feedback,
                improvement_tip=row.improvement_tip,
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

    # Delete the file from storage
    try:
        file_path = Path("static") / photo.storage_path.lstrip("/")
        if file_path.exists():
            file_path.unlink()
            logger.info("profile_audit_delete_file_removed", path=str(file_path))
    except Exception as e:
        logger.warning(
            "profile_audit_delete_file_failed", error=str(e), path=photo.storage_path
        )

    # Delete the database record
    await db.delete(photo)
    await db.commit()

    logger.info("profile_audit_delete_success", photo_id=photo_id, user_id=user.id)
    return {"success": True, "message": "Photo deleted successfully."}
