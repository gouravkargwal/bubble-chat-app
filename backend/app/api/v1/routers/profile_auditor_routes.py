import asyncio
import json
import time
from io import BytesIO
from pathlib import Path
from typing import Tuple

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi import Response
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import (
    AuditedPhotoItem,
    AuditedPhotoListResponse,
    AuditJobStatusResponse,
    AuditJobSubmitResponse,
)
from app.config import settings
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, AuditJob, BlueprintSlot, User
from app.infrastructure.oci_storage import (
    delete as oci_delete,
    get_bytes as oci_get_bytes,
    get_signed_url as oci_get_signed_url,
    upload as oci_upload,
)
from app.models.profile_auditor import AuditResponse
from app.services.audit_worker import process_audit_job
from app.services.quota_manager import QuotaExceededException, QuotaManager

logger = structlog.get_logger()

router = APIRouter(prefix="/profile-audit", tags=["Profile Auditor"])

# Endpoint-specific rate limiter (stricter than the global 120/min default)
limiter = Limiter(key_func=get_remote_address)

STATIC_ROOT = Path("static")
CARD_WIDTH = 1080
CARD_HEIGHT = 1920
SAFE_MARGIN = 80  # breathing room on left/right


# ─── Color Utilities ──────────────────────────────────────────────────


def parse_hex(
    color_str: str, default: Tuple[int, int, int] = (168, 85, 247)
) -> Tuple[int, int, int]:
    """Parse #RRGGBB → (R, G, B). Falls back to a vibrant purple."""
    try:
        if not color_str:
            return default
        s = color_str.strip().lstrip("#")
        if len(s) != 6:
            return default
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        return default


def lighten(rgb: Tuple[int, int, int], amount: int) -> Tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in rgb)


def darken(rgb: Tuple[int, int, int], amount: int) -> Tuple[int, int, int]:
    return tuple(max(0, c - amount) for c in rgb)


def contrast_text(bg_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Return white or near-black text depending on bg luminance."""
    lum = 0.2126 * bg_rgb[0] / 255 + 0.7152 * bg_rgb[1] / 255 + 0.0722 * bg_rgb[2] / 255
    return (12, 12, 18) if lum > 0.45 else (255, 255, 255)


def score_to_tier_label(score: int) -> str:
    """Map 0-100 rizz score to a gamified tier name."""
    if score >= 90:
        return "DIAMOND"
    if score >= 75:
        return "PLATINUM"
    if score >= 60:
        return "GOLD"
    if score >= 40:
        return "SILVER"
    return "BRONZE"


def tier_accent(tier: str, base_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Return a tier-specific accent color override (or use base)."""
    overrides = {
        "DIAMOND": (185, 242, 255),
        "PLATINUM": (220, 220, 235),
        "GOLD": (255, 215, 80),
        "SILVER": (192, 192, 210),
        "BRONZE": (205, 150, 100),
    }
    return overrides.get(tier, base_rgb)


# ─── Font Loading ─────────────────────────────────────────────────────


def _load_font(
    names: list[str], size: int
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try several font filenames inside static/fonts/, fall back to default."""
    for name in names:
        p = STATIC_ROOT / "fonts" / name
        try:
            if p.is_file():
                return ImageFont.truetype(str(p), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def font_bold(size: int):
    return _load_font(["Inter-Bold.ttf", "Montserrat-Bold.ttf"], size)


def font_semibold(size: int):
    return _load_font(["Inter-SemiBold.ttf", "Montserrat-SemiBold.ttf"], size)


def font_medium(size: int):
    return _load_font(["Inter-Medium.ttf", "Montserrat-Medium.ttf"], size)


def font_regular(size: int):
    return _load_font(["Inter-Regular.ttf", "Montserrat-Regular.ttf"], size)


# ─── Text Drawing ─────────────────────────────────────────────────────


def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    center_x: int,
    y: int,
    max_width: int,
    fill,
    line_spacing: int = 8,
    tracking: int = 0,
) -> int:
    """Word-wrap text centered at center_x. Returns new y after last line."""
    if not text:
        return y

    words = text.split()
    lines, current = [], ""
    for w in words:
        test = w if not current else current + " " + w
        tw, _ = _measure(draw, test, font)
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    for line in lines:
        lw, lh = _measure(draw, line, font)
        x = center_x - lw // 2
        draw.text((x, y), line, font=font, fill=fill)
        y += lh + line_spacing
    return y


# ─── Layer Builders ───────────────────────────────────────────────────


def _build_background(base_rgb: Tuple[int, int, int]) -> Image.Image:
    """
    Cinematic dark canvas with dual aurora glows:
      1) Large warm glow centered behind the photo area
      2) Softer secondary glow near the bottom for depth
    Plus film grain for analog texture.
    """
    bg = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (8, 8, 14, 255))

    # ── Primary aurora (centered on photo zone) ──
    aura1 = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(aura1)
    aw, ah = int(CARD_WIDTH * 1.8), int(CARD_HEIGHT * 1.0)
    cx, cy = CARD_WIDTH // 2, int(CARD_HEIGHT * 0.30)
    d1.ellipse(
        (cx - aw // 2, cy - ah // 2, cx + aw // 2, cy + ah // 2),
        fill=(*base_rgb, 90),
    )
    aura1 = aura1.filter(ImageFilter.GaussianBlur(radius=220))
    bg = Image.alpha_composite(bg, aura1)

    # ── Secondary glow (bottom, complementary shift) ──
    comp = ((base_rgb[0] + 128) % 256, (base_rgb[1] + 64) % 256, base_rgb[2])
    aura2 = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(aura2)
    aw2, ah2 = int(CARD_WIDTH * 1.2), int(CARD_HEIGHT * 0.5)
    cy2 = int(CARD_HEIGHT * 0.88)
    d2.ellipse(
        (cx - aw2 // 2, cy2 - ah2 // 2, cx + aw2 // 2, cy2 + ah2 // 2),
        fill=(*comp, 45),
    )
    aura2 = aura2.filter(ImageFilter.GaussianBlur(radius=180))
    bg = Image.alpha_composite(bg, aura2)

    # ── Film grain ──
    bg = _add_film_grain(bg, intensity=10)
    return bg


def _add_film_grain(image: Image.Image, intensity: int = 10) -> Image.Image:
    """Overlay subtle Gaussian film grain."""
    if intensity <= 0:
        return image
    intensity = max(1, min(intensity, 40))
    base = image.convert("RGBA")
    noise = Image.effect_noise(base.size, sigma=35).convert("L")
    alpha_val = int(255 * (intensity / 100.0))
    noise_rgba = Image.merge(
        "RGBA", (noise, noise, noise, Image.new("L", base.size, alpha_val))
    )
    return Image.alpha_composite(base, noise_rgba)


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[int, int, int, int],
    radius: int,
    fill=None,
    outline=None,
    width: int = 1,
):
    """Helper: draw a rounded rectangle on the given ImageDraw."""
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


def _composite_shadow(
    card: Image.Image,
    bbox: Tuple[int, int, int, int],
    radius: int,
    shadow_offset: int = 20,
    blur: int = 50,
    opacity: int = 160,
) -> Image.Image:
    """Draw a blurred shadow layer and composite it below content."""
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    shifted = (
        bbox[0] + shadow_offset,
        bbox[1] + shadow_offset,
        bbox[2] + shadow_offset,
        bbox[3] + shadow_offset,
    )
    sd.rounded_rectangle(shifted, radius=radius, fill=(0, 0, 0, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur))
    return Image.alpha_composite(card, shadow)


def _paste_photo_from_bytes(
    card: Image.Image,
    photo_bytes: bytes,
    left: int,
    top: int,
    width: int,
    height: int,
    corner_radius: int = 40,
) -> Image.Image:
    """Load photo from bytes, crop-to-fill, round-corner mask, and paste onto the card."""
    try:
        with Image.open(BytesIO(photo_bytes)).convert("RGB") as raw:
            rw, rh = raw.size
            target_r = width / height
            current_r = rw / rh
            if current_r > target_r:
                nh = height
                nw = int(nh * current_r)
            else:
                nw = width
                nh = int(nw / current_r)
            resized = raw.resize((nw, nh), Image.LANCZOS)
            cl = (nw - width) // 2
            ct = (nh - height) // 2
            cropped = resized.crop((cl, ct, cl + width, ct + height))

            mask = Image.new("L", (width, height), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, width, height), radius=corner_radius, fill=255
            )
            card.paste(cropped, (left, top), mask)
    except Exception:
        pass
    return card


# ─── Glassmorphic Badge ──────────────────────────────────────────────


def _draw_glass_badge(
    card: Image.Image,
    text: str,
    font,
    center_x: int,
    center_y: int,
    accent_rgb: Tuple[int, int, int],
    pill: bool = True,
) -> Image.Image:
    """
    Draw a frosted-glass style pill badge with:
      - Semi-transparent accent fill
      - Bright inner highlight stroke
      - Outer glow bloom
    """
    tmp = ImageDraw.Draw(card)
    tw, th = _measure(tmp, text, font)
    pad_x, pad_y = 48, 24
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    bl = center_x - bw // 2
    bt = center_y - bh // 2
    br = bl + bw
    bb = bt + bh
    rad = bh // 2 if pill else 28

    # Outer glow
    bloom = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    bd.rounded_rectangle(
        (bl - 12, bt - 12, br + 12, bb + 12), radius=rad + 12, fill=(*accent_rgb, 70)
    )
    bloom = bloom.filter(ImageFilter.GaussianBlur(radius=30))
    card = Image.alpha_composite(card, bloom)

    # Badge face
    badge = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bgd = ImageDraw.Draw(badge)
    bgd.rounded_rectangle((bl, bt, br, bb), radius=rad, fill=(*accent_rgb, 210))
    # Inner highlight
    bgd.rounded_rectangle(
        (bl + 2, bt + 2, br - 2, bb - 2),
        radius=rad - 2,
        outline=(255, 255, 255, 80),
        width=2,
    )
    card = Image.alpha_composite(card, badge)

    # Text
    draw = ImageDraw.Draw(card)
    text_color = contrast_text(accent_rgb)
    draw.text(
        (center_x - tw // 2, center_y - th // 2), text, font=font, fill=text_color
    )
    return card


# ─── Tier Ribbon ──────────────────────────────────────────────────────


def _draw_tier_ribbon(
    card: Image.Image,
    tier_label: str,
    font,
    x: int,
    y: int,
    accent_rgb: Tuple[int, int, int],
) -> Image.Image:
    """Small angled ribbon showing the tier name in the top-left of the photo."""
    draw = ImageDraw.Draw(card)
    tw, th = _measure(draw, tier_label, font)
    pad_x, pad_y = 28, 12
    rw = tw + pad_x * 2
    rh = th + pad_y * 2

    ribbon = Image.new("RGBA", card.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ribbon)
    rd.rounded_rectangle(
        (x, y, x + rw, y + rh), radius=8, fill=(*darken(accent_rgb, 30), 230)
    )
    rd.rounded_rectangle(
        (x + 1, y + 1, x + rw - 1, y + rh - 1),
        radius=7,
        outline=(255, 255, 255, 60),
        width=1,
    )
    card = Image.alpha_composite(card, ribbon)

    draw = ImageDraw.Draw(card)
    text_color = contrast_text(darken(accent_rgb, 30))
    draw.text((x + pad_x, y + pad_y), tier_label, font=font, fill=text_color)
    return card


# ─── Decorative Divider ──────────────────────────────────────────────


def _draw_divider(
    card: Image.Image,
    y: int,
    accent_rgb: Tuple[int, int, int],
    width: int = 180,
) -> Image.Image:
    """A short horizontal accent line as a visual separator."""
    draw = ImageDraw.Draw(card)
    cx = CARD_WIDTH // 2
    draw.line(
        (cx - width // 2, y, cx + width // 2, y),
        fill=(*accent_rgb, 120),
        width=3,
    )
    # Bright center dot
    draw.ellipse(
        (cx - 4, y - 4, cx + 4, y + 4),
        fill=(*lighten(accent_rgb, 60), 200),
    )
    return card


# ─── Main Renderer ────────────────────────────────────────────────────


def render_share_card(
    photo_bytes: bytes,
    score: int,
    archetype_title: str,
    roast_summary: str,
    share_card_color: str,
) -> bytes:
    """
    Render a 1080x1920 premium share card. Returns PNG bytes.

    Now accepts photo bytes directly from OCI instead of a file path.
    """
    base_rgb = parse_hex(share_card_color, default=(168, 85, 247))
    rizz_score = max(0, min(score * 10, 100))
    tier_label = score_to_tier_label(rizz_score)
    tier_rgb = tier_accent(tier_label, base_rgb)

    # ── Fonts ──
    f_score = font_bold(52)
    f_tier = font_semibold(28)
    f_title = font_bold(88)
    f_body = font_regular(42)
    f_brand = font_bold(48)
    f_cta = font_medium(34)
    f_small = font_regular(28)

    # ── Background ──
    card = _build_background(base_rgb)
    card = card.convert("RGBA")

    # ── Photo Frame ──
    photo_w, photo_h = 820, 1025  # 4:5
    photo_l = (CARD_WIDTH - photo_w) // 2
    photo_t = 130
    photo_r = photo_l + photo_w
    photo_b = photo_t + photo_h
    photo_bbox = (photo_l, photo_t, photo_r, photo_b)

    # Shadow behind photo
    card = _composite_shadow(
        card, photo_bbox, radius=40, shadow_offset=24, blur=60, opacity=180
    )

    # Thin accent border around photo area
    border_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(border_layer)
    bd.rounded_rectangle(
        (photo_l - 3, photo_t - 3, photo_r + 3, photo_b + 3),
        radius=43,
        outline=(*base_rgb, 100),
        width=2,
    )
    card = Image.alpha_composite(card, border_layer)

    # Paste actual photo from bytes
    card = _paste_photo_from_bytes(
        card, photo_bytes, photo_l, photo_t, photo_w, photo_h, corner_radius=40
    )

    # Subtle gradient vignette over bottom of photo (so badge reads well)
    vignette = Image.new("RGBA", (photo_w, photo_h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(200):
        alpha = int(130 * (i / 200) ** 1.5)
        y_line = photo_h - 200 + i
        vd.line((0, y_line, photo_w, y_line), fill=(8, 8, 14, alpha))
    mask = Image.new("L", (photo_w, photo_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, photo_w, photo_h), radius=40, fill=255
    )
    vignette.putalpha(mask)
    card.paste(vignette, (photo_l, photo_t), vignette)

    # ── Tier Ribbon (top-left of photo) ──
    card = _draw_tier_ribbon(
        card, tier_label, f_tier, photo_l + 20, photo_t + 20, tier_rgb
    )

    # ── Score Badge (overlapping bottom of photo) ──
    badge_text = f"{rizz_score}"
    badge_y = photo_b - 10
    card = _draw_glass_badge(
        card, badge_text, f_score, CARD_WIDTH // 2, badge_y, base_rgb, pill=True
    )

    # "RIZZ SCORE" small label above the number badge
    draw = ImageDraw.Draw(card)
    label = "RIZZ SCORE"
    lw, lh = _measure(draw, label, f_small)
    draw.text(
        (CARD_WIDTH // 2 - lw // 2, badge_y - lh - 44),
        label,
        font=f_small,
        fill=(255, 255, 255, 180),
    )

    # ── Divider ──
    current_y = photo_b + 70
    card = _draw_divider(card, current_y, base_rgb, width=160)
    current_y += 40

    # ── Archetype Title ──
    draw = ImageDraw.Draw(card)
    title = archetype_title or "The Main Character"
    current_y = draw_centered_text(
        draw,
        title,
        f_title,
        center_x=CARD_WIDTH // 2,
        y=current_y,
        max_width=int(CARD_WIDTH * 0.82),
        fill=(255, 255, 255),
        line_spacing=12,
    )
    current_y += 16

    # ── Roast Summary ──
    roast = (
        roast_summary
        or "You know you look good, and you're making sure nobody forgets it."
    )
    # Wrap in quotes for personality
    roast_display = f'"{roast}"'
    current_y = draw_centered_text(
        draw,
        roast_display,
        f_body,
        center_x=CARD_WIDTH // 2,
        y=current_y,
        max_width=int(CARD_WIDTH * 0.78),
        fill=(190, 190, 200),
        line_spacing=10,
    )

    # ── Bottom Divider ──
    current_y += 30
    card = _draw_divider(card, current_y, base_rgb, width=120)
    draw = ImageDraw.Draw(card)

    # ── Branding & CTA ──
    brand_y = CARD_HEIGHT - 200

    # Logo (if available)
    logo_path = STATIC_ROOT / "logo_cookd.png"
    if logo_path.is_file():
        try:
            with Image.open(logo_path).convert("RGBA") as logo:
                max_w = 180
                ratio = logo.width / logo.height
                lw = min(max_w, logo.width)
                lh = int(lw / ratio)
                logo_r = logo.resize((lw, lh), Image.LANCZOS)
                lx = (CARD_WIDTH - lw) // 2
                ly = brand_y - lh - 16
                card.paste(logo_r, (lx, ly), logo_r)
                draw = ImageDraw.Draw(card)
        except Exception:
            pass

    # Brand name
    brand = "cookd.ai"
    bw, bh = _measure(draw, brand, f_brand)
    draw.text(
        (CARD_WIDTH // 2 - bw // 2, brand_y),
        brand,
        font=f_brand,
        fill=(*lighten(base_rgb, 80), 255) if sum(base_rgb) < 400 else (255, 255, 255),
    )

    # CTA text
    cta = "Get your rizz rated"
    cw, ch = _measure(draw, cta, f_cta)
    draw.text(
        (CARD_WIDTH // 2 - cw // 2, brand_y + bh + 16),
        cta,
        font=f_cta,
        fill=(140, 140, 155),
    )

    # ── Export ──
    buf = BytesIO()
    card.convert("RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ─── Endpoints ────────────────────────────────────────────────────────


@router.post("", response_model=AuditJobSubmitResponse)
@limiter.limit("10/minute")
async def profile_audit(
    request: Request,
    background_tasks: BackgroundTasks,
    images: list[UploadFile] = File(
        ..., description="Up to 12 profile photos for brutal auditing"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Query(
        "English", description="Language/dialect for feedback and roasts"
    ),
    x_idempotency_key: str | None = Header(default=None),
) -> AuditJobSubmitResponse:
    """Submit photos for async audit. Returns a job_id immediately.

    The client should then connect to GET /profile-audit/{job_id}/stream (SSE)
    or poll GET /profile-audit/{job_id}/status to track progress and receive results.
    """
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required.")

    # Idempotency: if a completed job exists with this key, return its ID
    if x_idempotency_key:
        existing_job = await db.execute(
            select(AuditJob).where(
                AuditJob.user_id == user.id,
                AuditJob.idempotency_key == x_idempotency_key,
            ).limit(1)
        )
        cached_job = existing_job.scalar_one_or_none()
        if cached_job:
            logger.info("profile_audit_idempotent_hit", key=x_idempotency_key, job_id=cached_job.id)
            return AuditJobSubmitResponse(job_id=cached_job.id, status=cached_job.status)

    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])
    audits_per_week = tier_config["limits"]["profile_audits_per_week"]

    # Enforce weekly audit limit
    if audits_per_week > 0 and user.google_provider_id:
        qm = QuotaManager(db)
        try:
            await qm.check_and_increment_audits(
                user.google_provider_id,
                weekly_limit=audits_per_week,
            )
        except QuotaExceededException:
            raise HTTPException(
                status_code=429,
                detail=f"Weekly photo audit limit reached ({audits_per_week}/week). Resets on Monday.",
            )

    # Cap to 12 images
    upload_images = images[:12]

    # Upload images to temp OCI storage and create job
    image_keys: list[str] = []
    for i, upload in enumerate(upload_images):
        data = await upload.read()
        if not data:
            continue
        temp_key = f"temp-audits/{user.id}/{int(time.time() * 1000)}_{i}.jpg"
        await oci_upload(temp_key, data, content_type="image/jpeg")
        image_keys.append(temp_key)

    if not image_keys:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Failed to read any image data.")

    # Create the job row
    job = AuditJob(
        user_id=user.id,
        status="pending",
        progress_total=len(image_keys),
        lang=lang,
        idempotency_key=x_idempotency_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("profile_audit_job_created", job_id=job.id, images=len(image_keys))

    # Kick off background processing
    background_tasks.add_task(process_audit_job, job.id, image_keys)

    return AuditJobSubmitResponse(job_id=job.id, status="pending")


@router.get("/history", response_model=AuditedPhotoListResponse)
async def list_profile_audits(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditedPhotoListResponse:
    """Return previously audited photos for the current user with pagination."""
    # Get total count
    count_result = await db.execute(
        select(func.count(AuditedPhoto.id)).where(AuditedPhoto.user_id == user.id)
    )
    total_count = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user.id)
        .order_by(AuditedPhoto.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    items: list[AuditedPhotoItem] = []
    for row in rows:
        # Generate signed URL from OCI
        image_url = await oci_get_signed_url(row.storage_path)
        items.append(
            AuditedPhotoItem(
                id=row.id,
                score=row.score,
                tier=row.tier,
                brutal_feedback=row.brutal_feedback,
                improvement_tip=row.improvement_tip,
                archetype_title=row.archetype_title,
                roast_summary=row.roast_summary,
                share_card_color=row.share_card_color,
                image_url=image_url,
                created_at=int(row.created_at.timestamp()),
            )
        )

    return AuditedPhotoListResponse(
        items=items, total_count=total_count, limit=limit, offset=offset
    )


@router.delete("/{photo_id}")
async def delete_profile_audit_photo(
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a profile audit photo. Verifies ownership and handles blueprint slots."""
    # Verify ownership
    result = await db.execute(
        select(AuditedPhoto).where(
            AuditedPhoto.id == photo_id, AuditedPhoto.user_id == user.id
        )
    )
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found or access denied.")

    # Check if photo is used in any blueprint slots
    slot_result = await db.execute(
        select(BlueprintSlot).where(BlueprintSlot.photo_id == photo_id)
    )
    slots = slot_result.scalars().all()

    if slots:
        # Set photo_id to NULL for all slots using this photo
        for slot in slots:
            slot.photo_id = None
        logger.info(
            "profile_audit_delete_cleared_slots",
            photo_id=photo_id,
            slots_cleared=len(slots),
        )

    storage_path = photo.storage_path  # keep path before deleting DB row

    # Also delete the share card if it exists
    share_card_key = f"share-cards/{user.id}/{photo_id}.png"

    # 1. Delete the database record FIRST and commit.
    await db.delete(photo)
    await db.commit()

    logger.info("profile_audit_delete_db_success", photo_id=photo_id, user_id=user.id)

    # 2. Delete from OCI Object Storage SECOND.
    await oci_delete(storage_path)
    await oci_delete(share_card_key)

    return {"success": True, "message": "Photo deleted successfully."}


@router.get("/share-card/{user_id}")
async def get_share_card(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate (or return cached) 1080x1920 shareable roast card for the given user.

    Share cards are stored in OCI Object Storage
    cache, avoiding the ~2.5 GB memory leak from caching 256 full-resolution PNGs.
    """
    result = await db.execute(
        select(AuditedPhoto)
        .where(AuditedPhoto.user_id == user_id)
        .order_by(desc(AuditedPhoto.created_at))
        .limit(12)
    )
    photos = result.scalars().all()

    if not photos:
        raise HTTPException(
            status_code=404, detail="No photo audits found for this user."
        )

    latest_created_at = max(p.created_at for p in photos)
    latest_session = [p for p in photos if p.created_at == latest_created_at] or photos
    best_photo = max(latest_session, key=lambda p: p.score)

    archetype_title = best_photo.archetype_title or "The Main Character"
    roast_summary = best_photo.roast_summary or (
        "You know you look good, and you're making sure nobody forgets it."
    )
    share_card_color = best_photo.share_card_color or "#FFD700"

    # Check if pre-rendered share card already exists in OCI
    share_card_key = f"share-cards/{user_id}/{best_photo.id}.png"
    cached_png = await oci_get_bytes(share_card_key)
    if cached_png:
        return Response(content=cached_png, media_type="image/png")

    # Load the source photo from OCI
    photo_bytes = await oci_get_bytes(best_photo.storage_path)
    if not photo_bytes:
        raise HTTPException(
            status_code=404, detail="Source photo not found in storage."
        )

    try:
        png_bytes = render_share_card(
            photo_bytes=photo_bytes,
            score=best_photo.score,
            archetype_title=archetype_title,
            roast_summary=roast_summary,
            share_card_color=share_card_color,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.error("profile_share_card_render_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to generate share card."
        ) from e

    # Persist rendered card to OCI so subsequent requests skip rendering
    await oci_upload(share_card_key, png_bytes, content_type="image/png")

    return Response(content=png_bytes, media_type="image/png")


# ─── Job Progress Endpoints (parameterized — must come AFTER fixed routes) ────


@router.get("/{job_id}/stream")
async def stream_audit_progress(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE endpoint that streams real-time progress events for an audit job.

    Events:
      - event: progress  data: {"step": "analyzing", "current": 3, "total": 8}
      - event: complete  data: {full AuditResponse JSON}
      - event: error     data: {"message": "..."}
    """
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id, AuditJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found.")

    async def event_generator():
        """Yield SSE events by polling the job row until terminal state."""
        last_step = ""
        last_current = -1

        while True:
            await db.expire_all()
            res = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
            current_job = res.scalar_one_or_none()

            if not current_job:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                return

            if current_job.progress_step != last_step or current_job.progress_current != last_current:
                last_step = current_job.progress_step
                last_current = current_job.progress_current
                progress_data = {
                    "step": current_job.progress_step,
                    "current": current_job.progress_current,
                    "total": current_job.progress_total,
                    "status": current_job.status,
                }
                yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"

            if current_job.status == "completed" and current_job.result_json:
                yield f"event: complete\ndata: {current_job.result_json}\n\n"
                return

            if current_job.status == "failed":
                error_msg = current_job.error or "Processing failed"
                yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/status", response_model=AuditJobStatusResponse)
async def get_audit_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditJobStatusResponse:
    """Polling fallback: returns current status of an audit job."""
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id, AuditJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found.")

    audit_result = None
    if job.status == "completed" and job.result_json:
        try:
            audit_result = AuditResponse(**json.loads(job.result_json))
        except Exception:
            pass

    return AuditJobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        progress_step=job.progress_step,
        error=job.error,
        result=audit_result,
    )
