"""Shared test fixtures."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.models import Base

# ---------------------------------------------------------------------------
# Test database – in-memory SQLite so we never need PostgreSQL running locally
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _override_get_db():
    """Yield a test database session."""
    async with test_session_factory() as session:
        yield session


# Fake Firebase decoded token for tests
FAKE_FIREBASE_DECODED = {
    "uid": "firebase-test-uid-001",
    "email": "test@example.com",
    "name": "Test User",
}


@pytest.fixture
async def app():
    """Create a test app with fresh database tables."""
    # Import here so the production engine import doesn't fail the test module
    from app.main import create_app
    from app.infrastructure.database.engine import get_db

    # Create all tables on the test engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_app = create_app()
    test_app.dependency_overrides[get_db] = _override_get_db

    yield test_app

    # Cleanup: drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(app):
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authed_client(client):
    """Client with auth token (Firebase auth mocked)."""
    with patch(
        "app.infrastructure.auth.firebase.verify_firebase_token",
        return_value=FAKE_FIREBASE_DECODED,
    ):
        response = await client.post(
            "/api/v1/auth/firebase",
            json={"firebase_token": "fake-token"},
        )
    data = response.json()
    token = data["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
