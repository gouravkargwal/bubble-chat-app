"""Tests for promo code endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from tests.conftest import test_session_factory as async_session
from app.infrastructure.database.models import Promo, User


async def _create_promo(
    code: str = "TESTPROMO",
    tier_grant: str = "premium",
    duration_days: int = 7,
    max_uses: int = 100,
    is_active: bool = True,
    new_users_only: bool = False,
    expires_at: datetime | None = None,
) -> str:
    """Helper: create a promo in the DB and return its ID."""
    async with async_session() as session:
        promo = Promo(
            code=code,
            tier_grant=tier_grant,
            duration_days=duration_days,
            max_uses=max_uses,
            is_active=is_active,
            new_users_only=new_users_only,
            expires_at=expires_at,
        )
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo.id


@pytest.mark.asyncio
async def test_apply_promo_success(authed_client):
    """POST /promo/apply with a valid code grants the tier."""
    await _create_promo(code="FREEPRO", tier_grant="pro", duration_days=14)

    response = await authed_client.post(
        "/api/v1/promo/apply",
        json={"code": "FREEPRO"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tier_granted"] == "pro"
    assert data["duration_days"] == 14
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_apply_promo_invalid_code(authed_client):
    """POST /promo/apply with a non-existent code returns 404."""
    response = await authed_client.post(
        "/api/v1/promo/apply",
        json={"code": "DOESNOTEXIST"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_apply_promo_twice(authed_client):
    """POST /promo/apply twice with the same code returns 409."""
    await _create_promo(code="ONCEONLY", tier_grant="premium", duration_days=7)

    # First application
    response = await authed_client.post(
        "/api/v1/promo/apply",
        json={"code": "ONCEONLY"},
    )
    assert response.status_code == 200

    # Second application
    response = await authed_client.post(
        "/api/v1/promo/apply",
        json={"code": "ONCEONLY"},
    )
    assert response.status_code == 409
    assert "already" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_apply_promo_expired(authed_client):
    """POST /promo/apply with an expired code returns 410."""
    yesterday = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    await _create_promo(
        code="EXPIRED1",
        tier_grant="premium",
        duration_days=7,
        expires_at=yesterday,
    )

    response = await authed_client.post(
        "/api/v1/promo/apply",
        json={"code": "EXPIRED1"},
    )
    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()
