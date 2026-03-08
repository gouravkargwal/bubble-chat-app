"""Aggregate all v1 routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.vision import router as vision_router
from app.api.v1.track import router as track_router
from app.api.v1.usage import router as usage_router
from app.api.v1.conversations import router as conversations_router

v1_router = APIRouter()
v1_router.include_router(auth_router, tags=["auth"])
v1_router.include_router(vision_router, tags=["vision"])
v1_router.include_router(track_router, tags=["track"])
v1_router.include_router(usage_router, tags=["usage"])
v1_router.include_router(conversations_router, tags=["conversations"])
