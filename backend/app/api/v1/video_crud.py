"""CRUD for rendered videos — list, download, delete, re-render.

All endpoints are admin-only (behind X-Admin-Key) so they go through
the /api/admin/* BFF proxy from the landing page.
"""

import os
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse

from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import RenderedVideo

logger = structlog.get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_db)])  # admin_deps injected via router


@router.get("/admin/rendered-videos")
async def list_rendered_videos(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all rendered videos, newest first."""
    stmt = (
        select(RenderedVideo)
        .order_by(RenderedVideo.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(RenderedVideo.status == status)

    result = await db.execute(stmt)
    videos = result.scalars().all()

    return {
        "videos": [
            {
                "id": v.id,
                "interactionId": v.interaction_id,
                "personName": v.person_name,
                "winningLine": v.winning_line,
                "strategyLabel": v.strategy_label,
                "hookStyle": v.hook_style,
                "viralScore": v.viral_score,
                "fileSizeBytes": v.file_size_bytes,
                "status": v.status,
                "errorMessage": v.error_message,
                "createdAt": v.created_at.isoformat() if v.created_at else None,
                "updatedAt": v.updated_at.isoformat() if v.updated_at else None,
                # Download URL is just the id — frontend constructs /api/admin/rendered-videos/{id}/download
            }
            for v in videos
        ],
        "count": len(videos),
    }


@router.get("/admin/rendered-videos/{video_id}/download")
async def download_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stream a rendered video file for download."""
    stmt = select(RenderedVideo).where(RenderedVideo.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    if video.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Video status is '{video.status}', not 'completed'.",
        )

    if not video.file_path or not os.path.isfile(video.file_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk.")

    filename = f"cookd-{video.person_name.lower().replace(' ', '-')}.mp4"

    return FileResponse(
        path=video.file_path,
        media_type=video.content_type or "video/mp4",
        filename=filename,
    )


@router.delete("/admin/rendered-videos/{video_id}")
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a rendered video (file + DB record)."""
    stmt = select(RenderedVideo).where(RenderedVideo.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    # Delete file from disk
    if video.file_path and os.path.isfile(video.file_path):
        try:
            os.remove(video.file_path)
            logger.info("video_file_deleted", path=video.file_path)
        except OSError as e:
            logger.warning(
                "video_file_delete_failed", path=video.file_path, error=str(e)
            )

    # Delete DB record
    await db.delete(video)
    await db.commit()

    return {"status": "deleted", "id": video_id}


@router.post("/admin/rendered-videos")
async def create_rendered_video(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Create a rendered video record (called by render-video route)."""
    video = RenderedVideo(
        interaction_id=body.get("interactionId"),
        person_name=body.get("personName", "Someone"),
        winning_line=body.get("winningLine", ""),
        strategy_label=body.get("strategyLabel", "COOKD_AI"),
        hook_style=body.get("hookStyle", "strategy"),
        viral_score=body.get("viralScore", 0),
        file_path=body.get("filePath", ""),
        file_size_bytes=body.get("fileSizeBytes", 0),
        content_type="video/mp4",
        status=body.get("status", "completed"),
        error_message=body.get("errorMessage"),
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    return {
        "id": video.id,
        "status": video.status,
        "fileSizeBytes": video.file_size_bytes,
    }


@router.get("/admin/rendered-videos/stats")
async def video_stats(
    db: AsyncSession = Depends(get_db),
):
    """Aggregate stats about rendered videos."""
    from sqlalchemy import func

    total = await db.scalar(select(func.count(RenderedVideo.id)))
    completed = await db.scalar(
        select(func.count(RenderedVideo.id)).where(RenderedVideo.status == "completed")
    )
    failed = await db.scalar(
        select(func.count(RenderedVideo.id)).where(RenderedVideo.status == "failed")
    )
    total_bytes = await db.scalar(
        select(func.coalesce(func.sum(RenderedVideo.file_size_bytes), 0)).where(
            RenderedVideo.status == "completed"
        )
    )

    return {
        "total": total or 0,
        "completed": completed or 0,
        "failed": failed or 0,
        "totalBytes": total_bytes or 0,
        "totalMb": round((total_bytes or 0) / (1024 * 1024), 1),
    }
