"""Knowledge graph schemas (currently internal-only — no public endpoints)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KGEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    canonical_name: str
    aliases: list[str]
    first_seen_at: datetime
    last_seen_at: datetime


class KGRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relation_type: str
    confidence: float
    created_at: datetime
