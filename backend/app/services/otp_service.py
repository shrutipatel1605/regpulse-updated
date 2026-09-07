"""OTP generation, storage, and verification service.

OTPs are stored in Redis (not the database) with configurable TTL.
Rate-limiting (max sends per hour) is tracked via a Redis sorted set.
Attempt counting locks the OTP after max failures.
Only domain names are logged — never full email addresses or OTP values.
"""

from __future__ import annotations

import secrets

import bcrypt
import redis.asyncio as aioredis
import structlog

from app.config import Settings, get_settings
from app.exceptions import OTPRateLimitError, OTPVerificationError

logger = structlog.get_logger(__name__)

# Redis key patterns
_KEY_OTP = "otp:{email}:{purpose}"  # stores bcrypt hash
_KEY_ATTEMPTS = "otp_attempts:{email}:{purpose}"  # integer counter
_KEY_RATE = "otp_rate:{email}"  # sorted set of send timestamps


class OTPService:
    """Generate, store, and verify one-time passwords via Redis."""

    def __init__(
        self,
        redis: aioredis.Redis | None = None,  # type: ignore[type-arg]
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._redis = redis
        self._expiry_seconds = self._settings.OTP_EXPIRY_MINUTES * 60
        self._max_attempts = self._settings.OTP_MAX_ATTEMPTS
        self._max_sends_per_hour = self._settings.OTP_MAX_SENDS_PER_HOUR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_otp(
        self,
        email: str,
        purpose: str = "login",
    ) -> str:
        """Generate a 6-digit OTP, store bcrypt hash in Redis, return plaintext.

        Raises ``OTPRateLimitError`` if the email has exceeded the hourly send
        limit.
        """
        redis = await self._get_redis()
        domain = email.rsplit("@", 1)[-1] if "@" in email else "unknown"

        # --- Rate-limit check (sliding window, 1 hour) ---
        rate_key = _KEY_RATE.format(email=email)
        await self._enforce_rate_limit(redis, rate_key, domain)

        # --- Generate OTP ---
        if self._settings.DEMO_MODE:
            otp = "123456"
            logger.info("demo_mode_fixed_otp", domain=domain, purpose=purpose)
        else:
            otp = f"{secrets.randbelow(1_000_000):06d}"

        # --- Bcrypt hash and store ---
        otp_hash = bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()
        otp_key = _KEY_OTP.format(email=email, purpose=purpose)
        attempts_key = _KEY_ATTEMPTS.format(email=email, purpose=purpose)

        pipe = redis.pipeline()
        pipe.set(otp_key, otp_hash, ex=self._expiry_seconds)
        pipe.set(attempts_key, "0", ex=self._expiry_seconds)
        await pipe.execute()

        logger.info("otp_generated", domain=domain, purpose=purpose)
        return otp

    async def verify_otp(
        self,
        email: str,
        otp: str,
        purpose: str = "login",
    ) -> bool:
        """Verify an OTP. Returns ``True`` on success, clears OTP to prevent reuse.

        Raises ``OTPVerificationError`` if the OTP is invalid, expired, or
        the maximum number of attempts has been exceeded.
        """
        redis = await self._get_redis()
        domain = email.rsplit("@", 1)[-1] if "@" in email else "unknown"

        otp_key = _KEY_OTP.format(email=email, purpose=purpose)
        attempts_key = _KEY_ATTEMPTS.format(email=email, purpose=purpose)

        # --- Check stored hash exists ---
        stored_hash: str | None = await redis.get(otp_key)
        if stored_hash is None:
            logger.warning("otp_verify_no_pending", domain=domain, purpose=purpose)
            raise OTPVerificationError("No pending OTP or OTP has expired")

        # --- Check attempt count ---
        attempts_raw: str | None = await redis.get(attempts_key)
        attempts = int(attempts_raw) if attempts_raw else 0
        if attempts >= self._max_attempts:
            # Lock out — delete OTP so user must request a new one
            await redis.delete(otp_key, attempts_key)
            logger.warning("otp_locked_max_attempts", domain=domain, purpose=purpose)
            raise OTPVerificationError("Maximum verification attempts exceeded; request a new OTP")

        # --- Verify ---
        if bcrypt.checkpw(otp.encode(), stored_hash.encode()):
            # Success — clear OTP and attempts (no reuse)
            await redis.delete(otp_key, attempts_key)
            logger.info("otp_verified", domain=domain, purpose=purpose)
            return True

        # Increment attempt counter
        await redis.incr(attempts_key)
        remaining = self._max_attempts - attempts - 1
        logger.warning(
            "otp_verify_failed",
            domain=domain,
            purpose=purpose,
            remaining_attempts=remaining,
        )
        raise OTPVerificationError(f"Invalid OTP; {remaining} attempt(s) remaining")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:  # type: ignore[type-arg]
        if self._redis is not None:
            return self._redis
        # Lazy import to avoid circular dependency at module level
        from app.cache import redis_client

        self._redis = redis_client
        return self._redis

    async def _enforce_rate_limit(
        self,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        rate_key: str,
        domain: str,
    ) -> None:
        """Enforce sliding-window rate limit using a Redis sorted set."""
        import time

        now = time.time()
        window_start = now - 3600  # 1-hour window

        pipe = redis.pipeline()
        # Remove entries older than 1 hour
        pipe.zremrangebyscore(rate_key, "-inf", window_start)
        # Count remaining entries
        pipe.zcard(rate_key)
        results = await pipe.execute()
        count: int = results[1]

        if count >= self._max_sends_per_hour:
            logger.warning("otp_rate_limited", domain=domain, count=count)
            raise OTPRateLimitError(f"Maximum {self._max_sends_per_hour} OTP requests per hour; try again later")

        # Record this send
        await redis.zadd(rate_key, {str(now): now})
        await redis.expire(rate_key, 3600)
