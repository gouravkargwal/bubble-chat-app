"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.infrastructure.database.engine import engine, init_db
from app.infrastructure.database.models import Base


@pytest.fixture
async def app():
    """Create a test app with fresh database."""
    test_app = create_app()
    await init_db()
    yield test_app
    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(app):
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authed_client(client):
    """Client with auth token."""
    response = await client.post(
        "/api/v1/auth/anonymous",
        headers={"X-Device-ID": "test-device-001"},
    )
    data = response.json()
    token = data["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
