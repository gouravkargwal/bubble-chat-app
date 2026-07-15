"""
Social media poster — publishes videos to Instagram Reels and YouTube Shorts.

Instagram: Uses the Graph API (requires Facebook Business Page → Instagram Business Account).
YouTube: Uses the Data API v3 resumable upload protocol.

Both require OAuth tokens configured in settings.
"""

from __future__ import annotations

import json
import os
import structlog
from typing import Any

import httpx

from app.config import settings

logger = structlog.get_logger(__name__)

# ── Constants ──

_IG_GRAPH_API = "https://graph.facebook.com/v19.0"
_YT_UPLOAD_API = "https://www.googleapis.com/upload/youtube/v3/videos"
_YT_API_BASE = "https://www.googleapis.com/youtube/v3"

# Max upload size: 10 MB for Instagram, 256 GB for YouTube (we cap at 50 MB)
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


# ── YouTube Upload ──


async def post_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy_status: str = "public",
) -> dict[str, Any]:
    """
    Upload a video to YouTube Shorts via the Data API resumable upload protocol.

    Returns: { "platformPostId": str, "platformUrl": str }
    Raises RuntimeError on failure.
    """
    if not settings.youtube_refresh_token:
        raise RuntimeError("YouTube not configured: YOUTUBE_REFRESH_TOKEN is missing")

    # Step 1: Get an access token from the refresh token
    access_token = await _get_youtube_access_token()

    if not os.path.isfile(video_path):
        raise RuntimeError(f"Video file not found: {video_path}")

    file_size = os.path.getsize(video_path)
    if file_size > _MAX_UPLOAD_BYTES:
        raise RuntimeError(
            f"Video too large: {file_size} bytes (max {_MAX_UPLOAD_BYTES})"
        )

    # Step 2: Initiate resumable upload
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": (description or "")[:5000],
            "tags": (tags or [])[:500],
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/*",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Initiate upload session
        init_resp = await client.post(
            f"{_YT_UPLOAD_API}?part=snippet,status",
            headers=headers,
            json=metadata,
        )

        if init_resp.status_code != 200:
            body = init_resp.text[:500]
            raise RuntimeError(
                f"YouTube upload initiation failed: {init_resp.status_code} {body}"
            )

        # The upload URL is in the Location header
        upload_url = init_resp.headers.get("Location")
        if not upload_url:
            raise RuntimeError("YouTube did not return an upload URL")

        # Step 3: Upload the video binary
        with open(video_path, "rb") as f:
            upload_resp = await client.post(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/*",
                    "Content-Length": str(file_size),
                },
                content=f,
                timeout=300.0,  # 5 min for upload
            )

        if upload_resp.status_code not in (200, 201, 204):
            body = upload_resp.text[:500]
            raise RuntimeError(
                f"YouTube video upload failed: {upload_resp.status_code} {body}"
            )

        video_id = upload_resp.json().get("id", "")

    url = f"https://youtube.com/shorts/{video_id}" if video_id else ""

    logger.info(
        "youtube_upload_complete",
        video_id=video_id,
        title=title,
    )

    return {
        "platformPostId": video_id,
        "platformUrl": url,
    }


async def _get_youtube_access_token() -> str:
    """Exchange the refresh token for a short-lived access token."""
    data = {
        "client_id": settings.youtube_client_id,
        "client_secret": settings.youtube_client_secret,
        "refresh_token": settings.youtube_refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data=data)
        if resp.status_code != 200:
            raise RuntimeError(
                f"YouTube token refresh failed: {resp.status_code} {resp.text[:200]}"
            )
        return resp.json()["access_token"]


# ── Instagram Upload ──


async def post_to_instagram(
    video_path: str,
    caption: str,
) -> dict[str, Any]:
    """
    Upload a Reel to Instagram via the Graph API.

    Instagram requires a two-step process:
      1. Create a media container (POST to /{ig-user-id}/media)
      2. Publish the container (POST to /{ig-user-id}/media_publish)

    Returns: { "platformPostId": str, "platformUrl": str }
    Raises RuntimeError on failure.
    """
    if (
        not settings.instagram_access_token
        or not settings.instagram_business_account_id
    ):
        raise RuntimeError(
            "Instagram not configured: INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID missing"
        )

    if not os.path.isfile(video_path):
        raise RuntimeError(f"Video file not found: {video_path}")

    # Step 1: Create media container
    # The video must be hosted at a public URL for Instagram to ingest.
    # Since our videos are local, we need to upload to a temporary public URL first.
    # We use OCI object storage (already configured) for this.
    media_url = await _upload_to_temp_storage(video_path)

    ig_user_id = settings.instagram_business_account_id
    access_token = settings.instagram_access_token

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create container
        create_resp = await client.post(
            f"{_IG_GRAPH_API}/{ig_user_id}/media",
            params={
                "media_type": "REELS",
                "video_url": media_url,
                "caption": (caption or "")[:2200],
                "access_token": access_token,
            },
        )

        if create_resp.status_code != 200:
            body = create_resp.text[:500]
            raise RuntimeError(
                f"Instagram container creation failed: {create_resp.status_code} {body}"
            )

        container_id = create_resp.json().get("id", "")

        if not container_id:
            raise RuntimeError("Instagram did not return a container ID")

        # Step 2: Poll container status until ready (up to 60s)
        import asyncio

        for attempt in range(6):
            await asyncio.sleep(10)
            status_resp = await client.get(
                f"{_IG_GRAPH_API}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": access_token,
                },
            )

            if status_resp.status_code != 200:
                continue

            status_code = status_resp.json().get("status_code")
            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                raise RuntimeError("Instagram media processing failed")
            # else: still processing, retry

        # Step 3: Publish
        publish_resp = await client.post(
            f"{_IG_GRAPH_API}/{ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": access_token,
            },
        )

        if publish_resp.status_code != 200:
            body = publish_resp.text[:500]
            raise RuntimeError(
                f"Instagram publish failed: {publish_resp.status_code} {body}"
            )

        media_id = publish_resp.json().get("id", "")

    logger.info(
        "instagram_upload_complete",
        media_id=media_id,
    )

    return {
        "platformPostId": media_id,
        "platformUrl": f"https://instagram.com/reel/{media_id}" if media_id else "",
    }


async def _upload_to_temp_storage(video_path: str) -> str:
    """
    Upload a video to a temporary public URL for Instagram ingestion.

    Uses the existing OCI object storage infrastructure.
    Falls back to a simple file server approach if OCI is not configured.
    """
    from app.infrastructure.oci_storage import upload_file_to_oci

    try:
        url = await upload_file_to_oci(
            file_path=video_path,
            object_name=f"temp-publish/{os.path.basename(video_path)}",
            par_expiry_hours=2,
        )
        return url
    except Exception as e:
        logger.warning("oci_upload_failed_for_instagram", error=str(e))
        # Fallback: use the backend's own download endpoint if available
        # This requires the video to be accessible at a public URL
        raise RuntimeError(
            "Instagram requires a public video URL. "
            "Configure OCI storage or upload the video to a public server first."
        ) from e


# ── Caption Generator ──


async def generate_caption(transcript: str, winning_line: str) -> str:
    """
    Generate a social media caption for the video using Gemini.
    Always appends the app link + hashtags after the LLM-generated text.
    """
    app_link = "https://cookdai.site"
    hashtags = "#CookdAI #AIChat"
    footer = f"\n\n📲 {app_link}\n{hashtags}"

    if not settings.gemini_api_key:
        return f'"{winning_line}" — Cookd AI 🎯{footer}'

    prompt = (
        'You are a viral short-form video copywriter for "Cookd AI", an AI dating assistant app.\n'
        "Generate a short, punchy caption with relevant hashtags for this chat video.\n"
        "Make it curious — ask a question or create intrigue to drive comments.\n"
        f"Winning AI reply: {winning_line}\n"
        f"Chat context: {transcript}\n"
        "Rules:\n"
        "- Max 3 lines for the caption text\n"
        "- Then add 3-5 relevant hashtags on a new line (include #dating, #hinge, #bumble, #relationships, #ai, #texting, #datingadvice, #modernlove, #singlelife, or similar based on content)\n"
        "- End with a question or a cliffhanger in the caption part\n"
        "- Match the LANGUAGE of the winning reply (if it's Hinglish, write caption in Hinglish; if English, write in English)\n"
        "- Do NOT include the app link (it will be appended automatically)\n"
        "- Output format: caption text line(s) + blank line + hashtags"
    )

    caption_text = ""
    try:
        import google.genai as genai_module

        client = genai_module.Client(
            api_key=settings.gemini_api_key,
            http_options={"timeout": 15000},
        )
        response = client.models.generate_content(
            model=settings.gemini_model or "gemini-3.1-flash-lite",
            contents=prompt,
        )
        if response and response.text:
            caption_text = response.text.strip()[:300]
    except Exception as e:
        logger.warning("caption_generation_failed", error=str(e))

    if not caption_text:
        caption_text = f'"{winning_line}" — Cookd AI 🎯'

    return f"{caption_text}{footer}"
