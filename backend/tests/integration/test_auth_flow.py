"""Integration tests for auth dependencies — Sprint 3 gate.

Tests cover:
  1. get_current_user — valid token → user returned
  2. get_current_user — missing Authorization header → 403
  3. get_current_user — expired/invalid token → 401
  4. TOKEN_REVOKED — jti blacklisted in Redis → 401
  5. Injection guard — token.iat < user.password_changed_at → 401
  6. require_active_user — deactivated user → 401
  7. require_verified_user — unverified email → 403
  8. require_admin — non-admin user → 403
  9. require_admin — admin user → 200
 10. require_credits — zero credits → 402
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.utils.jwt_utils import blacklist_jti

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# 1. Valid token → returns user
# ---------------------------------------------------------------------------


async def test_valid_token_returns_user(client: AsyncClient, test_user: User, make_access_token):
    token, _jti = make_access_token(test_user)
    resp = await client.get("/test/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(test_user.id)
    assert data["email"] == test_user.email


# ---------------------------------------------------------------------------
# 2. Missing Authorization header → 403
# ---------------------------------------------------------------------------


async def test_missing_auth_header_returns_403(client: AsyncClient):
    resp = await client.get("/test/me")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. Invalid/expired token → 401
# ---------------------------------------------------------------------------


async def test_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get("/test/me", headers={"Authorization": "Bearer totally-invalid-token"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "AUTHENTICATION_FAILED"


# ---------------------------------------------------------------------------
# 4. TOKEN_REVOKED — jti blacklisted → 401
# ---------------------------------------------------------------------------


async def test_token_revoked_jti_blacklisted(client: AsyncClient, test_user: User, make_access_token, fake_redis):
    """jti blacklist is checked on every request — blacklisted jti → 401."""
    token, jti = make_access_token(test_user)

    # First request should succeed
    resp = await client.get("/test/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # Blacklist the jti
    await blacklist_jti(jti, ttl_seconds=3600, redis=fake_redis)

    # Same token should now be rejected
    resp = await client.get("/test/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTHENTICATION_FAILED"
    assert "revoked" in data["error"].lower()


# ---------------------------------------------------------------------------
# 5. Injection guard — iat < password_changed_at → 401
# ---------------------------------------------------------------------------


async def test_injection_guard_iat_before_password_change(client: AsyncClient, test_user: User, make_access_token, db_session):
    """Token issued before password_changed_at is rejected."""
    token, _jti = make_access_token(test_user)

    # Set password_changed_at to the future (simulating a security reset)
    from sqlalchemy import update

    await db_session.execute(update(User).where(User.id == test_user.id).values(password_changed_at=datetime.now(UTC) + timedelta(seconds=60)))
    await db_session.commit()

    # Token was issued before password_changed_at → 401
    resp = await client.get("/test/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTHENTICATION_FAILED"
    assert "security reset" in data["error"].lower()


# ---------------------------------------------------------------------------
# 6. require_active_user — deactivated → 401
# ---------------------------------------------------------------------------


async def test_deactivated_user_returns_401(client: AsyncClient, test_user: User, make_access_token, db_session):
    token, _jti = make_access_token(test_user)

    from sqlalchemy import update

    await db_session.execute(update(User).where(User.id == test_user.id).values(is_active=False))
    await db_session.commit()

    resp = await client.get("/test/active", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTHENTICATION_FAILED"


# ---------------------------------------------------------------------------
# 7. require_verified_user — unverified → 403
# ---------------------------------------------------------------------------


async def test_unverified_user_returns_403(client: AsyncClient, test_user: User, make_access_token, db_session):
    token, _jti = make_access_token(test_user)

    from sqlalchemy import update

    await db_session.execute(update(User).where(User.id == test_user.id).values(email_verified=False))
    await db_session.commit()

    resp = await client.get("/test/verified", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 8. require_admin — non-admin → 403
# ---------------------------------------------------------------------------


async def test_non_admin_returns_403(client: AsyncClient, test_user: User, make_access_token):
    token, _jti = make_access_token(test_user)
    resp = await client.get("/test/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == "FORBIDDEN"
    assert "admin" in data["error"].lower()


# ---------------------------------------------------------------------------
# 9. require_admin — admin user → 200
# ---------------------------------------------------------------------------


async def test_admin_user_returns_200(client: AsyncClient, admin_user: User, make_access_token):
    token, _jti = make_access_token(admin_user)
    resp = await client.get("/test/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["admin"] is True


# ---------------------------------------------------------------------------
# 10. require_credits — zero credits → 402
# ---------------------------------------------------------------------------


async def test_zero_credits_returns_402(client: AsyncClient, test_user: User, make_access_token, db_session):
    token, _jti = make_access_token(test_user)

    from sqlalchemy import update

    await db_session.execute(update(User).where(User.id == test_user.id).values(credit_balance=0))
    await db_session.commit()

    resp = await client.get("/test/credits", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 402
    data = resp.json()
    assert data["code"] == "INSUFFICIENT_CREDITS"
