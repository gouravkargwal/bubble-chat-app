import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# echo=False: echo=True attaches SQLAlchemy's own StreamHandler (plain text), which bypasses
# app JSON logging and duplicates lines in Loki. Use logging.getLogger("sqlalchemy.engine") instead.
engine = create_async_engine(settings.database_url, echo=False)

# LangGraph runs sync nodes inside asyncio.to_thread() with a fresh event loop per librarian
# fetch (see agent.nodes_v2._shared.fetch_librarian_context). Reusing the pooled `engine` from
# those loops returns asyncpg connections bound to the wrong loop → "Future attached to a
# different loop" on the main FastAPI session. NullPool gives a dedicated connection per session
# checkout and closes it, so nothing leaks into the main pool.
librarian_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=False,
)
librarian_async_session = async_sessionmaker(
    librarian_engine, class_=AsyncSession, expire_on_commit=False
)


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    from app.infrastructure.database.models import Base

    async with engine.begin() as conn:
        # pgvector type is only available after this; initdb scripts also run it on fresh volumes.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # pg_trgm trigram similarity for fuzzy graph-entity matching.
        # See docker/migrations/007_pg_trgm.sql (applied idempotently here at startup).
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        # Apply idempotent SQL migrations on every startup.
        # Each uses IF [NOT] EXISTS / ADD COLUMN IF NOT EXISTS so it's safe to re-run.
        await conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS archetype_counts TEXT NOT NULL DEFAULT '{}'"))  # 002
        await conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS dimension_counts TEXT NOT NULL DEFAULT '{}'"))  # 003
        await conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS photo_persona VARCHAR(64) NOT NULL DEFAULT ''"))  # 004
        await conn.execute(text("ALTER TABLE conversation_memories ADD COLUMN IF NOT EXISTS lexical_expansion TEXT DEFAULT ''"))  # 006
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN NOT NULL DEFAULT TRUE"))  # 009
        # ── 010_remove_ltd.sql: drop unused LTD columns (idempotent) ──────────
        await conn.execute(text("ALTER TABLE user_quotas DROP COLUMN IF EXISTS is_ltd"))
        await conn.execute(text("ALTER TABLE user_quotas DROP COLUMN IF EXISTS ltd_refill_credits"))
        await conn.execute(text("ALTER TABLE user_quotas DROP COLUMN IF EXISTS ltd_refill_days"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session  # type: ignore[misc]
