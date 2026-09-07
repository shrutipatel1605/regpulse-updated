"""Question, action item, and saved interpretation models."""

import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ActionItemStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_embedding = mapped_column(Vector(3072))
    answer_text: Mapped[str | None] = mapped_column(Text)
    quick_answer: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str | None] = mapped_column(String(10))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    consult_expert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommended_actions: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    affected_teams: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    citations: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    chunks_used: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    model_used: Mapped[str | None] = mapped_column(String(50))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    feedback: Mapped[int | None] = mapped_column(SmallInteger)
    feedback_comment: Mapped[str | None] = mapped_column(Text)
    admin_override: Mapped[str | None] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    credit_deducted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    streaming_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("question_clusters.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="questions")  # noqa: F821
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="source_question",
        foreign_keys="ActionItem.source_question_id",
    )
    saved_interpretations: Mapped[list["SavedInterpretation"]] = relationship(back_populates="question", cascade="all, delete")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_question_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"))
    source_circular_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("circular_documents.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assigned_team: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ActionItemStatus] = mapped_column(
        Enum(ActionItemStatus, name="action_item_status_enum"),
        default=ActionItemStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    source_question: Mapped["Question | None"] = relationship(back_populates="action_items", foreign_keys=[source_question_id])


class SavedInterpretation(Base):
    __tablename__ = "saved_interpretations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    question: Mapped["Question"] = relationship(back_populates="saved_interpretations")
