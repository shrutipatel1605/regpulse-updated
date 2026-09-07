"""News item schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NewsItemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    relevance_score: float | None = None
    status: str
    linked_circular_id: uuid.UUID | None = None
    created_at: datetime


class NewsItemDetail(NewsItemSummary):
    linked_entity_ids: list[uuid.UUID] = Field(default_factory=list)


class NewsListResponse(BaseModel):
    items: list[NewsItemSummary]
    total: int
    page: int
    page_size: int


class NewsStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(NEW|REVIEWED|DISMISSED)$")
