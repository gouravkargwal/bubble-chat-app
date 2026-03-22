from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
from app.services.profile_optimizer_service import generate_blueprint, _build_blueprint_response

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
    x_idempotency_key: str | None = Header(
        default=None,
        description=(
            "Optional client-generated key (e.g. UUID). If a blueprint was already "
            "created with this key, that blueprint is returned without calling the LLM again."
        ),
    ),
) -> ProfileBlueprintResponse:
    """Generate an optimized profile blueprint for the current user and save it to the database."""
    # Capture before any await + rollback: after rollback the User may be expired and
    # accessing .id lazy-loads via sync IO → MissingGreenlet in async SQLAlchemy.
    user_id = current_user.id

    effective_tier = get_effective_tier(current_user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])
    blueprints_per_week = tier_config["limits"]["profile_blueprints_per_week"]

    if blueprints_per_week == 0:
        raise HTTPException(
            status_code=403,
            detail="Profile blueprints are not available on your current plan. Please upgrade.",
        )

    # Enforce quota for ALL users — not just those with a Google provider ID.
    # Previously the google_provider_id guard silently let non-Google users bypass
    # the weekly limit entirely. We now use firebase_uid as a fallback key so
    # every authenticated user is rate-limited.
    if blueprints_per_week > 0:
        quota_key = current_user.google_provider_id or current_user.firebase_uid
        if not quota_key:
            raise HTTPException(
                status_code=403,
                detail="A verified account is required to generate blueprints.",
            )
        qm = QuotaManager(db)
        try:
            await qm.check_and_increment_blueprints(
                quota_key,
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

    try:
        blueprint = await generate_blueprint(
            user_id=user_id,
            db=db,
            lang=lang,
            idempotency_key=x_idempotency_key,
        )
        # SUCCESS: commit blueprint + quota increment atomically.
        await db.commit()
    except ValueError as exc:
        # Known, user-facing error (e.g. no photos, LLM hallucinated photo_id)
        # — rollback to refund quota.
        await db.rollback()
        logger.warning(
            "profile_blueprint_generation_failed",
            user_id=user_id,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # Unexpected failure — rollback so the user is not charged.
        await db.rollback()
        logger.error(
            "profile_blueprint_generation_critical_failure",
            user_id=user_id,
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
    """Return previously generated profile blueprints for the current user with pagination."""
    count_result = await db.execute(
        select(func.count(ProfileBlueprintDB.id)).where(
            ProfileBlueprintDB.user_id == current_user.id
        )
    )
    total_count = count_result.scalar_one()

    result = await db.execute(
        select(ProfileBlueprintDB)
        .where(ProfileBlueprintDB.user_id == current_user.id)
        .options(
            selectinload(ProfileBlueprintDB.slots),
            selectinload(ProfileBlueprintDB.universal_prompts),
        )
        .order_by(ProfileBlueprintDB.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    db_blueprints = result.scalars().all()

    items = [_build_blueprint_response(bp) for bp in db_blueprints]

    return ProfileBlueprintListResponse(
        items=items, total_count=total_count, limit=limit, offset=offset
    )
