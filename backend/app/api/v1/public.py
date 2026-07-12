"""Public (no-auth) lead-magnet API.

Single endpoint ``POST /lead-magnet/generate`` that accepts a chat screenshot,
direction, and email, runs the full ``rizz_agent_v2``, and returns generated
replies.  Protected by a DB-backed 24 h per‑IP rate limit and a secondary
slowapi 10 req/min throttle.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import dns.resolver
import structlog
from crawlerdetect import CrawlerDetect
from disposable_email_domains import blocklist
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.engine import get_db
from app.infrastructure.ratelimit import limiter
from app.services.lead_magnet_service import (
    ActiveWindow,
    compute_rate_limit_reset,
    fire_lead_webhook,
    get_active_rate_limit_window,
    get_cached_replies,
    insert_lead,
    update_lead_failed,
    update_lead_success,
    validate_and_hash_image,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# ── Schemas ────────────────────────────────────────────────────────────────

VALID_DIRECTIONS = {"OPENER", "TEASE", "KEEP_PLAYFUL"}


class LeadMagnetRequest(BaseModel):
    image: str = Field(
        ..., description="Base64-encoded chat screenshot (max 3 MB after decode)."
    )
    direction: str = Field(
        ..., description=f"One of {', '.join(sorted(VALID_DIRECTIONS))}."
    )
    email: str = Field(
        ..., description="Email address for lead capture.", max_length=320
    )
    custom_hint: str | None = Field(
        default=None, max_length=200, description="Optional coaching hint."
    )
    # Honeypot — bots auto-fill this hidden field; humans don't see it.
    honeypot: str | None = Field(
        default=None,
        max_length=1000,
        description="Honeypot bot detection (hidden CSS field, never filled by humans).",
    )


class ReplyPayload(BaseModel):
    id: str
    style: str
    text: str


class LeadMagnetResponse(BaseModel):
    status: str  # "success" | "rate_limited" | "failed"
    cached: bool = False
    replies: list[ReplyPayload] | None = None
    detail: str | None = None
    retry_after_seconds: float | None = None
    app_url: str | None = None


# ── Dependencies ───────────────────────────────────────────────────────────


async def get_client_ip(
    request: Request,
    x_forwarded_for: str | None = Header(default=None),
    x_real_ip: str | None = Header(default=None),
) -> str:
    """Extract client IP, respecting reverse-proxy headers."""
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host if request.client else "0.0.0.0"


# ── Helpers ────────────────────────────────────────────────────────────────


def _build_public_replies(parsed: Any) -> list[dict[str, Any]]:
    """Convert parsed agent output to public reply format."""
    return [
        {
            "id": f"r{i+1}",
            "style": r.strategy_label,
            "text": r.text,
        }
        for i, r in enumerate(parsed.replies[:4])
    ]


def _format_replies(replies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalise reply dicts — handles both raw agent output and cached JSON."""
    return [
        {
            "id": r.get("id", f"r{i+1}"),
            "style": r.get("style", r.get("strategy_label", "")),
            "text": r.get("text", ""),
        }
        for i, r in enumerate(replies[:4])
    ]


# ── Email validation ────────────────────────────────────────────────────────

_EMAIL_RE = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

# DNS resolver with a short timeout to avoid blocking
_DNS_RESOLVER = dns.resolver.Resolver()
_DNS_RESOLVER.timeout = 2.0
_DNS_RESOLVER.lifetime = 3.0


async def _domain_has_mx_records(domain: str) -> bool:
    """Check whether the domain has at least one MX record.

    Domains without MX records cannot receive email — this catches
    throwaway domains, typo-squats, and non-existent domains.
    Uses dnspython with a short timeout, wrapped in an executor to
    avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: _DNS_RESOLVER.resolve(domain, "MX"),
        )
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False
    except (dns.exception.Timeout, dns.resolver.LifetimeTimeout):
        # DNS unreachable — log and allow the request to proceed
        logger.warning("mx_lookup_timeout", domain=domain)
        return True
    except Exception:
        logger.exception("mx_lookup_failed", domain=domain)
        return True  # Fail open — don't block on transient DNS issues


async def _validate_email(email: str) -> None:
    """Validate email format, block disposable domains, and check MX records."""
    if not re.match(_EMAIL_RE, email):
        raise HTTPException(422, "Invalid email address format.")

    domain = email.rsplit("@", 1)[-1].lower()

    # 1. Check disposable email domain blocklist
    if domain in blocklist:
        raise HTTPException(
            422, "Disposable email addresses are not allowed. Please use a permanent email."
        )

    # 2. DNS MX record check — domain must be able to receive email
    has_mx = await _domain_has_mx_records(domain)
    if not has_mx:
        logger.info("invalid_email_no_mx", email=email, domain=domain)
        raise HTTPException(
            422,
            "This email address appears to be invalid. "
            "Please use a real email address that can receive messages.",
        )


# ── Bot detection via CrawlerDetect ─────────────────────────────────────────

_crawler_detect = CrawlerDetect()


def _is_suspicious_ua(user_agent: str | None) -> bool:
    """Use ``crawlerdetect`` to check for bots, crawlers and spiders.

    Covers 3,600+ known bots.  Also rejects empty/missing User-Agent.
    """
    if not user_agent:
        return True  # Missing UA is suspicious
    return _crawler_detect.is_crawler(user_agent)



# ── Endpoint ───────────────────────────────────────────────────────────────


@router.post("/lead-magnet/generate", response_model=LeadMagnetResponse)
@limiter.limit("10/minute")
async def lead_magnet_generate(
    body: LeadMagnetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ip_address: str = Depends(get_client_ip),
    user_agent: str | None = Header(default=None),
) -> JSONResponse:
    """Accept screenshot + direction + email, run full agent, return replies.

    Rate-limited to **1 request per 24 hours per IP** (success/failure).
    Failed attempts have a **15‑minute cooldown**.
    If rate-limited, checks image cache — same image returns cached result.
    """
    start_time = time.monotonic()

    # ── 1. Input validation ───────────────────────────────────────────────
    if body.direction not in VALID_DIRECTIONS:
        return JSONResponse(
            status_code=422,
            content={
                "status": "failed",
                "detail": f"Invalid direction '{body.direction}'. "
                f"Must be one of {', '.join(sorted(VALID_DIRECTIONS))}.",
            },
        )

    await _validate_email(body.email)

    # ── 2. Honeypot check ────────────────────────────────────────────────
    if body.honeypot:
        logger.warning(
            "lead_magnet_honeypot_triggered",
            ip=ip_address,
            honeypot_value=body.honeypot[:100],
        )
        return JSONResponse(
            status_code=400,
            content={"status": "failed", "detail": "Request rejected."},
        )

    # ── 3. Basic bot detection (User-Agent) ───────────────────────────────
    if _is_suspicious_ua(user_agent):
        logger.warning(
            "lead_magnet_bot_detected",
            ip=ip_address,
            ua=user_agent,
        )
        return JSONResponse(
            status_code=400,
            content={"status": "failed", "detail": "Request rejected."},
        )

    # ── 4. Image validation + hash ────────────────────────────────────────
    try:
        image_base64, image_hash = validate_and_hash_image(body.image)
    except HTTPException as exc:
        return JSONResponse(
            status_code=422,
            content={"status": "failed", "detail": exc.detail},
        )

    # ── 5. Check rate limit (DB-backed 24 h) ──────────────────────────────
    window: ActiveWindow | None = await get_active_rate_limit_window(ip_address, db)

    if window is not None:
        # ── 5a. Same-image cache check ────────────────────────────────────
        cached = await get_cached_replies(ip_address, image_hash, db)
        if cached is not None:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "cached": True,
                    "replies": _format_replies(cached),
                },
            )

        # ── 5b. Record rate-limited attempt ───────────────────────────────
        rate_limit_reset = compute_rate_limit_reset("rate_limited")
        await insert_lead(
            db,
            ip_address=ip_address,
            email=body.email,
            direction=body.direction,
            custom_hint=body.custom_hint,
            image_hash=image_hash,
            status="rate_limited",
            rate_limit_reset_at=rate_limit_reset,
        )
        await db.commit()

        logger.info(
            "lead_magnet_rate_limited",
            ip=ip_address,
            status=window.status,
            retry_after=window.retry_after_seconds,
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )

        return JSONResponse(
            status_code=429,
            content={
                "status": "rate_limited",
                "detail": (
                    "You've used your free demo for today! 🎯 "
                    "Download the app to get unlimited AI-powered replies, "
                    "custom coaching, and more."
                ),
                "retry_after_seconds": window.retry_after_seconds,
                "app_url": settings.lead_magnet_app_url,
            },
        )

    # ── 6. Insert lead (status=pending) — capture email before agent runs ─
    rate_limit_reset = compute_rate_limit_reset("pending")
    lead = await insert_lead(
        db,
        ip_address=ip_address,
        email=body.email,
        direction=body.direction,
        custom_hint=body.custom_hint,
        image_hash=image_hash,
        status="pending",
        rate_limit_reset_at=rate_limit_reset,
    )
    await db.commit()

    # ── 7. Run the full rizz_agent_v2 ─────────────────────────────────────
    try:
        from agent.graph_v2 import rizz_agent_v2
        from app.api.v1.vision_v2 import perform_full_vision_analysis
        from app.api.v1.vision_agent_state import (
            _build_agent_initial_state,
            _parsed_from_agent_state,
        )

        # ── 7a. Run the vision LLM to analyze the screenshot ───────────────
        vision_out = await perform_full_vision_analysis(
            [image_base64],
            direction=body.direction,
            user_id="public-demo",
        )

        # ── 7b. Handle bouncer rejection early ────────────────────────────
        if not vision_out.is_valid_chat:
            await update_lead_failed(db, lead.id, vision_out.bouncer_reason)
            await db.commit()
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "detail": vision_out.bouncer_reason,
                },
            )

        # ── 7c. Build initial state with vision_out pre-populated ─────────
        initial_state = _build_agent_initial_state(
            image_base64=image_base64,
            direction=body.direction,
            custom_hint=body.custom_hint or "",
            user_id="public-demo",
            conversation_id=None,
            voice_dna=None,
            conversation_context=None,
        )
        initial_state["vision_out"] = vision_out.model_dump()

        final_state = await rizz_agent_v2.ainvoke(initial_state)

        # ── 7d. Parse & format replies ────────────────────────────────────
        parsed = _parsed_from_agent_state(final_state)
        replies_raw = _build_public_replies(parsed)

    except Exception as exc:
        logger.error(
            "lead_magnet_agent_failed",
            lead_id=lead.id,
            ip=ip_address,
            error=str(exc),
            exc_info=True,
        )
        await update_lead_failed(db, lead.id, str(exc)[:500])
        await db.commit()
        return JSONResponse(
            status_code=502,
            content={
                "status": "failed",
                "detail": "Generation failed. Please try again in 15 minutes.",
                "retry_after_seconds": 900.0,
            },
        )

    # ── 8. Mark success, fire webhook, return ─────────────────────────────
    await update_lead_success(db, lead.id, replies_raw)
    await db.commit()

    # Fire-and-forget webhook
    await fire_lead_webhook(lead)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "lead_magnet_success",
        lead_id=lead.id,
        ip=ip_address,
        duration_ms=duration_ms,
    )

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "cached": False,
            "replies": replies_raw,
        },
    )
