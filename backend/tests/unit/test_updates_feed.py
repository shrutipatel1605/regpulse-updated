"""Unit tests for Sprint 8 updates feed (G-03).

Covers GET /circulars/updates and POST /circulars/updates/mark-seen.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models import Base
from app.models.circular import CircularDocument
from app.models.user import User
from app.routers.circulars import router as circulars_router

_TABLES = [Base.metadata.tables[t] for t in ("users", "circular_documents", "document_chunks", "scraper_runs") if t in Base.metadata.tables]


@pytest.fixture
async def _u_engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng.sync_engine, "connect")
    def _pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with eng.begin() as conn:
        for tbl in _TABLES:
            for col in tbl.columns:
                if hasattr(col.type, "as_uuid"):
                    col.type = String(36)  # type: ignore[assignment]
                if type(col.type).__name__ == "Vector":
                    col.type = String(36)  # type: ignore[assignment]
                    col.nullable = True
                if type(col.type).__name__ == "JSONB":
                    col.type = String(4000)  # type: ignore[assignment]
                    col.nullable = True
                if type(col.type).__name__ == "Enum":
                    col.type = String(50)  # type: ignore[assignment]
                if col.server_default is not None:
                    sd_text = str(col.server_default.arg) if col.server_default.arg else ""
                    if "now()" in sd_text or "'[]'::jsonb" in sd_text:
                        col.server_default = None  # type: ignore[assignment]
        await conn.run_sync(Base.metadata.create_all, tables=_TABLES)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=_TABLES)
    await eng.dispose()


@pytest.fixture
async def _u_factory(_u_engine):
    return async_sessionmaker(_u_engine, expire_on_commit=False)


@pytest.fixture
async def _u_user(_u_factory) -> User:
    async with _u_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="updates@test.com",
            email_verified=True,
            full_name="Updates Tester",
            credit_balance=10,
            plan="free",
            is_admin=False,
            is_active=True,
            # Deliberately leave last_seen_updates None for a first-visit scenario.
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def _u_client(_u_factory, _u_user):
    app = FastAPI()

    async def _get_db():
        async with _u_factory() as s:
            yield s

    async def _get_user():
        # Re-fetch to avoid detached-instance issues between tests.
        async with _u_factory() as s:
            fresh = (await s.execute(select(User).where(User.id == _u_user.id))).scalar_one()
            return fresh

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_verified_user] = _get_user

    app.include_router(circulars_router, prefix="/api/v1/circulars")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _seed_circulars(factory) -> None:
    now = datetime.now(UTC)
    async with factory() as session:
        # Recent: indexed in last 2 days
        for i in range(3):
            session.add(
                CircularDocument(
                    id=str(uuid.uuid4()),
                    title=f"Recent #{i}",
                    doc_type="CIRCULAR",
                    rbi_url=f"https://rbi.org.in/r{i}",
                    status="ACTIVE",
                    impact_level="HIGH" if i == 0 else "MEDIUM",
                    regulator="RBI",
                    upload_source="scraper",
                    indexed_at=now - timedelta(days=1),
                    updated_at=now,
                )
            )
        # Old: indexed 30 days ago — outside the default 7-day window
        session.add(
            CircularDocument(
                id=str(uuid.uuid4()),
                title="Old circular",
                doc_type="CIRCULAR",
                rbi_url="https://rbi.org.in/old",
                status="ACTIVE",
                impact_level="LOW",
                regulator="RBI",
                upload_source="scraper",
                indexed_at=now - timedelta(days=30),
                updated_at=now,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_updates_feed_returns_recent_with_unread_count(_u_client, _u_factory):
    await _seed_circulars(_u_factory)

    resp = await _u_client.get("/api/v1/circulars/updates", params={"days": 7})
    assert resp.status_code == 200
    body = resp.json()
    # Only the 3 recent circulars are in the 7-day window.
    assert body["total"] == 3
    assert len(body["data"]) == 3
    # First-visit user (last_seen_updates=None) sees every circular as unread.
    assert body["unread_count"] == 4


@pytest.mark.asyncio
async def test_updates_feed_filters_by_impact_level(_u_client, _u_factory):
    await _seed_circulars(_u_factory)
    resp = await _u_client.get(
        "/api/v1/circulars/updates",
        params={"days": 7, "impact_level": "HIGH"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["data"][0]["impact_level"] == "HIGH"


@pytest.mark.asyncio
async def test_mark_seen_drops_unread_to_zero(_u_client, _u_factory, _u_user):
    await _seed_circulars(_u_factory)

    resp = await _u_client.post("/api/v1/circulars/updates/mark-seen")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # last_seen_updates is now very close to "now" — no circulars should be newer.
    resp2 = await _u_client.get("/api/v1/circulars/updates", params={"days": 7})
    assert resp2.status_code == 200
    assert resp2.json()["unread_count"] == 0
