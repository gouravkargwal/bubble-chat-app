"""Aggregate all v1 routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.endpoints.profile_optimizer import (
    router as profile_optimizer_router,
)
from app.api.v1.history import router as history_router
from app.api.v1.promo import router as promo_router
from app.api.v1.referral import router as referral_router
from app.api.v1.routers.profile_auditor_routes import (
    router as profile_auditor_router,
)
from app.api.v1.track import router as track_router
from app.api.v1.usage import router as usage_router
from app.api.v1.vision import router as vision_router

v1_router = APIRouter()
v1_router.include_router(auth_router, tags=["auth"])
v1_router.include_router(vision_router, tags=["vision"])
v1_router.include_router(profile_auditor_router)
v1_router.include_router(profile_optimizer_router)
v1_router.include_router(track_router, tags=["track"])
v1_router.include_router(usage_router, tags=["usage"])
v1_router.include_router(history_router, tags=["history"])
v1_router.include_router(conversations_router, tags=["conversations"])
v1_router.include_router(referral_router, tags=["referral"])
v1_router.include_router(billing_router, tags=["billing"])
v1_router.include_router(promo_router, tags=["promo"])
