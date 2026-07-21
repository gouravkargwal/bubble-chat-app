"""Webhook endpoints for external services — RevenueCat (subscriptions only).

RevenueCat handles Crush (₹99/week) and Match (₹249/month) subscriptions
sold through Google Play Billing.
"""

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

# Entitlement → tier mapping (subscriptions only, no LTD).
_ENTITLEMENT_TIER: dict[str, str] = {
    "match": "match",
    "crush": "crush",
    "rizz": "rizz",
}


def _revenuecat_authorization_ok(header_value: str | None, webhook_secret: str) -> bool:
    if not header_value:
        return False
    if header_value == webhook_secret:
        return True
    if header_value == f"Bearer {webhook_secret}":
        return True
    return False


def _resolve_tier(product_id: str | None) -> str | None:
    """Infer tier from product_id (subscription products only)."""
    if not product_id:
        return None
    pid = product_id.lower()
    if "rizz" in pid:
        return "rizz"
    if "match" in pid:
        return "match"
    if "crush" in pid:
        return "crush"
    return None


@router.post("/webhooks/revenuecat")
async def revenuecat_webhook(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle RevenueCat webhook events for subscription management.

    Processes:
      - INITIAL_PURCHASE / RENEWAL / PRODUCT_CHANGE: grant subscription tier.
      - EXPIRATION: downgrade user to free.
      - Others (RESTORE, UNCANCELLATION, CANCELLATION): ignored.

    """
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

    try:
        body = await request.json()
    except Exception as e:
        logger.error("revenuecat_webhook_invalid_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON")

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

    result = await db.execute(select(User).where(User.id == app_user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("revenuecat_webhook_user_not_found", app_user_id=app_user_id)
        return {"status": "ignored", "reason": "User not found"}

    # Resolve tier from entitlement_ids or product_id
    entitlement_ids = event_data.get("entitlement_ids") or []
    if not isinstance(entitlement_ids, list):
        entitlement_ids = []

    new_tier: str | None = None
    for eid in entitlement_ids:
        t = _ENTITLEMENT_TIER.get(eid)
        if t is not None:
            new_tier = t
            break
    if new_tier is None:
        new_tier = _resolve_tier(event_data.get("product_id"))

    # Derive billing period
    period_days = BILLING_PERIOD_DAYS.get(new_tier or "", 30)
    billing_period = "weekly" if period_days == 7 else "monthly"

    # 1) INITIAL_PURCHASE / RENEWAL / PRODUCT_CHANGE
    if event_type in ("INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE") and new_tier:

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
            "message": "Subscription upgraded",
        }

    # 2) EXPIRATION
    if event_type == "EXPIRATION" and new_tier:
        # Only downgrade if the expiring entitlement matches current tier
        if user.tier != new_tier:
            return {
                "status": "ignored",
                "reason": "Expiration does not match current tier",
            }

        old_tier = user.tier
        user.tier = "free"
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
                quota.credits_remaining = 0
                quota.credits_period_limit = 0
                quota.credits_reset_at = None
                quota.daily_free_credits_used = 0
                quota.daily_free_reset_at = now + timedelta(days=1)

        await db.commit()

        logger.info(
            "revenuecat_webhook_expired",
            app_user_id=app_user_id,
            old_tier=old_tier,
        )
        return {
            "status": "success",
            "user_id": app_user_id,
            "old_tier": old_tier,
            "new_tier": "free",
            "message": "Subscription expired, tier downgraded",
        }

    # 3) Other event types — ignored
    return {
        "status": "ignored",
        "user_id": app_user_id,
        "event_type": event_type,
    }
