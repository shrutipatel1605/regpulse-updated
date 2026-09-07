"""Shared test fixtures — RSA keys, in-memory SQLite, fakeredis, minimal test app."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Generate RSA key pair BEFORE importing anything from app.*
# ---------------------------------------------------------------------------
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_public_pem = (
    _private_key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)

os.environ.update(
    {
        "DATABASE_URL": "sqlite+aiosqlite://",
        "REDIS_URL": "redis://localhost:6379/15",
        "JWT_PRIVATE_KEY": _private_pem,
        "JWT_PUBLIC_KEY": _public_pem,
        "OPENAI_API_KEY": "sk-test-fake",
        "ANTHROPIC_API_KEY": "sk-ant-test-fake",
        "RAZORPAY_KEY_ID": "rzp_test_fake",
        "RAZORPAY_KEY_SECRET": "rzp_secret_fake",
        "RAZORPAY_WEBHOOK_SECRET": "whsec_fake",
        "SMTP_HOST": "smtp.test.local",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@test.local",
        "SMTP_PASS": "test-password",
        "SMTP_FROM": "noreply@regpulse.test",
        "FRONTEND_URL": "http://localhost:3000",
        "ENVIRONMENT": "dev",
    }
)

import fakeredis.aioredis
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache import get_redis
from app.config import get_settings
from app.db import get_db
from app.dependencies.auth import (
    get_current_user,
    require_active_user,
    require_admin,
    require_credits,
    require_verified_user,
)
from app.exceptions import (
    RegPulseException,
    generic_exception_handler,
    regpulse_exception_handler,
)
from app.models import Base
from app.models.user import User

# ---------------------------------------------------------------------------
# Fix SQLite compatibility: remove server_default="now()" and
# replace UUID columns with String for SQLite.
# ---------------------------------------------------------------------------
for table in Base.metadata.tables.values():
    for col in table.columns:
        # Remove server_default="now()" — we'll provide values explicitly
        if col.server_default is not None:
            sd_text = str(col.server_default.arg) if col.server_default.arg else ""
            if "now()" in sd_text:
                col.server_default = None  # type: ignore[assignment]

# Only these tables needed for auth tests (no JSONB/pgvector issues)
_AUTH_TABLES = [Base.metadata.tables["users"], Base.metadata.tables["sessions"]]
if "pending_domain_reviews" in Base.metadata.tables:
    _AUTH_TABLES.append(Base.metadata.tables["pending_domain_reviews"])


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@pytest.fixture
def settings():
    return get_settings()


# ---------------------------------------------------------------------------
# Per-test engine + session factory (avoids event loop binding issues)
# ---------------------------------------------------------------------------
@pytest.fixture
async def _engine():
    # Use native_uuid=False so SQLAlchemy stores UUIDs as strings in SQLite
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Register UUID type adapter for SQLite: store as VARCHAR(32)
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    async with engine.begin() as conn:
        # SQLite doesn't support UUID type natively. Override UUID columns to use String.
        for table in _AUTH_TABLES:
            for col in table.columns:
                if hasattr(col.type, "as_uuid"):
                    col.type = String(36)  # type: ignore[assignment]
        await conn.run_sync(Base.metadata.create_all, tables=_AUTH_TABLES)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=_AUTH_TABLES)
    await engine.dispose()


@pytest.fixture
async def _session_factory(_engine):
    return async_sessionmaker(_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Per-test fake Redis (fresh instance per test — avoids event loop issues)
# ---------------------------------------------------------------------------
@pytest.fixture
async def fake_redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


# ---------------------------------------------------------------------------
# Minimal test app — only registers protected test routes
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(_session_factory, fake_redis):
    app = FastAPI()

    app.add_exception_handler(RegPulseException, regpulse_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    async def _get_db():
        async with _session_factory() as session:
            yield session

    async def _get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis

    @app.get("/test/me")
    async def _me(user: User = Depends(get_current_user)):
        return {"user_id": str(user.id), "email": user.email}

    @app.get("/test/active")
    async def _active(user: User = Depends(require_active_user)):
        return {"user_id": str(user.id), "active": user.is_active}

    @app.get("/test/verified")
    async def _verified(user: User = Depends(require_verified_user)):
        return {"user_id": str(user.id), "verified": user.email_verified}

    @app.get("/test/admin")
    async def _admin(user: User = Depends(require_admin)):
        return {"user_id": str(user.id), "admin": user.is_admin}

    @app.get("/test/credits")
    async def _credits(user: User = Depends(require_credits)):
        return {"user_id": str(user.id), "credits": user.credit_balance}

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test user fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def test_user(_session_factory) -> User:
    async with _session_factory() as session:
        uid = uuid.uuid4()
        user = User(
            id=str(uid),  # type: ignore[arg-type]  # SQLite stores as string
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


@pytest.fixture
async def admin_user(_session_factory) -> User:
    async with _session_factory() as session:
        uid = uuid.uuid4()
        user = User(
            id=str(uid),  # type: ignore[arg-type]
            email="admin@bigbank.com",
            email_verified=True,
            full_name="Admin User",
            credit_balance=10,
            plan="pro",
            is_admin=True,
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
# Token factory
# ---------------------------------------------------------------------------
@pytest.fixture
def make_access_token(settings):
    def _make(user: User, is_admin: bool | None = None):
        from app.utils.jwt_utils import create_access_token

        admin = is_admin if is_admin is not None else user.is_admin
        # user.id may be a string (SQLite) — ensure it's a UUID for jwt_utils
        uid = user.id if isinstance(user.id, uuid.UUID) else uuid.UUID(str(user.id))
        token, jti, _expires = create_access_token(uid, is_admin=admin, settings=settings)
        return token, jti

    return _make


# ---------------------------------------------------------------------------
# Direct DB session for assertions
# ---------------------------------------------------------------------------
@pytest.fixture
async def db_session(_session_factory) -> AsyncSession:
    async with _session_factory() as session:
        yield session
