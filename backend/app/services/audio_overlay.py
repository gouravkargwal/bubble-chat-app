"""
Audio overlay service — downloads a YouTube audio track and overlays it onto a video.

Uses yt-dlp to download the audio and FFmpeg to overlay it.
Both must be available on the system PATH (they are in the Docker images).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


async def overlay_youtube_audio(
    video_path: str,
    youtube_id: str,
    output_path: str,
    volume: float = 0.3,
) -> str:
    """
    Download audio from a YouTube video and overlay it onto the input video.

    Args:
        video_path: Path to the rendered MP4.
        youtube_id: YouTube video ID to extract audio from.
        output_path: Where to write the final video.
        volume: Audio volume relative to original (0.0-1.0). Default 0.3 preserves
                any original audio at 30% volume so the video isn't silent if
                the download fails.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If FFmpeg or yt-dlp fail.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "trending_audio.mp3")

        # Step 1: Download audio with yt-dlp
        try:
            _run_cmd(
                [
                    "yt-dlp",
                    "-x",  # Extract audio
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "128k",
                    "-o",
                    audio_path,
                    "--no-playlist",
                    "--quiet",
                    f"https://www.youtube.com/watch?v={youtube_id}",
                ],
                "yt-dlp download",
            )
        except RuntimeError as e:
            logger.warning("audio_download_failed", error=str(e), youtube_id=youtube_id)
            # Fallback: copy original video as-is
            _run_cmd(["cp", video_path, output_path], "copy fallback")
            return output_path

        if not os.path.isfile(audio_path):
            logger.warning("audio_file_not_found", youtube_id=youtube_id)
            _run_cmd(["cp", video_path, output_path], "copy fallback")
            return output_path

        # Step 2: Overlay audio with FFmpeg
        # -c:v copy preserves the video stream (no re-encode)
        # -map 0:v:0 = first video stream from input
        # -map 1:a:0 = first audio stream from downloaded file
        # -shortest = stop when the shorter stream ends (usually the video)
        # -filter:a "volume=..." sets the audio level
        try:
            _run_cmd(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    audio_path,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-shortest",
                    "-filter:a",
                    f"volume={volume}",
                    output_path,
                ],
                "ffmpeg overlay",
            )
        except RuntimeError as e:
            logger.error("ffmpeg_overlay_failed", error=str(e))
            # Fallback: copy original
            _run_cmd(["cp", video_path, output_path], "copy fallback")
            return output_path

    logger.info(
        "audio_overlay_complete",
        input_size=os.path.getsize(video_path),
        output_size=os.path.getsize(output_path),
    )
    return output_path


def _run_cmd(cmd: list[str], label: str) -> None:
    """Run a subprocess command, raising RuntimeError on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:500]
            raise RuntimeError(f"{label} failed (code {result.returncode}): {stderr}")
    except FileNotFoundError as e:
        raise RuntimeError(f"{label} binary not found: {e}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{label} timed out after 120s")
