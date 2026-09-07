"""Public safe snippet model — shareable, redacted answer previews."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class PublicSnippet(Base):
    __tablename__ = "public_snippets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    snippet_text: Mapped[str] = mapped_column(Text, nullable=False)
    top_citation: Mapped[dict | None] = mapped_column(JSONB)
    consult_expert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)

    question = relationship("Question")
    user = relationship("User")
