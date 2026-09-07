"""Debate model for Team Debates."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class DebateStatus(enum.StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class DebateThread(Base):
    __tablename__ = "debate_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DebateStatus] = mapped_column(Enum(DebateStatus, name="debate_status_enum"), default=DebateStatus.OPEN, nullable=False)

    source_circular_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("circular_documents.id", ondelete="SET NULL"))
    source_ref: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))

    stance_agree: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stance_disagree: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="debates")
    replies: Mapped[list["DebateReply"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class DebateReply(Base):
    __tablename__ = "debate_replies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("debate_threads.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    refs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    thread: Mapped["DebateThread"] = relationship(back_populates="replies")
    user: Mapped["User"] = relationship(back_populates="debate_replies")
