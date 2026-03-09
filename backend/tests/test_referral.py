"""Tests for referral endpoints."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.models import User
from tests.conftest import test_session_factory


FAKE_FIREBASE_DECODED_2 = {
    "uid": "firebase-test-uid-002",
    "email": "user2@example.com",
    "name": "User Two",
}


@pytest.fixture
async def authed_client_2(app):
    """Second authenticated user for referral tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch(
            "app.infrastructure.auth.firebase.verify_firebase_token",
            return_value=FAKE_FIREBASE_DECODED_2,
        ):
            response = await ac.post(
                "/api/v1/auth/firebase",
                json={"firebase_token": "fake-token-2"},
            )
        data = response.json()
        token = data["token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


@pytest.mark.asyncio
async def test_get_referral_me(authed_client):
    """GET /referral/me returns a referral code for the user."""
    response = await authed_client.get("/api/v1/referral/me")
    assert response.status_code == 200
    data = response.json()
    assert "referral_code" in data
    assert len(data["referral_code"]) == 8
    assert data["total_referrals"] == 0
    assert data["bonus_replies_earned"] == 0
    assert data["max_referrals"] == 10


@pytest.mark.asyncio
async def test_get_referral_me_generates_code(authed_client):
    """GET /referral/me generates a code if user doesn't already have one."""
    # Clear the user's referral code first
    from sqlalchemy import select

    async with test_session_factory() as session:
        result = await session.execute(
            select(User).where(User.firebase_uid == "firebase-test-uid-001")
        )
        user = result.scalar_one()
        user.referral_code = None
        await session.commit()

    response = await authed_client.get("/api/v1/referral/me")
    assert response.status_code == 200
    data = response.json()
    # A new code should have been generated
    assert len(data["referral_code"]) == 8


@pytest.mark.asyncio
async def test_apply_referral_success(authed_client, authed_client_2):
    """POST /referral/apply with a valid code grants bonus to both users."""
    # Get user 1's referral code
    response = await authed_client.get("/api/v1/referral/me")
    code = response.json()["referral_code"]

    # User 2 applies user 1's code
    response = await authed_client_2.post(
        "/api/v1/referral/apply",
        json={"code": code},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bonus_granted"] == 5
    assert data["new_total_bonus"] == 5

    # Verify user 1 also got bonus
    response = await authed_client.get("/api/v1/referral/me")
    data = response.json()
    assert data["total_referrals"] == 1
    assert data["bonus_replies_earned"] == 5


@pytest.mark.asyncio
async def test_apply_own_referral_code(authed_client):
    """POST /referral/apply with own code returns 400."""
    # Get the user's own code
    response = await authed_client.get("/api/v1/referral/me")
    code = response.json()["referral_code"]

    response = await authed_client.post(
        "/api/v1/referral/apply",
        json={"code": code},
    )
    assert response.status_code == 400
    assert "own" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_apply_referral_twice(authed_client, authed_client_2):
    """POST /referral/apply twice returns 400 (already referred)."""
    # Get user 1's referral code
    response = await authed_client.get("/api/v1/referral/me")
    code = response.json()["referral_code"]

    # User 2 applies the code once
    response = await authed_client_2.post(
        "/api/v1/referral/apply",
        json={"code": code},
    )
    assert response.status_code == 200

    # User 2 tries to apply again
    response = await authed_client_2.post(
        "/api/v1/referral/apply",
        json={"code": code},
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_apply_invalid_referral_code(authed_client):
    """POST /referral/apply with an invalid code returns 404."""
    response = await authed_client.post(
        "/api/v1/referral/apply",
        json={"code": "ZZZZZZZZ"},
    )
    assert response.status_code == 404
    assert "invalid" in response.json()["detail"].lower()
