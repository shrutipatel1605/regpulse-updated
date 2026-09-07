"""User and session models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.debate import DebateReply, DebateThread


class OrgType(enum.StrEnum):
    BANK = "BANK"
    NBFC = "NBFC"
    COOPERATIVE = "COOPERATIVE"
    PAYMENT_BANK = "PAYMENT_BANK"
    SMALL_FINANCE_BANK = "SMALL_FINANCE_BANK"
    FINTECH = "FINTECH"
    INSURANCE = "INSURANCE"
    OTHER = "OTHER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(255))
    org_name: Mapped[str | None] = mapped_column(String(255))
    org_type: Mapped[OrgType | None] = mapped_column(Enum(OrgType, name="org_type_enum"))
    credit_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bot_suspect: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_credit_alert_sent: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_updates: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete")
    questions: Mapped[list["Question"]] = relationship(back_populates="user", cascade="all, delete")  # noqa: F821
    learnings: Mapped[list["Learning"]] = relationship(back_populates="user", cascade="all, delete")  # noqa: F821
    debates: Mapped[list["DebateThread"]] = relationship(back_populates="user", cascade="all, delete")
    debate_replies: Mapped[list["DebateReply"]] = relationship(back_populates="user", cascade="all, delete")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")


class PendingDomainReview(Base):
    __tablename__ = "pending_domain_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    mx_valid: Mapped[bool | None] = mapped_column(Boolean)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved: Mapped[bool | None] = mapped_column(Boolean)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
