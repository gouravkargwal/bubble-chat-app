from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User
from app.models.profile_optimizer import ProfileBlueprint
from app.services.profile_optimizer_service import generate_blueprint

router = APIRouter(prefix="/profile-audit", tags=["profile-audit"])


@router.get(
    "/optimize",
    response_model=ProfileBlueprint,
)
async def optimize_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileBlueprint:
    """Generate an optimized profile blueprint for the current user."""
    try:
        blueprint = await generate_blueprint(user_id=current_user.id, db=db)
    except ValueError as exc:
        # Propagate as 400 so clients can handle "no audited photos" gracefully.
        raise HTTPException(status_code=400, detail=str(exc))
    return blueprint

