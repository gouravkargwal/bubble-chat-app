"""Webhook endpoints for external services."""

import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User

router = APIRouter()
logger = structlog.get_logger()


@router.post("/webhooks/revenuecat")
async def revenuecat_webhook(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle RevenueCat webhook events to update user tiers.

    This endpoint is public but requires a secret header for security when configured.
    """
    # Verify webhook secret (optional for development/testing)
    webhook_secret = settings.revenuecat_webhook_secret
    if webhook_secret:
        # Secret is configured - enforce authorization
        if authorization != f"Bearer {webhook_secret}":
            logger.warning(
                "revenuecat_webhook_unauthorized",
                provided_auth=authorization[:20] if authorization else None,
            )
            raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        # No secret configured - log warning but allow request (for development/testing)
        logger.warning(
            "revenuecat_webhook_secret_not_configured",
            message="Webhook secret not configured - allowing request without authentication",
        )

    # Parse request body
    try:
        body = await request.json()
        # Log full raw payload for debugging entitlements / tiers (staging only)
        logger.info("revenuecat_webhook_raw_body", body=body)
    except Exception as e:
        logger.error("revenuecat_webhook_invalid_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract event data - RevenueCat webhooks can have different structures / versions
    event_data = body.get("event", {})
    event_type = event_data.get("type") or body.get("type")
    app_user_id = event_data.get("app_user_id") or body.get("app_user_id")

    if not app_user_id:
        logger.warning("revenuecat_webhook_no_user_id", body=body)
        return {"status": "ignored", "reason": "No app_user_id"}

    logger.info(
        "revenuecat_webhook_received",
        event_type=event_type,
        app_user_id=app_user_id,
    )

    # Find user by app_user_id (which should match our backend user_id)
    result = await db.execute(select(User).where(User.id == app_user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("revenuecat_webhook_user_not_found", app_user_id=app_user_id)
        return {"status": "ignored", "reason": "User not found"}

    # ---- Tier mapping logic ----
    # Webhooks send an array of entitlement_ids (e.g. ["pro"], ["premium"])
    affected_entitlements = event_data.get("entitlement_ids") or []
    if not isinstance(affected_entitlements, list):
        affected_entitlements = []

    # Start from current values
    new_tier: str = user.tier
    new_source: str | None = user.tier_source
    new_plan_period_start: datetime | None = user.plan_period_start

    # Helper: does this event affect a given entitlement id?
    def affects(entitlement_id: str) -> bool:
        return entitlement_id in affected_entitlements

    # purchased_at_ms is the start of the new billing period (from RevenueCat)
    purchased_at_ms = event_data.get("purchased_at_ms")

    # 1) Upgrades / renewals / restores / product changes
    if event_type in (
        "INITIAL_PURCHASE",
        "RENEWAL",
        "RESTORE",
        "UNCANCELLATION",
        "PRODUCT_CHANGE",
    ):
        # Priority: premium > pro
        if affects("premium"):
            new_tier = "premium"
            new_source = "purchase"
        elif affects("pro"):
            new_tier = "pro"
            new_source = "purchase"

        # Reset usage window to the start of this new billing period
        if purchased_at_ms:
            new_plan_period_start = datetime.fromtimestamp(
                purchased_at_ms / 1000, tz=timezone.utc
            )
        else:
            new_plan_period_start = datetime.now(timezone.utc)

    # 2) Expiration: only downgrade if the expiring entitlement matches current tier
    elif event_type == "EXPIRATION":
        if user.tier == "premium" and affects("premium"):
            new_tier = "free"
            new_source = None
            new_plan_period_start = None
        elif user.tier == "pro" and affects("pro"):
            new_tier = "free"
            new_source = None
            new_plan_period_start = None

    # 3) CANCELLATION: ignore for tier changes; access remains until EXPIRATION

    # Optimization: if nothing changed, return early
    if new_tier == user.tier and new_source == user.tier_source and new_plan_period_start == user.plan_period_start:
        logger.info(
            "revenuecat_webhook_tier_unchanged",
            app_user_id=app_user_id,
            tier=new_tier,
            event_type=event_type,
        )
        return {
            "status": "success",
            "user_id": app_user_id,
            "old_tier": user.tier,
            "new_tier": new_tier,
            "message": "Tier unchanged",
        }

    # Persist changes
    old_tier = user.tier
    old_source = user.tier_source

    user.tier = new_tier
    # DB column is NOT NULL, so fall back to a sentinel when clearing source
    user.tier_source = new_source or "free"
    # RevenueCat manages expiration; we do not track an explicit expiry timestamp
    user.tier_expires_at = None
    user.plan_period_start = new_plan_period_start

    await db.commit()
    await db.refresh(user)

    logger.info(
        "revenuecat_webhook_tier_updated",
        app_user_id=app_user_id,
        old_tier=old_tier,
        new_tier=new_tier,
        old_source=old_source,
        new_source=new_source,
        event_type=event_type,
    )

    return {
        "status": "success",
        "user_id": app_user_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "tier_source": new_source,
    }
