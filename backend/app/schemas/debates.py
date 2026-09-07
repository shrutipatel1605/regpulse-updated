from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.debate import DebateStatus


class DebateReplyCreate(BaseModel):
    content: str = Field(..., max_length=2000)
    refs_count: int = 0


class DebateReplyResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    refs_count: int
    created_at: datetime
    updated_at: datetime

    # UI helper fields
    who: str | None = None
    role: str | None = None

    class Config:
        from_attributes = True


class DebateThreadCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    source_circular_id: uuid.UUID | None = None
    source_ref: str | None = Field(None, max_length=255)
    tags: list[str] = Field(default_factory=list)


class DebateThreadResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    status: DebateStatus
    source_circular_id: uuid.UUID | None
    source_ref: str | None
    tags: list[str]
    stance_agree: int
    stance_disagree: int
    created_at: datetime
    updated_at: datetime

    replies: list[DebateReplyResponse] = []

    class Config:
        from_attributes = True
