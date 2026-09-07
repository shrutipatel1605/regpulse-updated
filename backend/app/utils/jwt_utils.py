"""RS256 JWT creation and verification with jti blacklist via Redis."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
import structlog
from jose import JWTError, jwt

from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)

_ALGORITHM = "RS256"


def create_access_token(
    user_id: uuid.UUID,
    is_admin: bool = False,
    settings: Settings | None = None,
) -> tuple[str, str, int]:
    """Create a signed JWT access token.

    Returns ``(token, jti, expires_in_seconds)``.
    """
    s = settings or get_settings()
    expire_minutes = s.ACCESS_TOKEN_EXPIRE_MINUTES
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "is_admin": is_admin,
        "type": "access",
    }
    token = jwt.encode(payload, s.JWT_PRIVATE_KEY, algorithm=_ALGORITHM)
    return token, jti, expire_minutes * 60


def create_refresh_token(
    user_id: uuid.UUID,
    settings: Settings | None = None,
) -> tuple[str, str, datetime]:
    """Create a signed JWT refresh token.

    Returns ``(token, jti, expires_at)``.
    """
    s = settings or get_settings()
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=s.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "type": "refresh",
    }
    token = jwt.encode(payload, s.JWT_PRIVATE_KEY, algorithm=_ALGORITHM)
    return token, jti, expires_at


def decode_token(
    token: str,
    expected_type: str = "access",
    settings: Settings | None = None,
) -> dict:
    """Decode and verify a JWT. Raises ``JWTError`` on failure."""
    s = settings or get_settings()
    payload = jwt.decode(token, s.JWT_PUBLIC_KEY, algorithms=[_ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload


async def blacklist_jti(
    jti: str,
    ttl_seconds: int,
    redis: aioredis.Redis,  # type: ignore[type-arg]
) -> None:
    """Add a jti to the Redis blacklist with TTL matching token remaining lifetime."""
    key = f"jwt_blacklist:{jti}"
    await redis.set(key, "1", ex=max(ttl_seconds, 1))
    logger.info("jti_blacklisted", jti=jti, ttl=ttl_seconds)


async def is_jti_blacklisted(
    jti: str,
    redis: aioredis.Redis,  # type: ignore[type-arg]
) -> bool:
    """Check if a jti is blacklisted."""
    key = f"jwt_blacklist:{jti}"
    return await redis.exists(key) > 0
