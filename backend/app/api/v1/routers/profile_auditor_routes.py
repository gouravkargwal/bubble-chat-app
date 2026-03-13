from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    AuditedPhotoItem,
    AuditedPhotoListResponse,
)
from app.config import settings
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, User
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
            status_code=502, detail="Failed to audit profile photos."
        ) from e


@router.get("/history", response_model=AuditedPhotoListResponse)
async def list_profile_audits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditedPhotoListResponse:
    """Return all previously audited photos for the current user."""
    from sqlalchemy import select

    result = await db.execute(
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user.id)
        .order_by(AuditedPhoto.created_at.desc())
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

    return AuditedPhotoListResponse(items=items)
