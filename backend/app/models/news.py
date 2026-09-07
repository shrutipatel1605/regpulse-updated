"""News item model — RSS-ingested market news linked to circulars."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class NewsSource(enum.StrEnum):
    RBI_PRESS = "RBI_PRESS"
    BUSINESS_STANDARD = "BUSINESS_STANDARD"
    LIVEMINT = "LIVEMINT"
    ET_BANKING = "ET_BANKING"


class NewsStatus(enum.StrEnum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_news_items_source_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[NewsSource] = mapped_column(Enum(NewsSource, name="news_source_enum"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(Text)
    raw_html_hash: Mapped[str | None] = mapped_column(String(64))
    linked_circular_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("circular_documents.id", ondelete="SET NULL"),
    )
    linked_entity_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    relevance_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[NewsStatus] = mapped_column(
        Enum(NewsStatus, name="news_status_enum"),
        nullable=False,
        default=NewsStatus.NEW,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)

    linked_circular = relationship("CircularDocument", foreign_keys=[linked_circular_id])
