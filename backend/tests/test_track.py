"""Tests for tracking endpoints (copy and rating)."""

import pytest
from sqlalchemy import select

from tests.conftest import test_session_factory as async_session
from app.infrastructure.database.models import Interaction, User


async def _create_interaction(user_id: str) -> str:
    """Helper: create a test interaction and return its ID."""
    async with async_session() as session:
        interaction = Interaction(
            user_id=user_id,
            direction="quick_reply",
            reply_0="Flirty reply here",
            reply_1="Witty reply here",
            reply_2="Smooth reply here",
            reply_3="Bold reply here",
            llm_model="test-model",
            temperature_used=0.7,
        )
        session.add(interaction)
        await session.commit()
        await session.refresh(interaction)
        return interaction.id


async def _get_user_id() -> str:
    """Helper: look up the test user's internal ID."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.firebase_uid == "firebase-test-uid-001")
        )
        user = result.scalar_one()
        return user.id


@pytest.mark.asyncio
async def test_track_copy_success(authed_client):
    """POST /track/copy updates copied_index on the interaction."""
    user_id = await _get_user_id()
    interaction_id = await _create_interaction(user_id)

    response = await authed_client.post(
        "/api/v1/track/copy",
        json={"interaction_id": interaction_id, "reply_index": 2},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify in DB
    async with async_session() as session:
        result = await session.execute(
            select(Interaction).where(Interaction.id == interaction_id)
        )
        interaction = result.scalar_one()
        assert interaction.copied_index == 2


@pytest.mark.asyncio
async def test_track_copy_not_found(authed_client):
    """POST /track/copy returns 404 for non-existent interaction."""
    response = await authed_client.post(
        "/api/v1/track/copy",
        json={"interaction_id": "non-existent-id", "reply_index": 0},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_track_rating_success(authed_client):
    """POST /track/rating updates rating fields on the interaction."""
    user_id = await _get_user_id()
    interaction_id = await _create_interaction(user_id)

    response = await authed_client.post(
        "/api/v1/track/rating",
        json={
            "interaction_id": interaction_id,
            "reply_index": 1,
            "is_positive": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify in DB
    async with async_session() as session:
        result = await session.execute(
            select(Interaction).where(Interaction.id == interaction_id)
        )
        interaction = result.scalar_one()
        assert interaction.rating_index == 1
        assert interaction.rating_positive is True


@pytest.mark.asyncio
async def test_track_rating_not_found(authed_client):
    """POST /track/rating returns 404 for non-existent interaction."""
    response = await authed_client.post(
        "/api/v1/track/rating",
        json={
            "interaction_id": "non-existent-id",
            "reply_index": 0,
            "is_positive": False,
        },
    )
    assert response.status_code == 404
