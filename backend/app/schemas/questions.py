"""Question, action item, and saved interpretation schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Nested ---


class CitationItem(BaseModel):
    circular_number: str
    verbatim_quote: str
    section_reference: str | None = None


class RecommendedAction(BaseModel):
    team: str
    action_text: str
    priority: str = Field(pattern=r"^(HIGH|MEDIUM|LOW)$")


# --- Question Requests ---


class QuestionRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)


class FeedbackRequest(BaseModel):
    feedback: int = Field(ge=-1, le=1, description="-1=thumbs down, 1=thumbs up")
    comment: str | None = Field(default=None, max_length=2000)


# --- Question Responses ---


class QuestionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_text: str
    quick_answer: str | None = None
    risk_level: str | None = None
    confidence_score: float | None = None
    consult_expert: bool = False
    model_used: str | None = None
    feedback: int | None = None
    credit_deducted: bool
    created_at: datetime


class QuestionDetail(QuestionSummary):
    answer_text: str | None = None
    prompt_version: str | None = None
    affected_teams: list[str] | None = None
    citations: list[CitationItem] | None = None
    recommended_actions: list[RecommendedAction] | None = None
    streaming_completed: bool
    latency_ms: int | None = None


class QuestionResponse(BaseModel):
    success: bool = True
    data: QuestionDetail
    credit_balance: int


class QuestionListResponse(BaseModel):
    success: bool = True
    data: list[QuestionSummary]
    total: int
    page: int
    page_size: int


class QuestionSuggestionItem(BaseModel):
    id: uuid.UUID
    question_text: str
    quick_answer_preview: str | None = None


class QuestionSuggestionListResponse(BaseModel):
    success: bool = True
    data: list[QuestionSuggestionItem]


# --- Action Item Requests ---


class ActionItemCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    assigned_team: str | None = Field(default=None, max_length=100)
    priority: str = Field(default="MEDIUM", pattern=r"^(HIGH|MEDIUM|LOW)$")
    due_date: date | None = None
    source_question_id: uuid.UUID | None = None
    source_circular_id: uuid.UUID | None = None


class ActionItemUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    assigned_team: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, pattern=r"^(HIGH|MEDIUM|LOW)$")
    due_date: date | None = None
    status: str | None = Field(default=None, pattern=r"^(PENDING|IN_PROGRESS|COMPLETED)$")


# --- Action Item Responses ---


class ActionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    assigned_team: str | None = None
    priority: str
    due_date: date | None = None
    status: str
    source_question_id: uuid.UUID | None = None
    source_circular_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    # Computed in the router — True when due_date is past and status != COMPLETED.
    is_overdue: bool = False


class ActionItemListResponse(BaseModel):
    success: bool = True
    data: list[ActionItemResponse]
    total: int
    page: int
    page_size: int


class ActionItemStatsResponse(BaseModel):
    """Aggregate counts for the current user's action items."""

    success: bool = True
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    overdue: int = 0


# --- Saved Interpretation Requests ---


class SaveInterpretationRequest(BaseModel):
    question_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    tags: list[str] | None = None


class SavedInterpretationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tags: list[str] | None = None


# --- Saved Interpretation Responses ---


class SavedInterpretationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    name: str
    tags: list[str] | None = None
    needs_review: bool
    created_at: datetime


class SavedInterpretationDetailResponse(SavedInterpretationResponse):
    question: QuestionDetail | None = None


class SavedInterpretationListResponse(BaseModel):
    success: bool = True
    data: list[SavedInterpretationResponse]
    total: int
    page: int
    page_size: int
