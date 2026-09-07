"""Circular document and chunk models."""

import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class DocType(enum.StrEnum):
    CIRCULAR = "CIRCULAR"
    MASTER_DIRECTION = "MASTER_DIRECTION"
    NOTIFICATION = "NOTIFICATION"
    PRESS_RELEASE = "PRESS_RELEASE"
    GUIDELINE = "GUIDELINE"
    OTHER = "OTHER"


class CircularStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DRAFT = "DRAFT"


class ImpactLevel(enum.StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CircularDocument(Base):
    __tablename__ = "circular_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    circular_number: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[DocType] = mapped_column(Enum(DocType, name="doc_type_enum"), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255))
    issued_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    rbi_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CircularStatus] = mapped_column(
        Enum(CircularStatus, name="circular_status_enum"),
        nullable=False,
        default=CircularStatus.ACTIVE,
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("circular_documents.id", ondelete="SET NULL"))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    pending_admin_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    impact_level: Mapped[ImpactLevel | None] = mapped_column(Enum(ImpactLevel, name="impact_level_enum"))
    action_deadline: Mapped[date | None] = mapped_column(Date)
    affected_teams: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    tags: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    regulator: Mapped[str] = mapped_column(String(20), default="RBI", nullable=False)
    upload_source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="scraper")
    scraper_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scraper_runs.id", ondelete="SET NULL"))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete")
    superseding_doc: Mapped["CircularDocument | None"] = relationship(remote_side="CircularDocument.id")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("circular_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(3072))
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    document: Mapped["CircularDocument"] = relationship(back_populates="chunks")
