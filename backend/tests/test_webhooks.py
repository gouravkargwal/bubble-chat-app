"""Tests for RevenueCat webhook endpoint."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.infrastructure.database.models import User
from tests.conftest import test_session_factory


async def _create_user(
    user_id: str | None = None,
    tier: str = "free",
    device_id: str | None = None,
) -> User:
    """Helper: create a user in the DB and return it."""
    async with test_session_factory() as session:
        user = User(
            id=user_id or str(uuid.uuid4()),
            device_id=device_id or f"device-{uuid.uuid4()}",
            tier=tier,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _get_user(user_id: str) -> User | None:
    """Helper: get a user from the DB."""
    async with test_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_webhook_no_secret_allows_request(client):
    """Webhook should work without secret configured (development mode)."""
    user = await _create_user(user_id="test-user-1", tier="free")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "TEST",
            "entitlements": {},
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "free"


@pytest.mark.asyncio
async def test_webhook_with_secret_requires_auth(client):
    """Webhook should require authorization when secret is configured."""
    with patch("app.config.settings.revenuecat_webhook_secret", "test-secret-123"):
        payload = {
            "event": {
                "app_user_id": "test-user-1",
                "type": "TEST",
                "entitlements": {},
            }
        }

        # Without authorization header
        response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
        assert response.status_code == 401

        # With wrong authorization
        response = await client.post(
            "/api/v1/webhooks/revenuecat",
            json=payload,
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert response.status_code == 401

        # With correct authorization
        response = await client.post(
            "/api/v1/webhooks/revenuecat",
            json=payload,
            headers={"Authorization": "Bearer test-secret-123"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_missing_app_user_id(client):
    """Webhook should return ignored status when app_user_id is missing."""
    payload = {
        "event": {
            "type": "TEST",
            "entitlements": {},
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert "No app_user_id" in data["reason"]


@pytest.mark.asyncio
async def test_webhook_user_not_found(client):
    """Webhook should return ignored status when user doesn't exist."""
    payload = {
        "event": {
            "app_user_id": "non-existent-user-id",
            "type": "TEST",
            "entitlements": {},
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert "User not found" in data["reason"]


@pytest.mark.asyncio
async def test_webhook_premium_entitlement_active(client):
    """Webhook should set tier to premium when premium entitlement is active."""
    user = await _create_user(user_id="test-user-2", tier="free")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "INITIAL_PURCHASE",
            "entitlements": {
                "premium": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                }
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["old_tier"] == "free"
    assert data["new_tier"] == "premium"

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "premium"
    assert updated_user.tier_source == "purchase"
    assert updated_user.tier_expires_at is None


@pytest.mark.asyncio
async def test_webhook_pro_entitlement_active(client):
    """Webhook should set tier to pro when pro entitlement is active."""
    user = await _create_user(user_id="test-user-3", tier="free")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "INITIAL_PURCHASE",
            "entitlements": {
                "pro": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                }
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["old_tier"] == "free"
    assert data["new_tier"] == "pro"

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "pro"


@pytest.mark.asyncio
async def test_webhook_premium_takes_priority_over_pro(client):
    """Webhook should prioritize premium over pro when both are active."""
    user = await _create_user(user_id="test-user-4", tier="pro")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "RENEWAL",
            "entitlements": {
                "premium": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                },
                "pro": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                },
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["old_tier"] == "pro"
    assert data["new_tier"] == "premium"  # Premium should win

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "premium"


@pytest.mark.asyncio
async def test_webhook_no_active_entitlements_sets_free(client):
    """Webhook should set tier to free when no entitlements are active."""
    user = await _create_user(user_id="test-user-5", tier="premium")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "EXPIRATION",
            "entitlements": {
                "premium": {
                    "is_active": False,
                    "expires_date": None,
                },
                "pro": {
                    "is_active": False,
                    "expires_date": None,
                },
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["old_tier"] == "premium"
    assert data["new_tier"] == "free"

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "free"


@pytest.mark.asyncio
async def test_webhook_empty_entitlements_sets_free(client):
    """Webhook should set tier to free when entitlements dictionary is empty."""
    user = await _create_user(user_id="test-user-6", tier="pro")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "CANCELLATION",
            "entitlements": {},
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "free"

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "free"


@pytest.mark.asyncio
async def test_webhook_missing_entitlements_sets_free(client):
    """Webhook should set tier to free when entitlements key is missing."""
    user = await _create_user(user_id="test-user-7", tier="premium")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "TEST",
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "free"

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "free"


@pytest.mark.asyncio
async def test_webhook_tier_unchanged_optimization(client):
    """Webhook should skip database update when tier hasn't changed."""
    user = await _create_user(user_id="test-user-8", tier="premium")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "RENEWAL",
            "entitlements": {
                "premium": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                }
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["old_tier"] == "premium"
    assert data["new_tier"] == "premium"
    assert "Tier unchanged" in data["message"]


@pytest.mark.asyncio
async def test_webhook_initial_purchase_sets_tier_source(client):
    """Webhook should set tier_source to 'purchase' for INITIAL_PURCHASE events."""
    user = await _create_user(user_id="test-user-9", tier="free")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "INITIAL_PURCHASE",
            "entitlements": {
                "pro": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                }
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "pro"
    assert updated_user.tier_source == "purchase"
    assert updated_user.tier_expires_at is None


@pytest.mark.asyncio
async def test_webhook_renewal_sets_tier_source(client):
    """Webhook should set tier_source to 'purchase' for RENEWAL events."""
    user = await _create_user(user_id="test-user-10", tier="pro")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "RENEWAL",
            "entitlements": {
                "premium": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                }
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "premium"
    assert updated_user.tier_source == "purchase"
    assert updated_user.tier_expires_at is None


@pytest.mark.asyncio
async def test_webhook_expiration_clears_tier_expires_at(client):
    """Webhook should clear tier_expires_at for EXPIRATION events."""
    user = await _create_user(user_id="test-user-11", tier="premium")
    # Set tier_expires_at to simulate an existing expiration
    async with test_session_factory() as session:
        user.tier_expires_at = datetime.now(timezone.utc)
        session.add(user)
        await session.commit()

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "EXPIRATION",
            "entitlements": {
                "premium": {
                    "is_active": False,
                }
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "free"
    assert updated_user.tier_expires_at is None


@pytest.mark.asyncio
async def test_webhook_cancellation_clears_tier_expires_at(client):
    """Webhook should clear tier_expires_at for CANCELLATION events."""
    user = await _create_user(user_id="test-user-12", tier="pro")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "CANCELLATION",
            "entitlements": {},
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "free"
    assert updated_user.tier_expires_at is None


@pytest.mark.asyncio
async def test_webhook_invalid_json_returns_400(client):
    """Webhook should return 400 for invalid JSON."""
    response = await client.post(
        "/api/v1/webhooks/revenuecat",
        content="invalid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_entitlement_is_active_false_ignored(client):
    """Webhook should only consider entitlements where is_active is explicitly True."""
    user = await _create_user(user_id="test-user-13", tier="free")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "INITIAL_PURCHASE",
            "entitlements": {
                "premium": {
                    "is_active": False,  # Explicitly False
                    "expires_date": "2026-12-31T23:59:59Z",
                },
                "pro": {
                    # Missing is_active key (should be ignored)
                    "expires_date": "2026-12-31T23:59:59Z",
                },
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "free"  # No active entitlements

    # Verify user tier remains free
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "free"


@pytest.mark.asyncio
async def test_webhook_entitlement_non_dict_ignored(client):
    """Webhook should handle non-dict entitlement values gracefully."""
    user = await _create_user(user_id="test-user-14", tier="free")

    payload = {
        "event": {
            "app_user_id": user.id,
            "type": "INITIAL_PURCHASE",
            "entitlements": {
                "premium": "invalid",  # Not a dict
                "pro": {
                    "is_active": True,
                    "expires_date": "2026-12-31T23:59:59Z",
                },
            },
        }
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "pro"  # Only pro is valid and active

    # Verify user was updated in DB
    updated_user = await _get_user(user.id)
    assert updated_user.tier == "pro"


@pytest.mark.asyncio
async def test_webhook_event_type_in_body_fallback(client):
    """Webhook should handle event type in body root as fallback."""
    user = await _create_user(user_id="test-user-15", tier="free")

    payload = {
        "type": "INITIAL_PURCHASE",  # Type in body root
        "event": {
            "app_user_id": user.id,
            "entitlements": {
                "pro": {
                    "is_active": True,
                },
            },
        },
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "pro"


@pytest.mark.asyncio
async def test_webhook_app_user_id_in_body_fallback(client):
    """Webhook should handle app_user_id in body root as fallback."""
    user = await _create_user(user_id="test-user-16", tier="free")

    payload = {
        "app_user_id": user.id,  # app_user_id in body root
        "event": {
            "type": "INITIAL_PURCHASE",
            "entitlements": {
                "pro": {
                    "is_active": True,
                },
            },
        },
    }

    response = await client.post("/api/v1/webhooks/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["new_tier"] == "pro"
