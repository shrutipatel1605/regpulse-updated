"""FastAPI auth dependencies — JWT decoding, jti blacklist, role checks.

Every protected route uses one of these as a ``Depends()`` parameter.
The dependency chain is:

    get_current_user          → decode JWT, check jti blacklist, check iat
    require_active_user       → get_current_user + is_active check
    require_verified_user     → require_active_user + email_verified check
    require_admin             → require_active_user + is_admin check
    require_credits           → require_verified_user + credit_balance > 0

jti blacklist is checked on **every** request — not just at login.
Injection guard: token.iat < user.password_changed_at → 401.
"""

from __future__ import annotations

from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.config import Settings, get_settings
from app.db import get_db
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InsufficientCreditsError,
)
from app.models.user import User
from app.utils.jwt_utils import decode_token, is_jti_blacklisted

logger = structlog.get_logger(__name__)

# HTTPBearer extracts "Bearer <token>" from the Authorization header.
# auto_error=True → returns 403 if header is missing (FastAPI default).
_bearer_scheme = HTTPBearer(auto_error=True)


# ---------------------------------------------------------------------------
# get_current_user — base dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
    settings: Settings = Depends(get_settings),
) -> User:
    """Decode JWT access token, check jti blacklist, load user from DB.

    Raises ``AuthenticationError`` on any failure.
    """
    token = credentials.credentials

    # 1. Decode and verify signature + type
    try:
        payload = decode_token(token, expected_type="access", settings=settings)
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc

    user_id: str = payload.get("sub", "")
    jti: str = payload.get("jti", "")
    iat: int | float | None = payload.get("iat")

    if not user_id or not jti:
        raise AuthenticationError("Malformed token payload")

    # 2. Check jti blacklist (checked on EVERY request)
    if await is_jti_blacklisted(jti, redis):
        raise AuthenticationError("Token has been revoked")

    # 3. Load user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found")

    # 4. Injection guard: token.iat < user.password_changed_at → 401
    if user.password_changed_at is not None and iat is not None:
        token_issued_at = datetime.fromtimestamp(iat, tz=UTC)
        # Ensure password_changed_at is timezone-aware for comparison
        pwd_changed = user.password_changed_at
        if pwd_changed.tzinfo is None:
            pwd_changed = pwd_changed.replace(tzinfo=UTC)
        if token_issued_at < pwd_changed:
            logger.warning(
                "token_issued_before_security_reset",
                user_id=str(user.id),
                token_iat=token_issued_at.isoformat(),
                security_reset=user.password_changed_at.isoformat(),
            )
            raise AuthenticationError("Token issued before security reset; please log in again")

    return user


# ---------------------------------------------------------------------------
# require_active_user
# ---------------------------------------------------------------------------


async def require_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user's account is active."""
    if not user.is_active:
        raise AuthenticationError("Account has been deactivated")
    return user


# ---------------------------------------------------------------------------
# require_verified_user
# ---------------------------------------------------------------------------


async def require_verified_user(
    user: User = Depends(require_active_user),
) -> User:
    """Ensure the authenticated user's email is verified."""
    if not user.email_verified:
        raise AuthorizationError("Email verification required")
    return user


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------


async def require_admin(
    user: User = Depends(require_active_user),
) -> User:
    """Ensure the authenticated user is an admin."""
    if not user.is_admin:
        raise AuthorizationError("Admin access required")
    return user


# ---------------------------------------------------------------------------
# require_credits
# ---------------------------------------------------------------------------


async def require_credits(
    user: User = Depends(require_verified_user),
) -> User:
    """Ensure the authenticated user has at least one credit remaining."""
    if user.credit_balance <= 0:
        raise InsufficientCreditsError()
    return user
