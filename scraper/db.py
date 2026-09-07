"""Synchronous SQLAlchemy engine and session for Celery workers.

Standalone scraper module. NEVER imports from backend/app/.
Uses psycopg2 (sync) — Celery workers are synchronous.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from scraper.config import get_scraper_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.scraper.db")

# ---------------------------------------------------------------------------
# Engine (lazy singleton)
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine():  # noqa: ANN202
    """Create or return the cached sync SQLAlchemy engine."""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        return _engine

    settings = get_scraper_settings()

    # Convert async URL to sync if needed (asyncpg → psycopg2)
    db_url = settings.DATABASE_URL
    if "postgresql+asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    _engine = create_engine(
        db_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    logger.info("scraper_db_engine_created", pool_size=5, max_overflow=10)
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    """Create or return the cached session factory."""
    global _SessionLocal  # noqa: PLW0603
    if _SessionLocal is not None:
        return _SessionLocal
    _SessionLocal = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Provide a transactional database session scope.

    Usage::

        with get_db_session() as session:
            session.execute(...)
            session.commit()
    """
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """Quick connectivity check — returns True if the DB is reachable."""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.error("db_connection_check_failed", exc_info=True)
        return False
