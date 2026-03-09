"""Tests for history and preferences endpoints."""

import pytest
from sqlalchemy import select

from tests.conftest import test_session_factory as async_session
from app.infrastructure.database.models import Interaction, User


@pytest.mark.asyncio
async def test_get_history_empty(authed_client):
    """GET /history returns empty list for a new user with no interactions."""
    response = await authed_client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_history_returns_items(authed_client):
    """GET /history returns interactions after creating them directly in DB."""
    # Look up the user created by authed_client fixture
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.firebase_uid == "firebase-test-uid-001")
        )
        user = result.scalar_one()

        # Create two interactions
        for i in range(2):
            interaction = Interaction(
                user_id=user.id,
                direction="quick_reply",
                reply_0=f"reply 0 for interaction {i}",
                reply_1=f"reply 1 for interaction {i}",
                reply_2=f"reply 2 for interaction {i}",
                reply_3=f"reply 3 for interaction {i}",
                llm_model="test-model",
                temperature_used=0.7,
                person_name=f"Person {i}",
            )
            session.add(interaction)
        await session.commit()

    response = await authed_client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    # Most recent first
    assert data["items"][0]["person_name"] == "Person 1"
    assert data["items"][1]["person_name"] == "Person 0"
    # Check reply structure
    assert len(data["items"][0]["replies"]) == 4
    assert data["items"][0]["direction"] == "quick_reply"


@pytest.mark.asyncio
async def test_delete_history_item(authed_client):
    """DELETE /history/{id} removes the interaction."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.firebase_uid == "firebase-test-uid-001")
        )
        user = result.scalar_one()

        interaction = Interaction(
            user_id=user.id,
            direction="flirty",
            reply_0="a",
            reply_1="b",
            reply_2="c",
            reply_3="d",
            llm_model="test-model",
            temperature_used=0.8,
        )
        session.add(interaction)
        await session.commit()
        await session.refresh(interaction)
        interaction_id = interaction.id

    response = await authed_client.delete(f"/api/v1/history/{interaction_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # Verify it's gone
    response = await authed_client.get("/api/v1/history")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert interaction_id not in ids


@pytest.mark.asyncio
async def test_delete_history_item_wrong_user(authed_client):
    """DELETE /history/{id} returns 404 when interaction belongs to another user."""
    async with async_session() as session:
        # Create a different user and an interaction for them
        other_user = User(
            device_id="other-device-999",
            firebase_uid="other-firebase-uid-999",
            email="other@example.com",
        )
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)

        interaction = Interaction(
            user_id=other_user.id,
            direction="quick_reply",
            reply_0="x",
            reply_1="y",
            reply_2="z",
            reply_3="w",
            llm_model="test-model",
            temperature_used=0.5,
        )
        session.add(interaction)
        await session.commit()
        await session.refresh(interaction)
        interaction_id = interaction.id

    response = await authed_client.delete(f"/api/v1/history/{interaction_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preferences_not_enough_data(authed_client):
    """GET /preferences returns has_enough_data=False when < 20 ratings."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.firebase_uid == "firebase-test-uid-001")
        )
        user = result.scalar_one()

        # Create 5 rated interactions (below 20 threshold)
        for i in range(5):
            interaction = Interaction(
                user_id=user.id,
                direction="quick_reply",
                reply_0="short",
                reply_1="short",
                reply_2="short",
                reply_3="short",
                llm_model="test-model",
                temperature_used=0.7,
                rating_index=0,
                rating_positive=True,
            )
            session.add(interaction)
        await session.commit()

    response = await authed_client.get("/api/v1/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["has_enough_data"] is False
    assert data["total_ratings"] == 5
    assert data["vibe_breakdown"] == []


@pytest.mark.asyncio
async def test_preferences_enough_data(authed_client):
    """GET /preferences returns vibe breakdown when >= 20 ratings."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.firebase_uid == "firebase-test-uid-001")
        )
        user = result.scalar_one()

        # Create 25 rated interactions with varying vibes
        for i in range(25):
            vibe_index = i % 4  # distribute across 4 vibes
            interaction = Interaction(
                user_id=user.id,
                direction="quick_reply",
                reply_0="Hey there, how are you doing today?",
                reply_1="What's up? Wanna hang out sometime soon?",
                reply_2="I was thinking about you all day long",
                reply_3="Bold move but I like where this is going",
                llm_model="test-model",
                temperature_used=0.7,
                rating_index=vibe_index,
                rating_positive=True,
            )
            session.add(interaction)
        await session.commit()

    response = await authed_client.get("/api/v1/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["has_enough_data"] is True
    assert data["total_ratings"] == 25
    assert len(data["vibe_breakdown"]) > 0
    # Verify vibe names are from the known set
    known_vibes = {"Flirty", "Witty", "Smooth", "Bold"}
    for vibe in data["vibe_breakdown"]:
        assert vibe["name"] in known_vibes
        assert 0 <= vibe["percentage"] <= 1.0
