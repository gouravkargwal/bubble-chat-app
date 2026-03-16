from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from pathlib import Path
from sqlalchemy import cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    AuditedPhotoItem,
    AuditedPhotoListResponse,
)
from app.config import settings
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, BlueprintSlot, User
from app.models.profile_auditor import AuditResponse
from app.services.profile_auditor_service import analyze_profile_photos
from app.services.quota_manager import QuotaExceededException, QuotaManager


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

    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])
    audits_per_week = tier_config["limits"]["profile_audits_per_week"]

    # 1. Enforce weekly audit limit via QuotaManager when we have a stable Google ID.
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
                detail=f"Weekly profile audit limit reached ({audits_per_week}/week). Resets on Monday.",
            )

    # 2. Execute heavy AI/Vision call with explicit transaction control.
    try:
        response = await analyze_profile_photos(
            images=images, user=user, db=db, lang=lang
        )
        # 3. SUCCESS: commit quota increment + new audits, release locks.
        await db.commit()
        return response
    except ValueError as e:
        # Known, user-facing error (bad images, etc.) — rollback to refund quota.
        await db.rollback()
        logger.error("profile_audit_failed", error=str(e))
        raise HTTPException(
            status_code=400, detail=str(e) or "Failed to audit profile photos."
        ) from e
    except Exception as e:
        # Unexpected failure — rollback so quota isn't charged on server error.
        await db.rollback()
        logger.error(
            "profile_audit_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred while auditing photos. "
                "Your quota was not charged."
            ),
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
                archetype_title=row.archetype_title,
                roast_summary=row.roast_summary,
                share_card_color=row.share_card_color,
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

    # 2. Delete the physical file SECOND.
    try:
        file_path = Path("static") / storage_path.lstrip("/")
        if file_path.exists():
            file_path.unlink()
            logger.info("profile_audit_delete_file_removed", path=str(file_path))
    except Exception as e:
        # Log only — DB is already consistent; orphaned files can be cleaned later.
        logger.warning(
            "profile_audit_delete_file_failed", error=str(e), path=storage_path
        )

    return {"success": True, "message": "Photo deleted successfully."}
