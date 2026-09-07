"""Account router — DPDP account deletion & data export.

POST /account/request-deletion-otp — send OTP to confirm deletion
PATCH /account/delete — verify OTP, anonymise PII, revoke sessions
GET   /account/export — download all user data as JSON
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.config import Settings, get_settings
from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models.question import ActionItem, Question, SavedInterpretation
from app.models.user import Session, User
from app.schemas.account import (
    DeleteAccountRequest,
    DeleteAccountResponse,
    RequestDeletionOTPResponse,
)
from app.services.email_service import EmailService
from app.services.otp_service import OTPService

router = APIRouter(tags=["account"])
logger = structlog.get_logger("regpulse.account")

_OTP_PURPOSE = "account_deletion"


def _get_otp_service() -> OTPService:
    return OTPService()


def _get_email_service() -> EmailService:
    return EmailService()


def _domain(email: str) -> str:
    return email.rsplit("@", 1)[-1] if "@" in email else "unknown"


# ---------------------------------------------------------------------------
# POST /account/request-deletion-otp
# ---------------------------------------------------------------------------


@router.post("/request-deletion-otp", response_model=RequestDeletionOTPResponse)
async def request_deletion_otp(
    user: User = Depends(require_verified_user),
    otp_svc: OTPService = Depends(_get_otp_service),
    email_svc: EmailService = Depends(_get_email_service),
    settings: Settings = Depends(get_settings),
) -> RequestDeletionOTPResponse:
    """Send an OTP to the user's email to confirm account deletion."""
    otp = await otp_svc.generate_otp(user.email, purpose=_OTP_PURPOSE)

    if not settings.DEMO_MODE:
        await email_svc.send_otp_email(user.email, otp, purpose="login")

    logger.info("deletion_otp_sent", domain=_domain(user.email))
    return RequestDeletionOTPResponse()


# ---------------------------------------------------------------------------
# PATCH /account/delete
# ---------------------------------------------------------------------------


@router.patch("/delete", response_model=DeleteAccountResponse)
async def delete_account(
    body: DeleteAccountRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
    otp_svc: OTPService = Depends(_get_otp_service),
    email_svc: EmailService = Depends(_get_email_service),
    settings: Settings = Depends(get_settings),
) -> DeleteAccountResponse | JSONResponse:
    """Verify OTP → anonymise PII → delete user data → revoke sessions.

    DPDP Act compliance: right to erasure.
    """
    # 1. Verify OTP
    await otp_svc.verify_otp(user.email, body.otp, purpose=_OTP_PURPOSE)

    original_email = user.email
    domain = _domain(original_email)
    logger.info("account_deletion_started", domain=domain, user_id=str(user.id))

    # 2. Send confirmation email BEFORE anonymising (so we still have the address)
    if not settings.DEMO_MODE:
        await email_svc.send_html_email(
            original_email,
            "RegPulse — Account deleted",
            "<p>Your RegPulse account has been deleted and your personal data has been "
            "anonymised as per the DPDP Act. This action cannot be undone.</p>",
            "Your RegPulse account has been deleted and your personal data has been " "anonymised as per the DPDP Act. This action cannot be undone.",
        )

    # 3. Delete user-owned records: saved_interpretations, action_items
    await db.execute(
        select(SavedInterpretation).where(SavedInterpretation.user_id == user.id).execution_options(synchronize_session="fetch"),
    )
    await db.execute(SavedInterpretation.__table__.delete().where(SavedInterpretation.user_id == user.id))
    await db.execute(ActionItem.__table__.delete().where(ActionItem.user_id == user.id))

    # 4. Nullify user_id on questions (preserve for analytics, remove ownership)
    await db.execute(update(Question).where(Question.user_id == user.id).values(user_id=None))

    # 5. Delete all sessions
    await db.execute(Session.__table__.delete().where(Session.user_id == user.id))

    # 6. Anonymise user PII via UPDATE (user may be detached from this session)
    anon_email = f"deleted_{uuid.uuid4().hex[:12]}@deleted.regpulse.com"
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            email=anon_email,
            full_name="Deleted User",
            designation=None,
            org_name=None,
            org_type=None,
            is_active=False,
            deletion_requested_at=datetime.now(UTC),
        )
    )

    await db.commit()
    logger.info("account_deletion_completed", domain=domain, user_id=str(user.id))

    return DeleteAccountResponse()


# ---------------------------------------------------------------------------
# GET /account/export
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_data(
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Export all user data as a downloadable JSON file (DPDP right to portability)."""
    # Questions
    result = await db.execute(select(Question).where(Question.user_id == user.id).order_by(Question.created_at.desc()))
    questions = result.scalars().all()

    # Saved interpretations
    result = await db.execute(
        select(SavedInterpretation).where(SavedInterpretation.user_id == user.id).order_by(SavedInterpretation.created_at.desc())
    )
    saved = result.scalars().all()

    # Action items
    result = await db.execute(select(ActionItem).where(ActionItem.user_id == user.id).order_by(ActionItem.created_at.desc()))
    actions = result.scalars().all()

    export = {
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "plan": user.plan,
            "credit_balance": user.credit_balance,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "answer_text": q.answer_text,
                "quick_answer": q.quick_answer,
                "risk_level": q.risk_level,
                "citations": q.citations,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in questions
        ],
        "saved_interpretations": [
            {
                "id": str(s.id),
                "name": s.name,
                "tags": s.tags,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in saved
        ],
        "action_items": [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "status": a.status.value if a.status else None,
                "priority": a.priority,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in actions
        ],
        "exported_at": datetime.now(UTC).isoformat(),
    }

    return JSONResponse(
        content=export,
        headers={
            "Content-Disposition": f"attachment; filename=regpulse_export_{user.id}.json",
        },
    )
