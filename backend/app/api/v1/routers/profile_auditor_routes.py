from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Tuple

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import Response
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import Date, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import AuditedPhotoItem, AuditedPhotoListResponse
from app.config import settings
from app.core.tier_config import TIER_CONFIG
from app.domain.tiers import get_effective_tier
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import AuditedPhoto, BlueprintSlot, User
from app.models.profile_auditor import AuditResponse
from app.services.profile_auditor_service import analyze_profile_photos
from app.services.quota_manager import QuotaExceededException, QuotaManager

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = structlog.get_logger()

router = APIRouter(prefix="/profile-audit", tags=["Profile Auditor"])

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


def _paste_photo(
    card: Image.Image,
    storage_path: str,
    left: int,
    top: int,
    width: int,
    height: int,
    corner_radius: int = 40,
) -> Image.Image:
    """Load, crop-to-fill, round-corner mask, and paste a photo onto the card."""
    photo_path = STATIC_ROOT / storage_path
    try:
        with Image.open(photo_path).convert("RGB") as raw:
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


@lru_cache(maxsize=256)
def render_share_card_cached(
    user_id: str,
    photo_id: str,
    storage_path: str,
    score: int,
    archetype_title: str,
    roast_summary: str,
    share_card_color: str,
) -> bytes:
    """
    Render a 1080×1920 premium share card. Returns PNG bytes.

    Layout (top → bottom):
      ┌────────────────────────────┐
      │  (aurora glow background)  │
      │                            │
      │   ┌──────────────────┐     │
      │   │  TIER RIBBON     │     │
      │   │                  │     │
      │   │     PHOTO        │     │
      │   │   (4:5 crop)     │     │
      │   │                  │     │
      │   │  ┌────────────┐  │     │
      │   └──┤ RIZZ SCORE ├──┘     │
      │      └────────────┘        │
      │                            │
      │     ── divider ──          │
      │                            │
      │     ARCHETYPE TITLE        │
      │     roast summary text     │
      │                            │
      │     ── divider ──          │
      │                            │
      │       🔥 cookd.ai         │
      │    "Get your rizz rated"   │
      └────────────────────────────┘
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

    # Paste actual photo
    card = _paste_photo(
        card, storage_path, photo_l, photo_t, photo_w, photo_h, corner_radius=40
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


@router.post("", response_model=AuditResponse)
async def profile_audit(
    images: list[UploadFile] = File(
        ..., description="Up to 12 profile photos for brutal auditing"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Query(
        "English", description="Language/dialect for feedback and roasts"
    ),
) -> AuditResponse:
    """Brutally audit up to 12 dating profile photos."""
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required.")

    effective_tier = get_effective_tier(user)
    tier_config = TIER_CONFIG.get(effective_tier, TIER_CONFIG["free"])
    audits_per_week = tier_config["limits"]["profile_audits_per_week"]

    # 1. Enforce weekly audit limit via QuotaManager when we have a stable Google ID.
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
                detail=f"Weekly profile audit limit reached ({audits_per_week}/week). Resets on Monday.",
            )

    # 2. Execute heavy AI/Vision call with explicit transaction control.
    try:
        response = await analyze_profile_photos(
            images=images, user=user, db=db, lang=lang
        )
        # 3. SUCCESS: commit quota increment + new audits, release locks.
        await db.commit()
        return response
    except ValueError as e:
        # Known, user-facing error (bad images, etc.) — rollback to refund quota.
        await db.rollback()
        logger.error("profile_audit_failed", error=str(e))
        raise HTTPException(
            status_code=400, detail=str(e) or "Failed to audit profile photos."
        ) from e
    except Exception as e:
        # Unexpected failure — rollback so quota isn't charged on server error.
        await db.rollback()
        logger.error(
            "profile_audit_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred while auditing photos. "
                "Your quota was not charged."
            ),
        ) from e


@router.get("/history", response_model=AuditedPhotoListResponse)
async def list_profile_audits(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditedPhotoListResponse:
    """Return previously audited photos for the current user with pagination."""
    from sqlalchemy import func, select

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

    base_static = settings.base_url.rstrip("/") + "/static/"
    items: list[AuditedPhotoItem] = []
    for row in rows:
        image_url = base_static + row.storage_path.lstrip("/")
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

    # 1. Delete the database record FIRST and commit.
    await db.delete(photo)
    await db.commit()

    logger.info("profile_audit_delete_db_success", photo_id=photo_id, user_id=user.id)

    # 2. Delete the physical file SECOND.
    try:
        file_path = Path("static") / storage_path.lstrip("/")
        if file_path.exists():
            file_path.unlink()
            logger.info("profile_audit_delete_file_removed", path=str(file_path))
    except Exception as e:
        # Log only — DB is already consistent; orphaned files can be cleaned later.
        logger.warning(
            "profile_audit_delete_file_failed", error=str(e), path=storage_path
        )

    return {"success": True, "message": "Photo deleted successfully."}


@router.get("/share-card/{user_id}")
async def get_share_card(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate (or return cached) 1080x1920 shareable roast card for the given user.

    Logic:
    - Fetch latest audited photos for this user (most recent created_at).
    - Among that "session", pick the photo with highest score to feature.
    - Render a branded PNG card using archetype_title, roast_summary, share_card_color.
    - Use an in-memory LRU cache so repeated requests don't re-render.
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
            status_code=404, detail="No profile audits found for this user."
        )

    latest_created_at = max(p.created_at for p in photos)
    latest_session = [p for p in photos if p.created_at == latest_created_at] or photos
    best_photo = max(latest_session, key=lambda p: p.score)

    archetype_title = best_photo.archetype_title or "The Main Character"
    roast_summary = best_photo.roast_summary or (
        "You know you look good, and you're making sure nobody forgets it."
    )
    share_card_color = best_photo.share_card_color or "#FFD700"

    try:
        png_bytes = render_share_card_cached(
            user_id=user_id,
            photo_id=best_photo.id,
            storage_path=best_photo.storage_path,
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

    return Response(content=png_bytes, media_type="image/png")
