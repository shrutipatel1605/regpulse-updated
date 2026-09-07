"""Auth router — register, login (OTP), verify-otp, refresh, logout.

Flow:
  Register: POST /register → validate work email → send OTP → 200
  Login:    POST /login    → check user exists → send OTP → 200
  Verify:   POST /verify-otp → verify OTP → create user (register) or
            update last_login (login) → issue JWT + refresh token → 200
  Refresh:  POST /refresh  → rotate refresh token → issue new JWT → 200
  Logout:   POST /logout   → revoke refresh token, blacklist jti → 200

PII rules: only domain names logged, never full email or OTP values.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Cookie, Depends, Response
from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.config import Settings, get_settings
from app.db import get_db
from app.exceptions import (
    InvalidWorkEmailError,
    OTPVerificationError,
    RegPulseException,
)
from app.models.user import PendingDomainReview, Session, User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    OTPVerifyRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.email_service import EmailService
from app.services.email_validator import WorkEmailValidator
from app.services.otp_service import OTPService
from app.utils.jwt_utils import (
    blacklist_jti,
    create_access_token,
    create_refresh_token,
    decode_token,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Dependency factories & Config overrides
# ---------------------------------------------------------------------------


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=30 * 24 * 3600,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


def _get_email_validator() -> WorkEmailValidator | None:
    if get_settings().DEMO_MODE:
        return None
    return WorkEmailValidator()


def _get_otp_service() -> OTPService:
    return OTPService()


def _get_email_service() -> EmailService:
    return EmailService()


def _domain(email: str) -> str:
    """Extract domain for PII-safe logging."""
    return email.rsplit("@", 1)[-1] if "@" in email else "unknown"


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


@router.post("/register", response_model=MessageResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    validator: WorkEmailValidator | None = Depends(_get_email_validator),
    otp_svc: OTPService = Depends(_get_otp_service),
    email_svc: EmailService = Depends(_get_email_service),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Validate work email, check for duplicates, send registration OTP."""
    email = body.email.lower().strip()
    domain = _domain(email)

    # Bot trap — if honeypot field is filled, silently accept but do nothing
    if body.honeypot:
        logger.warning("bot_suspect_registration", domain=domain)
        return MessageResponse(message="If this is a valid work email, you will receive an OTP.")

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("register_duplicate_email", domain=domain)
        # Return same message to avoid email enumeration
        return MessageResponse(message="If this is a valid work email, you will receive an OTP.")

    # Validate work email (skipped in demo mode)
    if not settings.DEMO_MODE:
        validation = await validator.validate(email)
        if not validation.is_valid:
            raise InvalidWorkEmailError(validation.reason)

        # Flag domain for admin review if MX was inconclusive
        if validation.requires_review:
            exists = await db.execute(select(PendingDomainReview).where(PendingDomainReview.domain == domain))
            if not exists.scalar_one_or_none():
                db.add(PendingDomainReview(domain=domain, email=email, mx_valid=None))
                await db.commit()

    # Store registration data in Redis so verify-otp can create the user
    redis = await otp_svc._get_redis()
    import json

    reg_data = {
        "full_name": body.full_name,
        "designation": body.designation,
        "org_name": body.org_name,
        "org_type": body.org_type,
    }
    await redis.set(
        f"reg_data:{email}",
        json.dumps(reg_data),
        ex=settings.OTP_EXPIRY_MINUTES * 60,
    )

    # Generate and send OTP
    otp = await otp_svc.generate_otp(email, purpose="register")
    if not settings.DEMO_MODE:
        await email_svc.send_otp_email(email, otp, purpose="register")

    logger.info("register_otp_sent", domain=domain, demo_mode=settings.DEMO_MODE)
    return MessageResponse(message="If this is a valid work email, you will receive an OTP.")


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=MessageResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    otp_svc: OTPService = Depends(_get_otp_service),
    email_svc: EmailService = Depends(_get_email_service),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Send login OTP to an existing, active user."""
    email = body.email.lower().strip()
    domain = _domain(email)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.info("login_unknown_email", domain=domain)
        # Same message to avoid email enumeration
        return MessageResponse(message="If you have an account, you will receive an OTP.")

    otp = await otp_svc.generate_otp(email, purpose="login")
    if not settings.DEMO_MODE:
        await email_svc.send_otp_email(email, otp, purpose="login")

    logger.info("login_otp_sent", domain=domain, demo_mode=settings.DEMO_MODE)
    return MessageResponse(message="If you have an account, you will receive an OTP.")


# ---------------------------------------------------------------------------
# POST /verify-otp
# ---------------------------------------------------------------------------


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(
    body: OTPVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
    otp_svc: OTPService = Depends(_get_otp_service),
    email_svc: EmailService = Depends(_get_email_service),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    """Verify OTP. On register: create user. On login: update last_login.
    Issues JWT access token + refresh token.
    """
    email = body.email.lower().strip()
    domain = _domain(email)
    purpose = body.purpose

    # Verify OTP (raises OTPVerificationError on failure)
    await otp_svc.verify_otp(email, body.otp, purpose=purpose)

    if purpose == "register":
        user = await _create_user_from_registration(email, body, db, redis, settings)
        # Send welcome email (fire-and-forget — don't fail the request)
        try:
            await email_svc.send_welcome_email(email, user.full_name)
        except Exception:
            logger.warning("welcome_email_failed", domain=domain)
    else:
        # Login — find existing user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise OTPVerificationError("Account not found or deactivated")
        # Update last_login_at
        await db.execute(update(User).where(User.id == user.id).values(last_login_at=datetime.now(UTC)))
        await db.commit()
        await db.refresh(user)

    # Issue tokens
    tokens, session = await _issue_tokens(user, db, settings)
    _set_refresh_cookie(response, tokens.refresh_token, settings)

    logger.info("auth_success", domain=domain, purpose=purpose)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    """Rotate refresh token: revoke old, issue new JWT + refresh token."""
    if not refresh_token:
        raise _auth_error("Refresh token missing from cookies")

    try:
        payload = decode_token(refresh_token, expected_type="refresh", settings=settings)
    except JWTError as exc:
        raise _auth_error("Invalid or expired refresh token") from exc

    user_id = payload["sub"]
    old_jti = payload["jti"]

    # Check blacklist
    from app.utils.jwt_utils import is_jti_blacklisted

    if await is_jti_blacklisted(old_jti, redis):
        raise _auth_error("Refresh token has been revoked")

    # Load user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise _auth_error("Account not found or deactivated")

    # Revoke old session + create new session in a single DB commit (atomic)
    token_hash = _hash_token(refresh_token)
    result = await db.execute(
        select(Session).where(
            Session.token_hash == token_hash,
            Session.revoked.is_(False),
        )
    )
    old_session = result.scalar_one_or_none()
    if old_session:
        old_session.revoked = True

    # Issue new tokens — _issue_tokens calls db.commit(), flushing both
    # the old session revocation and new session creation atomically
    tokens, _session = await _issue_tokens(user, db, settings)
    _set_refresh_cookie(response, tokens.refresh_token, settings)

    # Blacklist old jti in Redis AFTER successful DB commit
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    remaining = int((exp - datetime.now(UTC)).total_seconds())
    await blacklist_jti(old_jti, remaining, redis)

    logger.info("token_refreshed", domain=_domain(user.email))
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Revoke refresh token and blacklist its jti."""
    _clear_refresh_cookie(response)

    if not refresh_token:
        return MessageResponse(message="Logged out successfully")

    try:
        payload = decode_token(refresh_token, expected_type="refresh", settings=settings)
    except JWTError:
        # Even if token is invalid/expired, return success (idempotent logout)
        return MessageResponse(message="Logged out successfully")

    jti = payload["jti"]

    # Blacklist jti
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    remaining = int((exp - datetime.now(UTC)).total_seconds())
    if remaining > 0:
        await blacklist_jti(jti, remaining, redis)

    # Revoke session in DB
    token_hash = _hash_token(refresh_token)
    await db.execute(update(Session).where(Session.token_hash == token_hash).values(revoked=True))
    await db.commit()

    logger.info("user_logged_out", jti=jti)
    return MessageResponse(message="Logged out successfully")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user_from_registration(
    email: str,
    body: OTPVerifyRequest,
    db: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    settings: Settings,
) -> User:
    """Create a new user from registration data stored in Redis."""
    import json

    reg_data_raw: str | None = await redis.get(f"reg_data:{email}")
    if reg_data_raw:
        reg_data = json.loads(reg_data_raw)
        await redis.delete(f"reg_data:{email}")
    else:
        # Fallback to fields in verify request body
        reg_data = {
            "full_name": body.full_name or "User",
            "designation": body.designation,
            "org_name": body.org_name,
            "org_type": body.org_type,
        }

    user = User(
        email=email,
        email_verified=True,
        full_name=reg_data.get("full_name") or body.full_name or "User",
        designation=reg_data.get("designation") or body.designation,
        org_name=reg_data.get("org_name") or body.org_name,
        org_type=reg_data.get("org_type") or body.org_type,
        credit_balance=settings.FREE_CREDIT_GRANT,
        plan="free",
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _issue_tokens(
    user: User,
    db: AsyncSession,
    settings: Settings,
) -> tuple[TokenResponse, Session]:
    """Create access + refresh tokens and persist the refresh session."""
    access_token, _access_jti, expires_in = create_access_token(user.id, is_admin=user.is_admin, settings=settings)
    refresh_token, _refresh_jti, expires_at = create_refresh_token(user.id, settings=settings)

    # Store refresh token hash in sessions table
    session = Session(
        user_id=user.id,
        token_hash=_hash_token(refresh_token),
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    tokens = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )
    return tokens, session


def _hash_token(token: str) -> str:
    """SHA-256 hash of a token for storage (not bcrypt — refresh tokens are long)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _auth_error(message: str) -> RegPulseException:
    """Return a 401 auth error."""
    err = RegPulseException(message)
    err.http_status = 401
    err.error_code = "AUTHENTICATION_FAILED"
    return err
