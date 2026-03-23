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


def _revenuecat_authorization_ok(header_value: str | None, webhook_secret: str) -> bool:
    """Match RevenueCat's webhook Authorization header.

    RevenueCat sends the dashboard \"Authorization header value\" as the full
    ``Authorization`` header (often the raw secret). We also accept standard
    ``Bearer <secret>`` for compatibility.
    """
    if not header_value:
        return False
    if header_value == webhook_secret:
        return True
    if header_value == f"Bearer {webhook_secret}":
        return True
    return False


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
    if not webhook_secret and settings.environment != "development":
        logger.error(
            "revenuecat_webhook_secret_not_configured",
            message="Webhook rejected: set REVENUECAT_WEBHOOK_SECRET in this environment",
        )
        raise HTTPException(
            status_code=503,
            detail="RevenueCat webhook is not configured on this server.",
        )
    if webhook_secret:
        if not _revenuecat_authorization_ok(authorization, webhook_secret):
            logger.warning(
                "revenuecat_webhook_unauthorized",
                has_authorization_header=bool(authorization),
            )
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse request body
    try:
        body = await request.json()
    except Exception as e:
        logger.error("revenuecat_webhook_invalid_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract event data - RevenueCat webhooks can have different structures / versions
    event_data = body.get("event", {})
    event_type = event_data.get("type") or body.get("type")
    app_user_id = event_data.get("app_user_id") or body.get("app_user_id")

    if not app_user_id:
        logger.warning(
            "revenuecat_webhook_no_user_id",
            event_type=event_type,
            has_event_key=bool(body.get("event")),
        )
        return {"status": "ignored", "reason": "No app_user_id"}

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

    # RevenueCat sometimes sends `entitlement_ids: null` for certain payloads/environments.
    # In that case, we can still infer the tier from the `product_id`.
    def infer_tier_from_product_id(pid: str | None) -> str | None:
        if not pid:
            return None
        val = pid.lower()
        # Priority: premium should win over pro if both substrings ever appear.
        if "premium" in val:
            return "premium"
        if "pro" in val:
            return "pro"
        return None

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

    # If entitlements were missing/empty, fall back to product_id inference.
    if new_tier is None:
        new_tier = infer_tier_from_product_id(product_id)

    # 1) INITIAL_PURCHASE / RENEWAL / PRODUCT_CHANGE → Clean Slate upgrade path
    # FIXED: Added PRODUCT_CHANGE so users who upgrade tiers actually get their new limits.
    if (
        event_type in ("INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE")
        and new_tier is not None
    ):

        await apply_plan_upgrade(
            db=db,
            user_id=user.id,
            new_tier=new_tier,
            billing_period=billing_period,
            webhook_event_type=event_type,
        )

        return {
            "status": "success",
            "user_id": app_user_id,
            "new_tier": new_tier,
            "billing_period": billing_period,
            "message": "Plan upgraded with clean-slate quotas",
        }

    # 2) EXPIRATION: only downgrade if the expiring entitlement matches current tier.
    # We also apply a soft quota reset behavior here so users are never "debt-locked"
    # the moment their paid plan ends.
    if event_type == "EXPIRATION":
        new_tier_exp: str | None = None
        expiring_tier = infer_tier_from_product_id(product_id)
        if user.tier == "premium" and (affects("premium") or expiring_tier == "premium"):
            new_tier_exp = "free"
        elif user.tier == "pro" and (affects("pro") or expiring_tier == "pro"):
            new_tier_exp = "free"

        if new_tier_exp is None:
            return {
                "status": "ignored",
                "reason": "Expiration does not affect current tier",
            }

        old_tier_snapshot = user.tier

        # Downgrade user to free and clear subscription metadata.
        user.tier = new_tier_exp
        user.tier_source = "free"
        user.tier_expires_at = None
        user.plan_period_start = None

        # Apply a grace reset on daily usage if they were above the free limit.
        # This mirrors the downgrade behavior inside apply_plan_upgrade but is
        # triggered by an EXPIRATION event instead of a PRODUCT_CHANGE.
        if user.google_provider_id:
            from datetime import timedelta, timezone

            from app.infrastructure.database.models import UserQuota
            from app.core.tier_config import TIER_CONFIG

            now = datetime.now(timezone.utc)

            quota_result = await db.execute(
                select(UserQuota)
                .where(UserQuota.google_provider_id == user.google_provider_id)
                .with_for_update()
            )
            quota = quota_result.scalar_one_or_none()

            if quota is not None:
                free_cfg = TIER_CONFIG.get("free", TIER_CONFIG["free"])
                free_daily_limit = int(
                    free_cfg["limits"].get("chat_generations_per_day", 0)
                )

                # Always realign reset windows from expiration time so the new
                # free period starts cleanly.
                quota.daily_reset_at = now + timedelta(days=1)
                quota.weekly_reset_at = now + timedelta(weeks=1)

                if free_daily_limit > 0 and quota.daily_usage_count > free_daily_limit:
                    logger.info(
                        "revenuecat_expiration_grace_reset",
                        app_user_id=app_user_id,
                        previous_daily_usage=quota.daily_usage_count,
                        free_daily_limit=free_daily_limit,
                    )
                    quota.daily_usage_count = 0

        await db.commit()

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
    return {
        "status": "ignored",
        "user_id": app_user_id,
        "event_type": event_type,
    }
