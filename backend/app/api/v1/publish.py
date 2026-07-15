"""
Publish endpoint — the "Post Wizard" backend.

Flow:
  1. GET  /admin/publish/trending-audio  → returns trending tracks from YouTube
  2. POST /admin/publish/generate-caption → calls Llama 3 to write a caption
  3. POST /admin/publish/send            → overlays audio + posts to selected platforms

All endpoints are admin-only (behind X-Admin-Key).
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_deps import verify_admin_key
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import RenderedVideo, PublishedVideo
from app.services.trending_audio import fetch_trending_audio
from app.services.audio_overlay import overlay_youtube_audio
from app.services.social_poster import (
    post_to_youtube,
    post_to_instagram,
    generate_caption,
)

logger = structlog.get_logger(__name__)

router = APIRouter(dependencies=[Depends(verify_admin_key)])


# ── Schemas ──


class TrendingAudioResponse(BaseModel):
    tracks: list[dict[str, Any]]


class GenerateCaptionRequest(BaseModel):
    transcript: str = ""
    winningLine: str = ""


class GenerateCaptionResponse(BaseModel):
    caption: str


class PublishRequest(BaseModel):
    renderedVideoId: str
    youtubeAudioId: str = ""  # YouTube video ID for audio overlay
    audioTitle: str = ""
    caption: str = ""
    platforms: list[str] = ["instagram", "youtube"]


class PublishResult(BaseModel):
    platform: str
    status: str
    platformPostId: str | None = None
    platformUrl: str | None = None
    error: str | None = None


class PublishResponse(BaseModel):
    results: list[PublishResult]


# ── Endpoints ──


@router.get("/admin/publish/trending-audio", response_model=TrendingAudioResponse)
async def get_trending_audio():
    """Return trending music tracks from YouTube for the audio picker."""
    tracks = await fetch_trending_audio(region_code="IN", max_results=20)
    return TrendingAudioResponse(tracks=tracks)


@router.post("/admin/publish/generate-caption", response_model=GenerateCaptionResponse)
async def generate_caption_endpoint(body: GenerateCaptionRequest):
    """Generate a social media caption using Llama 3."""
    caption = await generate_caption(
        transcript=body.transcript, winning_line=body.winningLine
    )
    return GenerateCaptionResponse(caption=caption)


@router.post("/admin/publish/send", response_model=PublishResponse)
async def publish_video(body: PublishRequest, db: AsyncSession = Depends(get_db)):
    """
    Overlay audio onto a rendered video and publish to selected platforms.

    This is the core "Post Wizard" endpoint:
      1. Loads the rendered video record
      2. Downloads trending audio from YouTube (if specified)
      3. Overlays audio onto the video via FFmpeg
      4. Uploads to each selected platform
      5. Creates PublishedVideo records
    """
    # 1. Look up the rendered video
    from sqlalchemy import select

    stmt = select(RenderedVideo).where(RenderedVideo.id == body.renderedVideoId)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Rendered video not found")

    if video.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Video status is '{video.status}', must be 'completed'",
        )

    if not video.file_path or not os.path.isfile(video.file_path):
        raise HTTPException(status_code=400, detail="Video file not found on disk")

    # 2. Apply audio overlay (if audio track selected)
    final_video_path = video.file_path
    if body.youtubeAudioId:
        output_dir = os.path.join(os.path.dirname(video.file_path), "published")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            f"{os.path.splitext(os.path.basename(video.file_path))[0]}_with_audio.mp4",
        )

        try:
            final_video_path = await overlay_youtube_audio(
                video_path=video.file_path,
                youtube_id=body.youtubeAudioId,
                output_path=output_path,
                volume=0.3,
            )
        except RuntimeError as e:
            logger.error("audio_overlay_failed", error=str(e))
            # Continue with original video
            final_video_path = video.file_path

    # 3. Post to each selected platform
    results: list[PublishResult] = []

    for platform in body.platforms:
        platform = platform.lower().strip()
        pub_record = PublishedVideo(
            rendered_video_id=video.id,
            platform=platform,
            audio_track_title=body.audioTitle or "",
            audio_track_youtube_id=body.youtubeAudioId or "",
            caption=body.caption or "",
            status="posting",
        )
        db.add(pub_record)
        await db.flush()

        try:
            if platform == "youtube":
                # Build a short-form-friendly title
                title = f"Cookd AI — {video.person_name} 🔥"
                desc = (
                    f"{body.caption}\n\n"
                    f"📲 Download Cookd AI: https://cookdai.site\n"
                    f"#CookdAI #DatingCoach #AIChat"
                )
                plat_result = await post_to_youtube(
                    video_path=final_video_path,
                    title=title,
                    description=desc,
                    tags=["CookdAI", "DatingCoach", "AIChat", "DatingTips"],
                    privacy_status="public",
                )

                pub_record.platform_post_id = plat_result.get("platformPostId")
                pub_record.platform_url = plat_result.get("platformUrl")
                pub_record.status = "posted"

                results.append(
                    PublishResult(
                        platform=platform,
                        status="posted",
                        platformPostId=plat_result.get("platformPostId"),
                        platformUrl=plat_result.get("platformUrl"),
                    )
                )

            elif platform == "instagram":
                plat_result = await post_to_instagram(
                    video_path=final_video_path,
                    caption=body.caption or "",
                )

                pub_record.platform_post_id = plat_result.get("platformPostId")
                pub_record.platform_url = plat_result.get("platformUrl")
                pub_record.status = "posted"

                results.append(
                    PublishResult(
                        platform=platform,
                        status="posted",
                        platformPostId=plat_result.get("platformPostId"),
                        platformUrl=plat_result.get("platformUrl"),
                    )
                )

            else:
                results.append(
                    PublishResult(
                        platform=platform,
                        status="failed",
                        error=f"Unknown platform: {platform}",
                    )
                )
                pub_record.status = "failed"
                pub_record.error_message = f"Unknown platform: {platform}"

        except RuntimeError as e:
            logger.error("publish_failed", platform=platform, error=str(e))
            pub_record.status = "failed"
            pub_record.error_message = str(e)
            results.append(
                PublishResult(
                    platform=platform,
                    status="failed",
                    error=str(e),
                )
            )

        await db.flush()

    await db.commit()

    return PublishResponse(results=results)


@router.get("/admin/publish/history")
async def get_publish_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Return recently published videos across all platforms."""
    from sqlalchemy import select, desc

    stmt = select(PublishedVideo).order_by(desc(PublishedVideo.created_at)).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()

    return {
        "published": [
            {
                "id": p.id,
                "renderedVideoId": p.rendered_video_id,
                "platform": p.platform,
                "platformPostId": p.platform_post_id,
                "platformUrl": p.platform_url,
                "audioTrackTitle": p.audio_track_title,
                "caption": p.caption,
                "status": p.status,
                "errorMessage": p.error_message,
                "viewCount": p.view_count,
                "likeCount": p.like_count,
                "commentCount": p.comment_count,
                "createdAt": p.created_at.isoformat() if p.created_at else None,
            }
            for p in records
        ]
    }
