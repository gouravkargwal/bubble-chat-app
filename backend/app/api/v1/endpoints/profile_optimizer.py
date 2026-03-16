from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import (
    ProfileBlueprint as ProfileBlueprintDB,
    User,
)
from app.schemas.profile_blueprint import (
    ProfileBlueprintListResponse,
    ProfileBlueprintResponse,
)
from app.services.profile_optimizer_service import generate_blueprint

router = APIRouter(prefix="/profile-audit", tags=["profile-audit"])


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

    now = datetime.now(timezone.utc)
    monday_midnight = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    plan_start = current_user.plan_period_start
    if plan_start is not None:
        plan_start_naive = plan_start.replace(tzinfo=None) if plan_start.tzinfo else plan_start
        week_start = max(monday_midnight, plan_start_naive)
    else:
        week_start = monday_midnight

    weekly_count_result = await db.execute(
        select(func.count(ProfileBlueprintDB.id)).where(
            ProfileBlueprintDB.user_id == current_user.id,
            ProfileBlueprintDB.created_at >= week_start,
        )
    )
    weekly_used = weekly_count_result.scalar() or 0

    if weekly_used >= blueprints_per_week:
        raise HTTPException(
            status_code=429,
            detail=f"Weekly blueprint limit reached ({blueprints_per_week}/week). Resets on Monday.",
        )

    try:
        blueprint = await generate_blueprint(user_id=current_user.id, db=db, lang=lang)
    except ValueError as exc:
        # Propagate as 400 so clients can handle "no audited photos" gracefully.
        raise HTTPException(status_code=400, detail=str(exc))
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
