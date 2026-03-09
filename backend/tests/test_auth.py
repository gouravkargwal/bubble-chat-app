"""Test authentication endpoints."""

from unittest.mock import patch

import pytest

from tests.conftest import FAKE_FIREBASE_DECODED


@pytest.mark.asyncio
async def test_firebase_auth(client):
    """Should authenticate with a valid Firebase token."""
    with patch(
        "app.infrastructure.auth.firebase.verify_firebase_token",
        return_value=FAKE_FIREBASE_DECODED,
    ):
        response = await client.post(
            "/api/v1/auth/firebase",
            json={"firebase_token": "fake-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "user_id" in data
    assert "expires_at" in data
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert data["is_new_user"] is True


@pytest.mark.asyncio
async def test_firebase_auth_same_uid_returns_same_user(client):
    """Same Firebase UID should return same user."""
    with patch(
        "app.infrastructure.auth.firebase.verify_firebase_token",
        return_value=FAKE_FIREBASE_DECODED,
    ):
        r1 = await client.post(
            "/api/v1/auth/firebase",
            json={"firebase_token": "fake-token-1"},
        )
        r2 = await client.post(
            "/api/v1/auth/firebase",
            json={"firebase_token": "fake-token-2"},
        )
    assert r1.json()["user_id"] == r2.json()["user_id"]
    assert r2.json()["is_new_user"] is False


@pytest.mark.asyncio
async def test_firebase_auth_invalid_token(client):
    """Should reject invalid Firebase token."""
    with patch(
        "app.infrastructure.auth.firebase.verify_firebase_token",
        side_effect=ValueError("Invalid Firebase token"),
    ):
        response = await client.post(
            "/api/v1/auth/firebase",
            json={"firebase_token": "bad-token"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_new_user_gets_pro_trial(client):
    """New users should get a Pro trial."""
    with patch(
        "app.infrastructure.auth.firebase.verify_firebase_token",
        return_value=FAKE_FIREBASE_DECODED,
    ):
        response = await client.post(
            "/api/v1/auth/firebase",
            json={"firebase_token": "fake-token"},
        )
    data = response.json()
    assert data["is_new_user"] is True
    assert data["trial_tier"] == "pro"


@pytest.mark.asyncio
async def test_usage_requires_auth(client):
    """Endpoints should reject unauthenticated requests."""
    response = await client.get("/api/v1/usage")
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_usage_with_auth(authed_client):
    response = await authed_client.get("/api/v1/usage")
    assert response.status_code == 200
    data = response.json()
    assert data["daily_used"] == 0
    assert data["is_premium"] is False
