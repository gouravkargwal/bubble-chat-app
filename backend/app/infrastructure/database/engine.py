import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.infrastructure.metrics import db_connections_in_use

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


# Track pool pressure — export checked-out connection count to Prometheus
def _update_connection_gauge(pool) -> None:
    """Refresh the Prometheus gauge with the current checked-out count."""
    total = getattr(pool, "checkedout", lambda: 0)()
    db_connections_in_use.set(total)


@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(dbapi_connection, connection_record, connection_proxy):
    _update_connection_gauge(engine.pool)


@event.listens_for(engine.sync_engine, "checkin")
def _on_checkin(dbapi_connection, connection_record):
    _update_connection_gauge(engine.pool)


# Also track the librarian (NullPool) engine — NullPool creates/closes connections per checkout.
@event.listens_for(librarian_engine.sync_engine, "checkout")
def _on_librarian_checkout(dbapi_connection, connection_record, connection_proxy):
    _update_connection_gauge(librarian_engine.pool)


@event.listens_for(librarian_engine.sync_engine, "checkin")
def _on_librarian_checkin(dbapi_connection, connection_record):
    _update_connection_gauge(librarian_engine.pool)


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    from app.infrastructure.database.models import Base

    async with engine.begin() as conn:
        # pgvector type is only available after this; initdb scripts also run it on fresh volumes.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session  # type: ignore[misc]
