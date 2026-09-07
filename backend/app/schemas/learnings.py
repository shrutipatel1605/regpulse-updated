from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.learning import LearningSourceType


class LearningCreate(BaseModel):
    title: str = Field(..., max_length=500)
    note: str | None = None
    source_type: LearningSourceType | None = None
    source_id: uuid.UUID | None = None
    source_ref: str | None = Field(None, max_length=255)
    tags: list[str] = Field(default_factory=list)
    notify_team: bool = False


class LearningUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    note: str | None = None
    tags: list[str] | None = None


class LearningResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    note: str | None
    source_type: LearningSourceType | None
    source_id: uuid.UUID | None
    source_ref: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    user_initials: str | None = None

    class Config:
        from_attributes = True
