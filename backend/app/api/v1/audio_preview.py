"""
Audio preview endpoint — streams a YouTube audio track for preview in the Post Wizard.

This is a lightweight proxy: given a YouTube video ID, it uses yt-dlp to get
the direct audio URL and redirects the client to it. No audio is stored on our servers.

Usage: GET /api/v1/admin/publish/audio-preview/{youtube_id}
  → Redirects to the audio stream URL
"""

from __future__ import annotations

import subprocess
import json

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.api.v1.admin_deps import verify_admin_key

logger = structlog.get_logger(__name__)

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/admin/publish/audio-preview/{youtube_id}")
async def stream_audio_preview(youtube_id: str):
    """Redirect to the audio stream URL for a YouTube video.

    Uses yt-dlp to extract the best audio URL, then redirects the browser
    to that URL. This avoids storing audio on our servers.
    """
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-g",  # Get URL only (no download)
                "-f",
                "bestaudio[ext=m4a]/bestaudio",
                "--no-playlist",
                "--quiet",
                f"https://www.youtube.com/watch?v={youtube_id}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:200]
            raise RuntimeError(f"yt-dlp failed: {stderr}")

        audio_url = result.stdout.strip()
        if not audio_url:
            raise RuntimeError("No audio URL returned")

        return RedirectResponse(url=audio_url)

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Audio fetch timed out")
    except RuntimeError as e:
        logger.error("audio_preview_failed", youtube_id=youtube_id, error=str(e))
        raise HTTPException(status_code=502, detail=str(e))
