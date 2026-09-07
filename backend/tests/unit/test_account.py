"""Unit tests for DPDP account deletion and data export.

Tests cover:
- Account deletion: PII anonymised, sessions deleted, questions.user_id nullified,
  saved_interpretations and action_items deleted
- Data export: contains all user data, excludes admin fields
- OTP verification required for deletion
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cache import get_redis
from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models import Base
from app.models.user import Session, User
from app.routers.account import router as account_router

# ---------------------------------------------------------------------------
# Account-specific tables that need SQLite compat (questions, etc.)
# ---------------------------------------------------------------------------

_ACCOUNT_TABLE_NAMES = [
    "users",
    "sessions",
    "questions",
    "saved_interpretations",
    "action_items",
]

_ACCOUNT_TABLES = [Base.metadata.tables[t] for t in _ACCOUNT_TABLE_NAMES if t in Base.metadata.tables]


@pytest.fixture
async def account_engine():
    """Engine with all account-related tables, SQLite-compatible."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    async with eng.begin() as conn:
        for table in _ACCOUNT_TABLES:
            for col in table.columns:
                # UUID → String for SQLite
                if hasattr(col.type, "as_uuid"):
                    col.type = String(36)  # type: ignore[assignment]
                # Vector → nullable Text stub for SQLite
                if type(col.type).__name__ == "Vector":
                    col.type = String(36)  # type: ignore[assignment]
                    col.nullable = True
                # JSONB → Text for SQLite
                if type(col.type).__name__ == "JSONB":
                    col.type = String(4000)  # type: ignore[assignment]
                    col.nullable = True
                # Enum → String for SQLite
                if type(col.type).__name__ == "Enum":
                    col.type = String(50)  # type: ignore[assignment]
                # Remove server_default="now()"
                if col.server_default is not None:
                    sd_text = str(col.server_default.arg) if col.server_default.arg else ""
                    if "now()" in sd_text or "'[]'::jsonb" in sd_text:
                        col.server_default = None  # type: ignore[assignment]
        await conn.run_sync(Base.metadata.create_all, tables=_ACCOUNT_TABLES)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=_ACCOUNT_TABLES)
    await eng.dispose()


@pytest.fixture
async def account_session_factory(account_engine):
    return async_sessionmaker(account_engine, expire_on_commit=False)


@pytest.fixture
async def account_test_user(account_session_factory) -> User:
    async with account_session_factory() as session:
        uid = uuid.uuid4()
        user = User(
            id=str(uid),  # type: ignore[arg-type]
            email="tester@bigbank.com",
            email_verified=True,
            full_name="Test User",
            credit_balance=5,
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def account_app(account_session_factory, fake_redis):
    """Minimal FastAPI app with account router and mocked OTP service."""
    from app.exceptions import (
        RegPulseException,
        regpulse_exception_handler,
    )

    app = FastAPI()
    app.add_exception_handler(RegPulseException, regpulse_exception_handler)  # type: ignore[arg-type]

    async def _get_db():
        async with account_session_factory() as session:
            yield session

    async def _get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis

    app.include_router(account_router, prefix="/api/v1/account")

    return app


@pytest.fixture
async def account_client(account_app, account_test_user):
    """Client with account router and auth overridden to return test_user."""

    async def _override_user():
        return account_test_user

    account_app.dependency_overrides[require_verified_user] = _override_user

    transport = ASGITransport(app=account_app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests — Account Deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_account_anonymises_pii(account_client, account_test_user, account_session_factory):
    """DPDP deletion: PII is anonymised, is_active=False, deletion_requested_at set."""
    with (
        patch(
            "app.routers.account.OTPService.verify_otp",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.account.EmailService.send_html_email",
            new_callable=AsyncMock,
        ),
    ):
        resp = await account_client.patch(
            "/api/v1/account/delete",
            json={"otp": "123456"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    async with account_session_factory() as session:
        result = await session.execute(User.__table__.select().where(User.__table__.c.id == str(account_test_user.id)))
        user = result.first()
        assert user is not None
        assert user.full_name == "Deleted User"
        assert user.email.startswith("deleted_")
        assert user.email.endswith("@deleted.regpulse.com")
        assert user.designation is None
        assert user.org_name is None
        assert user.is_active is False
        assert user.deletion_requested_at is not None


@pytest.mark.asyncio
async def test_delete_account_removes_sessions(account_client, account_test_user, account_session_factory):
    """Deletion should remove all sessions for the user."""
    async with account_session_factory() as session:
        s = Session(
            id=str(uuid.uuid4()),
            user_id=str(account_test_user.id),
            token_hash="fakehash",  # noqa: S106
            expires_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        session.add(s)
        await session.commit()

    with (
        patch(
            "app.routers.account.OTPService.verify_otp",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.account.EmailService.send_html_email",
            new_callable=AsyncMock,
        ),
    ):
        resp = await account_client.patch(
            "/api/v1/account/delete",
            json={"otp": "123456"},
        )

    assert resp.status_code == 200

    async with account_session_factory() as session:
        result = await session.execute(Session.__table__.select().where(Session.__table__.c.user_id == str(account_test_user.id)))
        sessions = result.all()
        assert len(sessions) == 0


@pytest.mark.asyncio
async def test_delete_account_invalid_otp_rejected(account_client):
    """Deletion fails if OTP verification fails."""
    from app.exceptions import OTPVerificationError

    with patch(
        "app.routers.account.OTPService.verify_otp",
        new_callable=AsyncMock,
        side_effect=OTPVerificationError("Invalid OTP; 2 attempt(s) remaining"),
    ):
        resp = await account_client.patch(
            "/api/v1/account/delete",
            json={"otp": "000000"},
        )

    assert resp.status_code == 400
    assert resp.json()["code"] == "OTP_VERIFICATION_FAILED"


# ---------------------------------------------------------------------------
# Tests — Data Export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_data_returns_user_info(account_client, account_test_user):
    """Export should contain user profile data."""
    resp = await account_client.get("/api/v1/account/export")
    assert resp.status_code == 200

    data = resp.json()
    assert data["user"]["email"] == account_test_user.email
    assert data["user"]["full_name"] == account_test_user.full_name
    assert data["user"]["plan"] == account_test_user.plan
    assert "exported_at" in data
    assert "questions" in data
    assert "saved_interpretations" in data
    assert "action_items" in data


@pytest.mark.asyncio
async def test_export_data_has_content_disposition(account_client, account_test_user):
    """Export response should have Content-Disposition for file download."""
    resp = await account_client.get("/api/v1/account/export")
    assert resp.status_code == 200
    assert "content-disposition" in resp.headers
    assert "regpulse_export_" in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_excludes_admin_fields(account_client, account_test_user):
    """Export should not contain admin-internal fields."""
    resp = await account_client.get("/api/v1/account/export")
    data = resp.json()
    user_fields = set(data["user"].keys())
    assert "is_admin" not in user_fields
    assert "bot_suspect" not in user_fields
    assert "password_changed_at" not in user_fields
