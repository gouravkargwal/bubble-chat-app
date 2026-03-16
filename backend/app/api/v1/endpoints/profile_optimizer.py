from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from app.api.v1.deps import get_current_user
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import (
    ProfileBlueprint as ProfileBlueprintDB,
    User,
)
from app.services.quota_manager import QuotaExceededException, QuotaManager
from app.schemas.profile_blueprint import (
    ProfileBlueprintListResponse,
    ProfileBlueprintResponse,
)
from app.services.profile_optimizer_service import generate_blueprint

router = APIRouter(prefix="/profile-audit", tags=["profile-audit"])
logger = structlog.get_logger()


@router.post(
    "/optimize",
    response_model=ProfileBlueprintResponse,
)
async def optimize_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Query("English", description="Language/dialect for all generated copy"),
) -> ProfileBlueprintResponse:
    """Generate an optimized profile blueprint for the current user and save it to the database."""
    effective_tier = get_effective_tier(current_user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])
    blueprints_per_week = tier_config["limits"]["profile_blueprints_per_week"]

    if blueprints_per_week == 0:
        raise HTTPException(
            status_code=403,
            detail="Profile blueprints are not available on your current plan. Please upgrade.",
        )

    # 1. Enforce quota and acquire row lock on the quota row.
    if blueprints_per_week > 0 and current_user.google_provider_id:
        qm = QuotaManager(db)
        try:
            await qm.check_and_increment_blueprints(
                current_user.google_provider_id,
                weekly_limit=blueprints_per_week,
            )
        except QuotaExceededException:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Weekly blueprint limit reached ({blueprints_per_week}/week). "
                    "Resets on Monday."
                ),
            )

    # 2. Execute the heavy AI generation with explicit transaction control.
    try:
        blueprint = await generate_blueprint(user_id=current_user.id, db=db, lang=lang)
        # 3. SUCCESS: commit blueprint + quota increment and release locks.
        await db.commit()
    except ValueError as exc:
        # Known, user-facing error (e.g. no photos) — rollback to refund quota.
        await db.rollback()
        logger.warning(
            "profile_blueprint_generation_failed",
            user_id=current_user.id,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # Unexpected failure (LLM crash, timeout, DB error) — rollback so user
        # is not charged for a failed generation.
        await db.rollback()
        logger.error(
            "profile_blueprint_generation_critical_failure",
            user_id=current_user.id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Our AI is currently overloaded. Your blueprint was not saved and "
                "your quota was not charged. Please try again."
            ),
        )

    return blueprint


@router.get(
    "/blueprints",
    response_model=ProfileBlueprintListResponse,
)
async def list_profile_blueprints(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileBlueprintListResponse:
    """Return previously generated profile blueprints for the current user with pagination, ordered by created_at DESC."""
    from sqlalchemy import func

    # Get total count
    count_result = await db.execute(
        select(func.count(ProfileBlueprintDB.id)).where(
            ProfileBlueprintDB.user_id == current_user.id
        )
    )
    total_count = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(ProfileBlueprintDB)
        .where(ProfileBlueprintDB.user_id == current_user.id)
        .options(selectinload(ProfileBlueprintDB.slots))
        .order_by(ProfileBlueprintDB.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    db_blueprints = result.scalars().all()

    # Build response with storage paths from audited_photos
    items = []
    for db_blueprint in db_blueprints:
        slot_responses = []
        for db_slot in db_blueprint.slots:
            slot_responses.append(
                {
                    "id": db_slot.id,
                    "photo_id": db_slot.photo_id,
                    "slot_number": db_slot.slot_number,
                    "role": db_slot.role,
                    "caption": db_slot.caption,
                    "universal_hook": db_slot.universal_hook,
                    "hinge_prompt": db_slot.hinge_prompt,
                    "aisle_prompt": db_slot.aisle_prompt,
                    "image_url": db_slot.image_url,
                }
            )

        # Sort slots by slot_number
        slot_responses.sort(key=lambda x: x["slot_number"])

        items.append(
            ProfileBlueprintResponse(
                id=db_blueprint.id,
                user_id=db_blueprint.user_id,
                overall_theme=db_blueprint.overall_theme,
                bio=db_blueprint.bio,
                created_at=db_blueprint.created_at,
                slots=slot_responses,
            )
        )

    return ProfileBlueprintListResponse(
        items=items, total_count=total_count, limit=limit, offset=offset
    )
