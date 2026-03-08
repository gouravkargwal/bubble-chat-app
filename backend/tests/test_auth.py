"""Test authentication endpoints."""

import pytest


@pytest.mark.asyncio
async def test_anonymous_auth(client):
    response = await client.post(
        "/api/v1/auth/anonymous",
        headers={"X-Device-ID": "test-device-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "user_id" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_anonymous_auth_same_device(client):
    """Same device ID should return same user."""
    r1 = await client.post(
        "/api/v1/auth/anonymous",
        headers={"X-Device-ID": "same-device"},
    )
    r2 = await client.post(
        "/api/v1/auth/anonymous",
        headers={"X-Device-ID": "same-device"},
    )
    assert r1.json()["user_id"] == r2.json()["user_id"]


@pytest.mark.asyncio
async def test_anonymous_auth_no_device_id(client):
    """Should auto-generate device ID if not provided."""
    response = await client.post("/api/v1/auth/anonymous")
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.asyncio
async def test_usage_requires_auth(client):
    """Endpoints should reject unauthenticated requests."""
    response = await client.get("/api/v1/usage")
    assert response.status_code == 422  # missing header


@pytest.mark.asyncio
async def test_usage_with_auth(authed_client):
    response = await authed_client.get("/api/v1/usage")
    assert response.status_code == 200
    data = response.json()
    assert data["daily_used"] == 0
    assert data["daily_limit"] == 5
    assert data["is_premium"] is False
