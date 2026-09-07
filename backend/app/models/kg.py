"""Knowledge graph entity and relationship models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class KGEntityType(enum.StrEnum):
    CIRCULAR = "CIRCULAR"
    SECTION = "SECTION"
    REGULATION = "REGULATION"
    ENTITY_TYPE = "ENTITY_TYPE"
    AMOUNT = "AMOUNT"
    DATE = "DATE"
    TEAM = "TEAM"
    ORG = "ORG"


class KGRelationType(enum.StrEnum):
    SUPERSEDES = "SUPERSEDES"
    REFERENCES = "REFERENCES"
    AMENDS = "AMENDS"
    APPLIES_TO = "APPLIES_TO"
    MENTIONS = "MENTIONS"
    EFFECTIVE_FROM = "EFFECTIVE_FROM"


class KGEntity(Base):
    __tablename__ = "kg_entities"
    __table_args__ = (UniqueConstraint("entity_type", "canonical_name", name="uq_kg_entities_type_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[KGEntityType] = mapped_column(Enum(KGEntityType, name="kg_entity_type_enum"), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    entity_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="'{}'::jsonb")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)


class KGRelationship(Base):
    __tablename__ = "kg_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relation_type",
            "source_document_id",
            name="uq_kg_relationships_edge",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kg_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kg_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[KGRelationType] = mapped_column(Enum(KGRelationType, name="kg_relation_type_enum"), nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("circular_documents.id", ondelete="CASCADE"),
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)

    source_entity: Mapped["KGEntity"] = relationship(foreign_keys=[source_entity_id])
    target_entity: Mapped["KGEntity"] = relationship(foreign_keys=[target_entity_id])
