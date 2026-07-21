"""Centralized quota management using user_quotas table — credits-based system.

Credits system:
- Free users: 10 one-time signup bonus + 2 credits/day forever.
- Paid users: period credit pool (weekly or monthly) set by billing.
- Credit costs: chat_generation=1, profile_audit=8, profile_blueprint=12.
- No daily cap for paid users — they spend from their period pool freely.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tier_config import CREDIT_COSTS, FREE_SIGNUP_CREDITS, FREE_DAILY_CREDITS

FREE_SIGNUP_BONUS_CREDITS = FREE_SIGNUP_CREDITS  # 10 credits
from app.infrastructure.database.models import UserQuota


class QuotaExceededException(Exception):
    """Raised when a user exceeds their allowed quota."""


class QuotaManager:
    """Manages per-user credits backed by the user_quotas table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_or_create_quota(
        self, google_provider_id: str, *, lock: bool = False
    ) -> UserQuota:
        stmt = select(UserQuota).where(
            UserQuota.google_provider_id == google_provider_id
        )
        if lock:
            stmt = stmt.with_for_update()

        result = await self._db.execute(stmt)
        quota = result.scalar_one_or_none()
        if quota is None:
            quota = UserQuota(
                google_provider_id=google_provider_id,
                credits_remaining=0,
                credits_period_limit=0,
                credits_reset_at=None,
                signup_bonus_granted=False,
                daily_free_credits_used=0,
                daily_free_reset_at=None,
            )
            self._db.add(quota)
            await self._db.flush()
        return quota

    def _reset_daily_free_window_if_needed(
        self, quota: UserQuota, now: datetime
    ) -> None:
        """Reset daily free credit window for free tier users."""
        if quota.daily_free_reset_at is None or now >= quota.daily_free_reset_at:
            quota.daily_free_credits_used = 0
            quota.daily_free_reset_at = now + timedelta(days=1)

    def _reset_period_if_needed(self, quota: UserQuota, now: datetime) -> None:
        """Reset/refill credits when the billing period expires.

        Subscriptions: zero the pool when the period ends (no auto-refill).
        """
        if quota.credits_reset_at is not None and now >= quota.credits_reset_at:
            # Subscriptions: zero pool on expiry.
            quota.credits_remaining = 0
            quota.credits_period_limit = 0
            quota.credits_reset_at = None

    async def grant_signup_bonus(self, google_provider_id: str) -> bool:
        """Grant one-time 10-credit signup bonus. Returns True if bonus was newly granted."""
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        if quota.signup_bonus_granted:
            return False
        quota.credits_remaining += FREE_SIGNUP_BONUS_CREDITS
        quota.signup_bonus_granted = True
        await self._db.commit()
        return True

    async def grant_period_credits(
        self,
        google_provider_id: str,
        *,
        credits: int,
        period_days: int,
    ) -> None:
        """Grant a new period credit pool (called by billing webhook on purchase)."""
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        quota.credits_remaining = credits
        quota.credits_period_limit = credits
        quota.credits_reset_at = now + timedelta(days=period_days)
        await self._db.commit()

    async def check_only_credits(
        self,
        google_provider_id: str,
        *,
        action: str,
        tier: str,
        daily_free_limit: int = FREE_DAILY_CREDITS,
    ) -> None:
        """Check if user has credits without deducting. Raises QuotaExceededException if not."""
        now = datetime.now(timezone.utc)
        cost = CREDIT_COSTS.get(action, 1)
        quota = await self._get_or_create_quota(google_provider_id, lock=False)

        if tier == "free":
            # Check signup bonus first.
            if not quota.signup_bonus_granted or quota.credits_remaining >= cost:
                return  # Has bonus credits or will get them on first spend.
            self._reset_daily_free_window_if_needed(quota, now)
            if quota.daily_free_credits_used + cost > daily_free_limit:
                raise QuotaExceededException(
                    "Daily free quota exceeded. Upgrade to get more credits."
                )
        else:
            self._reset_period_if_needed(quota, now)
            if quota.credits_remaining < cost:
                raise QuotaExceededException(
                    f"Insufficient credits. {quota.credits_remaining} remaining, need {cost}."
                )

    async def refund(
        self,
        google_provider_id: str,
        *,
        action: str,
        tier: str,
    ) -> None:
        """Refund credits for a failed job. Restores to credits_remaining for all tiers."""
        cost = CREDIT_COSTS.get(action, 1)
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        quota.credits_remaining += cost
        await self._db.commit()

    async def check_and_spend(
        self,
        google_provider_id: str,
        *,
        action: str,
        tier: str,
        daily_free_limit: int = FREE_DAILY_CREDITS,
        idempotency_key: str | None = None,
    ) -> int:
        """Check if user has enough credits, deduct them, return credits remaining.

        For free tier: checks daily free credits (resets daily).
        For paid tiers: checks period pool.
        idempotency_key: if provided, skip deduction if this key was already processed
        (prevents double-charge on network retries).
        Raises QuotaExceededException if insufficient.
        """
        import json

        now = datetime.now(timezone.utc)
        cost = CREDIT_COSTS.get(action, 1)
        quota = await self._get_or_create_quota(google_provider_id, lock=True)

        # Idempotency check — skip deduction if this key was already processed.
        if idempotency_key:
            try:
                charged_keys: list[str] = json.loads(quota.last_charged_keys or "[]")
            except Exception:
                charged_keys = []
            if idempotency_key in charged_keys:
                # Already charged — return current remaining without deducting again.
                return quota.credits_remaining
            # Record this key (keep last 10 only).
            charged_keys = ([idempotency_key] + charged_keys)[:10]
            quota.last_charged_keys = json.dumps(charged_keys)

        if tier == "free":
            # Grant signup bonus on first use if not yet granted.
            if not quota.signup_bonus_granted:
                quota.credits_remaining = FREE_SIGNUP_BONUS_CREDITS
                quota.signup_bonus_granted = True

            # Check signup bonus pool first.
            if quota.credits_remaining >= cost:
                quota.credits_remaining -= cost
                await self._db.commit()
                return quota.credits_remaining

            # Bonus exhausted — fall back to daily free credits.
            self._reset_daily_free_window_if_needed(quota, now)
            if quota.daily_free_credits_used + cost > daily_free_limit:
                raise QuotaExceededException(
                    f"Daily free quota exceeded. Upgrade to get more credits."
                )
            quota.daily_free_credits_used += cost
            await self._db.commit()
            return max(0, daily_free_limit - quota.daily_free_credits_used)

        else:
            # Paid tier — use period pool.
            self._reset_period_if_needed(quota, now)
            if quota.credits_remaining < cost:
                raise QuotaExceededException(
                    f"Insufficient credits. {quota.credits_remaining} remaining, need {cost}."
                )
            quota.credits_remaining -= cost
            await self._db.commit()
            return quota.credits_remaining

    async def get_credits_remaining(self, google_provider_id: str, tier: str) -> int:
        """Return current credits remaining for display in app."""
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=False)

        if tier == "free":
            if not quota.signup_bonus_granted:
                return FREE_SIGNUP_BONUS_CREDITS
            self._reset_daily_free_window_if_needed(quota, now)
            daily_remaining = max(0, FREE_DAILY_CREDITS - quota.daily_free_credits_used)
            return quota.credits_remaining + daily_remaining
        else:
            self._reset_period_if_needed(quota, now)
            return quota.credits_remaining

    async def get_credits_period_limit(self, google_provider_id: str, tier: str) -> int:
        """Return the total credit pool for 'X of Y' display.

        For free users: same as credits_remaining (signup bonus + daily free),
                        so it shows correctly without a misleading progress bar.
        For paid users: the period credit pool limit (e.g. 60 for Crush/week).
        """
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=False)

        if tier == "free":
            if not quota.signup_bonus_granted:
                return FREE_SIGNUP_BONUS_CREDITS
            self._reset_daily_free_window_if_needed(quota, now)
            daily_remaining = max(0, FREE_DAILY_CREDITS - quota.daily_free_credits_used)
            return quota.credits_remaining + daily_remaining
        else:
            self._reset_period_if_needed(quota, now)
            return quota.credits_period_limit
