from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.environment == "development")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# LangGraph runs sync nodes inside asyncio.to_thread() with a fresh event loop per librarian
# fetch (see agent.nodes_v2._shared.fetch_librarian_context). Reusing the pooled `engine` from
# those loops returns asyncpg connections bound to the wrong loop → "Future attached to a
# different loop" on the main FastAPI session. NullPool gives a dedicated connection per session
# checkout and closes it, so nothing leaks into the main pool.
librarian_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=settings.environment == "development",
)
librarian_async_session = async_sessionmaker(
    librarian_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    from app.infrastructure.database.models import Base

    async with engine.begin() as conn:
        # pgvector type is only available after this; initdb scripts also run it on fresh volumes.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session  # type: ignore[misc]
