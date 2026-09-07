"""Circular document request/response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Nested ---


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    chunk_text: str
    token_count: int


# --- Requests ---


class CircularSearchParams(BaseModel):
    query: str | None = None
    doc_type: str | None = None
    status: str | None = None
    impact_level: str | None = None
    department: str | None = None
    regulator: str | None = None
    tags: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "issued_date"
    sort_order: str = Field(default="desc", pattern=r"^(asc|desc)$")


class HybridSearchRequest(BaseModel):
    """Request body for hybrid (vector + BM25) search."""

    query: str = Field(..., min_length=3, max_length=500)
    doc_type: str | None = None
    status: str | None = Field(default="ACTIVE")
    impact_level: str | None = None
    department: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AutocompleteRequest(BaseModel):
    """Query params for autocomplete."""

    q: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=50)


class CircularUpdateRequest(BaseModel):
    """Admin-only update fields."""

    ai_summary: str | None = None
    pending_admin_review: bool | None = None
    impact_level: str | None = None
    action_deadline: date | None = None
    affected_teams: list[str] | None = None
    tags: list[str] | None = None
    status: str | None = None


# --- Responses ---


class CircularListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    circular_number: str | None = None
    title: str
    doc_type: str
    department: str | None = None
    issued_date: date | None = None
    status: str
    impact_level: str | None = None
    action_deadline: date | None = None
    affected_teams: list[str] | None = None
    tags: list[str] | None = None
    regulator: str
    indexed_at: datetime


class CircularSearchResultItem(CircularListItem):
    """Search result with relevance score."""

    relevance_score: float = 0.0
    snippet: str | None = None


class CircularDetail(CircularListItem):
    effective_date: date | None = None
    rbi_url: str
    ai_summary: str | None = None
    pending_admin_review: bool
    superseded_by: uuid.UUID | None = None
    chunks: list[ChunkResponse] = []
    updated_at: datetime


class CircularListResponse(BaseModel):
    success: bool = True
    data: list[CircularListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UpdatesFeedResponse(CircularListResponse):
    """Recent circulars feed with unread-since-last-visit count."""

    unread_count: int = 0


class CircularSearchResponse(BaseModel):
    success: bool = True
    data: list[CircularSearchResultItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class CircularDetailResponse(BaseModel):
    success: bool = True
    data: CircularDetail


class AutocompleteItem(BaseModel):
    id: uuid.UUID
    circular_number: str | None = None
    title: str
    doc_type: str


class AutocompleteResponse(BaseModel):
    success: bool = True
    data: list[AutocompleteItem]


class DepartmentListResponse(BaseModel):
    success: bool = True
    data: list[str]


class TagListResponse(BaseModel):
    success: bool = True
    data: list[str]
