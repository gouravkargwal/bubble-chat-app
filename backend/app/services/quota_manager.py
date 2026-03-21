"""Centralized quota management using user_quotas table.

This module is the single source of truth for usage limits. It MUST NOT
depend on chat history row counts (Interaction, etc.).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import UserQuota


class QuotaExceededException(Exception):
    """Raised when a user exceeds their allowed quota."""


class QuotaManager:
    """Manages per-user quotas backed by the user_quotas table.

    All limit checks MUST go through this class so we never accidentally
    reintroduce SELECT COUNT(*)-based limits.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_or_create_quota(
        self, google_provider_id: str, *, lock: bool = False
    ) -> UserQuota:
        """Fetch the quota row; optionally apply a row-level lock (FOR UPDATE)."""
        stmt = select(UserQuota).where(
            UserQuota.google_provider_id == google_provider_id
        )
        if lock:
            # Prevents the "double-tap" race where two requests overspend quota.
            stmt = stmt.with_for_update()

        result = await self._db.execute(stmt)
        quota = result.scalar_one_or_none()
        if quota is None:
            now = datetime.now(timezone.utc)
            quota = UserQuota(
                google_provider_id=google_provider_id,
                daily_usage_count=0,
                weekly_usage_count=0,
                weekly_audits_count=0,
                weekly_blueprints_count=0,
                daily_reset_at=now + timedelta(days=1),
                weekly_reset_at=now + timedelta(weeks=1),
                weekly_audits_reset_at=now + timedelta(weeks=1),
                weekly_blueprints_reset_at=now + timedelta(weeks=1),
            )
            self._db.add(quota)
            # Flush so concurrent readers inside the same transaction see it.
            await self._db.flush()
        return quota

    @staticmethod
    def _maybe_reset_chat_windows(quota: UserQuota, now: datetime) -> bool:
        """Reset daily/weekly chat windows if needed. Returns True if any reset occurred."""
        reset = False
        # Daily chat
        if quota.daily_reset_at is None or now >= quota.daily_reset_at:
            quota.daily_usage_count = 0
            quota.daily_reset_at = now + timedelta(days=1)
            reset = True

        # Weekly chat
        if quota.weekly_reset_at is None or now >= quota.weekly_reset_at:
            quota.weekly_usage_count = 0
            quota.weekly_reset_at = now + timedelta(weeks=1)
            reset = True

        return reset

    @staticmethod
    def _maybe_reset_audit_windows(quota: UserQuota, now: datetime) -> bool:
        """Reset weekly profile-audit window if needed. Returns True if reset occurred."""
        if quota.weekly_audits_reset_at is None or now >= quota.weekly_audits_reset_at:
            quota.weekly_audits_count = 0
            quota.weekly_audits_reset_at = now + timedelta(weeks=1)
            return True
        return False

    @staticmethod
    def _maybe_reset_blueprint_windows(quota: UserQuota, now: datetime) -> bool:
        """Reset weekly blueprint window if needed. Returns True if reset occurred."""
        if (
            quota.weekly_blueprints_reset_at is None
            or now >= quota.weekly_blueprints_reset_at
        ):
            quota.weekly_blueprints_count = 0
            quota.weekly_blueprints_reset_at = now + timedelta(weeks=1)
            return True
        return False

    async def get_usage(self, google_provider_id: str) -> Tuple[int, int, int, int]:
        """Return (daily_chat, weekly_chat, weekly_audits, weekly_blueprints) AFTER any resets."""
        now = datetime.now(timezone.utc)
        # No lock for a simple read.
        quota = await self._get_or_create_quota(google_provider_id, lock=False)

        reset_chats = self._maybe_reset_chat_windows(quota, now)
        reset_audits = self._maybe_reset_audit_windows(quota, now)
        reset_blueprints = self._maybe_reset_blueprint_windows(quota, now)

        if reset_chats or reset_audits or reset_blueprints:
            # Persist reset so subsequent requests don't redo the math.
            await self._db.commit()

        return (
            quota.daily_usage_count,
            quota.weekly_usage_count,
            quota.weekly_audits_count,
            quota.weekly_blueprints_count,
        )

    async def check_and_increment(
        self,
        google_provider_id: str,
        *,
        daily_limit: int,
        weekly_limit: int | None = None,
    ) -> Tuple[int, int]:
        """Check limits, raise if exceeded, and increment counters on success.

        Returns (new_daily_usage, new_weekly_usage) AFTER increment.
        """
        now = datetime.now(timezone.utc)
        # Lock row so concurrent calls can't overspend.
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        self._maybe_reset_chat_windows(quota, now)

        # Interpret 0 or negative as "unlimited".
        effective_daily_limit = max(daily_limit, 0)

        if (
            effective_daily_limit > 0
            and quota.daily_usage_count >= effective_daily_limit
        ):
            raise QuotaExceededException(
                f"Daily quota exceeded for {google_provider_id}"
            )

        if weekly_limit is not None and weekly_limit > 0:
            if quota.weekly_usage_count >= weekly_limit:
                raise QuotaExceededException(
                    f"Weekly quota exceeded for {google_provider_id}"
                )

        # Increment on success.
        quota.daily_usage_count += 1
        quota.weekly_usage_count += 1

        # Caller is responsible for committing.
        return quota.daily_usage_count, quota.weekly_usage_count

    async def check_only(
        self,
        google_provider_id: str,
        *,
        daily_limit: int,
        weekly_limit: int | None = None,
    ) -> None:
        """Check limits and raise if exceeded, but do NOT increment.

        Use this before running the agent. Call increment() after success.
        """
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=False)
        self._maybe_reset_chat_windows(quota, now)

        effective_daily_limit = max(daily_limit, 0)
        if effective_daily_limit > 0 and quota.daily_usage_count >= effective_daily_limit:
            raise QuotaExceededException(
                f"Daily quota exceeded for {google_provider_id}"
            )

        if weekly_limit is not None and weekly_limit > 0:
            if quota.weekly_usage_count >= weekly_limit:
                raise QuotaExceededException(
                    f"Weekly quota exceeded for {google_provider_id}"
                )

    async def increment(self, google_provider_id: str) -> Tuple[int, int]:
        """Increment usage counters after a successful generation.

        Returns (new_daily_usage, new_weekly_usage) AFTER increment.
        Caller is responsible for committing.
        """
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        self._maybe_reset_chat_windows(quota, now)
        quota.daily_usage_count += 1
        quota.weekly_usage_count += 1
        return quota.daily_usage_count, quota.weekly_usage_count

    async def check_and_increment_audits(
        self,
        google_provider_id: str,
        *,
        weekly_limit: int,
    ) -> int:
        """Check weekly profile-audit limit and increment on success.

        Returns new weekly audit count after increment.
        """
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        self._maybe_reset_audit_windows(quota, now)

        if weekly_limit > 0 and quota.weekly_audits_count >= weekly_limit:
            raise QuotaExceededException(
                f"Weekly profile-audit quota exceeded for {google_provider_id}"
            )

        quota.weekly_audits_count += 1
        return quota.weekly_audits_count

    async def check_and_increment_blueprints(
        self,
        google_provider_id: str,
        *,
        weekly_limit: int,
    ) -> int:
        """Check weekly profile-blueprint limit and increment on success.

        Returns new weekly blueprint count after increment.
        """
        now = datetime.now(timezone.utc)
        quota = await self._get_or_create_quota(google_provider_id, lock=True)
        self._maybe_reset_blueprint_windows(quota, now)

        if weekly_limit > 0 and quota.weekly_blueprints_count >= weekly_limit:
            raise QuotaExceededException(
                f"Weekly blueprint quota exceeded for {google_provider_id}"
            )

        quota.weekly_blueprints_count += 1
        return quota.weekly_blueprints_count
