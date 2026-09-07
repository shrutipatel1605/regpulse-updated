"""Unit tests for Sprint 8 action items — /stats endpoint and is_overdue.

Covers gaps G-06 (stats) and G-12 (overdue computation).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models import Base
from app.models.question import ActionItem
from app.models.user import User
from app.routers.action_items import router as action_items_router

_TABLES = [Base.metadata.tables[t] for t in ("users", "questions", "circular_documents", "action_items") if t in Base.metadata.tables]


@pytest.fixture
async def _ai_engine():
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
async def _ai_factory(_ai_engine):
    return async_sessionmaker(_ai_engine, expire_on_commit=False)


@pytest.fixture
async def _ai_user(_ai_factory) -> User:
    async with _ai_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="ai@test.com",
            email_verified=True,
            full_name="AI Tester",
            credit_balance=10,
            plan="free",
            is_admin=False,
            is_active=True,
            last_login_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def _ai_client(_ai_factory, _ai_user):
    app = FastAPI()

    async def _get_db():
        async with _ai_factory() as s:
            yield s

    async def _get_user():
        return _ai_user

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_verified_user] = _get_user

    app.include_router(action_items_router, prefix="/api/v1/action-items")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _seed(factory, user: User, items: list[tuple[str, date | None]]) -> None:
    async with factory() as session:
        for status, due in items:
            session.add(
                ActionItem(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    title=f"Item {status}/{due}",
                    status=status,
                    priority="MEDIUM",
                    due_date=due,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_stats_returns_grouped_counts(_ai_client, _ai_factory, _ai_user):
    today = date.today()
    past = today - timedelta(days=2)
    future = today + timedelta(days=5)
    await _seed(
        _ai_factory,
        _ai_user,
        [
            ("PENDING", past),  # overdue
            ("PENDING", future),
            ("IN_PROGRESS", past),  # overdue
            ("IN_PROGRESS", None),
            ("COMPLETED", past),  # overdue-by-date but COMPLETED → excluded
            ("COMPLETED", None),
        ],
    )

    resp = await _ai_client.get("/api/v1/action-items/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] == 2
    assert data["in_progress"] == 2
    assert data["completed"] == 2
    assert data["overdue"] == 2  # only PENDING/IN_PROGRESS past-due count


@pytest.mark.asyncio
async def test_list_includes_is_overdue_flag(_ai_client, _ai_factory, _ai_user):
    today = date.today()
    await _seed(
        _ai_factory,
        _ai_user,
        [
            ("PENDING", today - timedelta(days=1)),
            ("PENDING", today + timedelta(days=10)),
            ("COMPLETED", today - timedelta(days=5)),
        ],
    )

    resp = await _ai_client.get("/api/v1/action-items")
    assert resp.status_code == 200
    items = resp.json()["data"]
    flags = {(it["status"], it["is_overdue"]) for it in items}
    # Past-due PENDING → overdue. Future PENDING → not. Past-due COMPLETED → not.
    assert ("PENDING", True) in flags
    assert ("PENDING", False) in flags
    assert ("COMPLETED", False) in flags
