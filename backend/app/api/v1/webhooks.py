"""Webhook endpoints for external services."""

import structlog
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.tier_config import BILLING_PERIOD_DAYS
from app.infrastructure.database.engine import get_db
from app.infrastructure.database.models import User
from app.services.billing import apply_plan_upgrade

router = APIRouter()
logger = structlog.get_logger()


# Entitlement → tier mapping + LTD detection.
# Add new entitlement IDs here as they are created in the RevenueCat dashboard.
_ENTITLEMENT_TIER: dict[str, str] = {
    "match": "match",
    "crush": "crush",
}

# Entitlement IDs that represent a Lifetime Deal (non-subscription, perpetual).
_LTD_ENTITLEMENTS: frozenset[str] = frozenset({"ltd", "lifetime", "match_ltd"})


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


def _resolve_tier_and_ltd(
    affected_entitlements: list[str],
    product_id: str | None,
) -> tuple[str | None, bool]:
    """Determine (tier, is_ltd) from RevenueCat webhook event data.

    Priority: explicit entitlement mapping > product ID inference.
    """
    for entitlement_id in affected_entitlements:
        tier = _ENTITLEMENT_TIER.get(entitlement_id)
        if tier is not None:
            return tier, entitlement_id in _LTD_ENTITLEMENTS
    # Fallback: infer from product_id.
    if product_id:
        pid = product_id.lower()
        if "ltd" in pid or "lifetime" in pid:
            return "match", True
        if "match" in pid:
            return "match", False
        if "crush" in pid:
            return "crush", False
    return None, False


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

    # ---- Tier mapping + LTD detection ----
    affected_entitlements = event_data.get("entitlement_ids") or []
    if not isinstance(affected_entitlements, list):
        affected_entitlements = []

    product_id: str | None = event_data.get("product_id")
    new_tier, is_ltd = _resolve_tier_and_ltd(affected_entitlements, product_id)

    # Derive billing_period from tier (authoritative) — avoids fragile product_id string matching.
    period_days = BILLING_PERIOD_DAYS.get(new_tier or "", 30)
    billing_period = "weekly" if period_days == 7 else "monthly"

    # 1) INITIAL_PURCHASE / RENEWAL / PRODUCT_CHANGE → Clean Slate upgrade path
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
            is_ltd=is_ltd,
        )

        return {
            "status": "success",
            "user_id": app_user_id,
            "new_tier": new_tier,
            "billing_period": billing_period,
            "is_ltd": is_ltd,
            "message": "Plan upgraded with clean-slate quotas",
        }

    # 2) EXPIRATION: only downgrade if the expiring entitlement matches current tier.
    # LTD entitlements never expire, so they are skipped here.
    if event_type == "EXPIRATION" and not is_ltd:
        new_tier_exp: str | None = None
        for entitlement_id in affected_entitlements:
            t = _ENTITLEMENT_TIER.get(entitlement_id)
            if t and user.tier == t:
                new_tier_exp = "free"
                break
        # Fallback: product ID inference
        if new_tier_exp is None and product_id:
            pid = product_id.lower()
            if "match" in pid and user.tier == "match":
                new_tier_exp = "free"
            elif "crush" in pid and user.tier == "crush":
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

        if user.google_provider_id:
            from app.infrastructure.database.models import UserQuota

            now = datetime.now(timezone.utc)

            quota_result = await db.execute(
                select(UserQuota)
                .where(UserQuota.google_provider_id == user.google_provider_id)
                .with_for_update()
            )
            quota = quota_result.scalar_one_or_none()

            if quota is not None:
                logger.info(
                    "revenuecat_expiration_credits_cleared",
                    app_user_id=app_user_id,
                    credits_cleared=quota.credits_remaining,
                )
                quota.credits_remaining = 0
                quota.credits_period_limit = 0
                quota.credits_reset_at = None
                quota.daily_free_credits_used = 0
                quota.daily_free_reset_at = now + timedelta(days=1)
                # Clear LTD flags if present.
                quota.is_ltd = False
                quota.ltd_refill_credits = 0
                quota.ltd_refill_days = 0

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
