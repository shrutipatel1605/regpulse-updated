"""Async SQLAlchemy engine, session factory, and get_db() dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_settings = get_settings()

_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "echo": (_settings.ENVIRONMENT == "dev"),
}
# pool_size / max_overflow not supported by SQLite
if not _settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(_settings.DATABASE_URL, **_engine_kwargs)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession and auto-closes."""
    async with async_session_factory() as session:
        yield session
