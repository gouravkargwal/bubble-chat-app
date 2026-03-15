"""Webhook endpoints for external services."""

import structlog
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
    except Exception as e:
        logger.error("revenuecat_webhook_invalid_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract event data - RevenueCat webhooks can have different structures
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

    # Source of Truth: Always use entitlements dictionary to determine tier
    entitlements = event_data.get("entitlements", {})

    # Extract active entitlement IDs (where is_active is explicitly True)
    active_entitlement_ids = []
    if isinstance(entitlements, dict):
        active_entitlement_ids = [
            eid
            for eid, ent_data in entitlements.items()
            if isinstance(ent_data, dict) and ent_data.get("is_active") is True
        ]

    # Determine tier based on priority: premium > pro > free
    # This naturally handles upgrades (premium takes precedence) and expirations (no active = free)
    new_tier = "free"
    if "premium" in active_entitlement_ids:
        new_tier = "premium"
    elif "pro" in active_entitlement_ids:
        new_tier = "pro"

    # Optimization: Skip database update if tier hasn't changed
    if user.tier == new_tier:
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

    # Update user tier
    old_tier = user.tier
    user.tier = new_tier

    # Clear tier_expires_at for RevenueCat-managed subscriptions
    # (RevenueCat handles expiration, so we don't need to track it separately)
    if event_type in ("INITIAL_PURCHASE", "RENEWAL", "RESTORE"):
        user.tier_expires_at = None
        user.tier_source = "purchase"
    elif event_type in ("EXPIRATION", "CANCELLATION"):
        user.tier_expires_at = None

    await db.commit()
    await db.refresh(user)

    logger.info(
        "revenuecat_webhook_tier_updated",
        app_user_id=app_user_id,
        old_tier=old_tier,
        new_tier=new_tier,
        event_type=event_type,
    )

    return {
        "status": "success",
        "user_id": app_user_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
    }
