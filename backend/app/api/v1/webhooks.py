"""Webhook endpoints for external services."""

import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User
from app.services.billing import apply_plan_upgrade

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

    # ---- Tier mapping + billing period logic ----
    # Webhooks send an array of entitlement_ids (e.g. ["pro"], ["premium"])
    affected_entitlements = event_data.get("entitlement_ids") or []
    if not isinstance(affected_entitlements, list):
        affected_entitlements = []

    # Helper: does this event affect a given entitlement id?
    def affects(entitlement_id: str) -> bool:
        return entitlement_id in affected_entitlements

    # Determine new tier from entitlements (priority: premium > pro)
    new_tier: str | None = None
    if affects("premium"):
        new_tier = "premium"
    elif affects("pro"):
        new_tier = "pro"

    # Derive billing_period from product_id string
    product_id: str | None = event_data.get("product_id")
    billing_period = "weekly"  # sensible default
    if product_id:
        pid = product_id.lower()
        if "monthly" in pid:
            billing_period = "monthly"
        elif "yearly" in pid or "annual" in pid:
            billing_period = "yearly"
        elif "weekly" in pid:
            billing_period = "weekly"

    # 1) INITIAL_PURCHASE / RENEWAL / PRODUCT_CHANGE → Clean Slate upgrade path
    # FIXED: Added PRODUCT_CHANGE so users who upgrade tiers actually get their new limits.
    if (
        event_type in ("INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE")
        and new_tier is not None
    ):

        # Capture pre-commit tier so we don't touch expired objects after apply_plan_upgrade.
        old_tier_snapshot = user.tier

        await apply_plan_upgrade(
            db=db,
            user_id=user.id,
            new_tier=new_tier,
            billing_period=billing_period,
        )

        logger.info(
            "revenuecat_webhook_tier_updated",
            app_user_id=app_user_id,
            old_tier=old_tier_snapshot,
            new_tier=new_tier,
            event_type=event_type,
            billing_period=billing_period,
        )
        return {
            "status": "success",
            "user_id": app_user_id,
            "new_tier": new_tier,
            "billing_period": billing_period,
            "message": "Plan upgraded with clean-slate quotas",
        }

    # 2) EXPIRATION: only downgrade if the expiring entitlement matches current tier
    if event_type == "EXPIRATION":
        new_tier_exp: str | None = None
        if user.tier == "premium" and affects("premium"):
            new_tier_exp = "free"
        elif user.tier == "pro" and affects("pro"):
            new_tier_exp = "free"

        if new_tier_exp is None:
            return {
                "status": "ignored",
                "reason": "Expiration does not affect current tier",
            }

        old_tier_snapshot = user.tier
        user.tier = new_tier_exp
        user.tier_source = "free"
        user.tier_expires_at = None
        user.plan_period_start = None

        await db.commit()
        # await db.refresh(user) isn't strictly necessary anymore if we just return,
        # but it's safe if you need to use the `user` object later.

        logger.info(
            "revenuecat_webhook_tier_updated",
            app_user_id=app_user_id,
            old_tier=old_tier_snapshot,
            new_tier=new_tier_exp,
            event_type=event_type,
        )
        return {
            "status": "success",
            "user_id": app_user_id,
            "old_tier": old_tier_snapshot,
            "new_tier": new_tier_exp,
            "message": "Subscription expired, tier downgraded",
        }

    # 3) Other event types (RESTORE / UNCANCELLATION / CANCELLATION)
    # Note: CANCELLATION just means auto-renew is off. They keep their tier until EXPIRATION.
    logger.info(
        "revenuecat_webhook_event_ignored",
        app_user_id=app_user_id,
        event_type=event_type,
    )
    return {
        "status": "ignored",
        "user_id": app_user_id,
        "event_type": event_type,
    }
