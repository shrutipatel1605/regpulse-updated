"""Public snippet schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SnippetCreateRequest(BaseModel):
    question_id: uuid.UUID


class SnippetCitation(BaseModel):
    circular_number: str
    verbatim_quote: str
    section_reference: str | None = None


class PublicSnippetResponse(BaseModel):
    """Returned to the snippet owner after creating a snippet."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    snippet_text: str
    top_citation: SnippetCitation | None = None
    consult_expert: bool
    share_url: str
    view_count: int
    revoked: bool
    created_at: datetime


class PublicSnippetView(BaseModel):
    """Returned to the unauthenticated public — minimal payload, no IDs."""

    slug: str
    snippet_text: str
    top_citation: SnippetCitation | None = None
    consult_expert: bool
    register_cta: str = "Register on RegPulse to access the full anti-hallucination compliance answer."
    og_image_url: str
    created_at: datetime


class SnippetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    question_id: uuid.UUID
    snippet_text: str
    consult_expert: bool
    view_count: int
    revoked: bool
    created_at: datetime


class SnippetListResponse(BaseModel):
    items: list[SnippetListItem]
    total: int
