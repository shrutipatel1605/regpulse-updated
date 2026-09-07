"""Learning model for Team Learnings."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class LearningSourceType(enum.StrEnum):
    QUESTION = "QUESTION"
    CIRCULAR = "CIRCULAR"


class Learning(Base):
    __tablename__ = "learnings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[LearningSourceType | None] = mapped_column(Enum(LearningSourceType, name="learning_source_type_enum"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_ref: Mapped[str | None] = mapped_column(String(255))

    tags: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="learnings")
