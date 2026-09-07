"""Admin dashboard, review, prompt, and analytics schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Dashboard ---


class DashboardStats(BaseModel):
    total_users: int
    active_users_30d: int
    total_questions: int
    questions_today: int
    total_circulars: int
    pending_reviews: int
    avg_feedback_score: float | None = None
    credits_consumed_30d: int


class DashboardResponse(BaseModel):
    success: bool = True
    data: DashboardStats


# --- User Management ---


class AdminUserListParams(BaseModel):
    search: str | None = None
    plan: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    credit_balance: int | None = Field(default=None, ge=0)
    plan: str | None = None
    bot_suspect: bool | None = None


# --- Question Review ---


class AdminQuestionListParams(BaseModel):
    feedback: int | None = None
    reviewed: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AdminQuestionOverride(BaseModel):
    admin_override: str = Field(min_length=1)


# --- Prompt Versions ---


class PromptVersionCreate(BaseModel):
    version_tag: str = Field(min_length=1, max_length=50)
    prompt_text: str = Field(min_length=1)


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_tag: str
    prompt_text: str
    is_active: bool
    created_by: uuid.UUID | None = None
    created_at: datetime


class PromptVersionListResponse(BaseModel):
    success: bool = True
    data: list[PromptVersionResponse]


# --- Audit Log ---


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    target_table: str | None = None
    target_id: uuid.UUID | None = None
    old_value: dict | None = None
    new_value: dict | None = None
    ip_address: str | None = None
    created_at: datetime


class AuditLogResponse(BaseModel):
    success: bool = True
    data: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


# --- Analytics ---


class AnalyticsEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    event_data: dict | None = None


class AnalyticsEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_hash: str
    event_type: str
    event_data: dict | None = None
    session_id: str | None = None
    created_at: datetime


# --- Scraper Admin ---


class ScraperRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    documents_processed: int
    documents_failed: int
    error_message: str | None = None
    created_at: datetime


class ScraperRunListResponse(BaseModel):
    success: bool = True
    data: list[ScraperRunResponse]
    total: int
    page: int
    page_size: int


# --- Domain Review ---


class DomainReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    email: str
    mx_valid: bool | None = None
    reviewed: bool
    approved: bool | None = None
    created_at: datetime


class DomainReviewAction(BaseModel):
    approved: bool


# --- Manual Uploads ---


class ManualUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_id: uuid.UUID
    filename: str
    file_size_bytes: int
    status: str
    document_id: uuid.UUID | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ManualUploadListResponse(BaseModel):
    success: bool = True
    data: list[ManualUploadResponse]
    total: int
    page: int
    page_size: int


class ManualUploadInitResponse(BaseModel):
    success: bool = True
    upload_id: uuid.UUID
    message: str


# --- Clustering Heatmap ---


class ClusterInfo(BaseModel):
    id: uuid.UUID
    label: str
    question_count: int
    representative_questions: list[str]


class ClusterHeatmapResponse(BaseModel):
    success: bool = True
    clusters: list[ClusterInfo]
    time_buckets: list[str]
    matrix: list[list[int]]


class ClusterTriggerResponse(BaseModel):
    success: bool = True
    message: str
