"""Admin manual PDF upload — receive, validate, enqueue for processing."""

from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.admin import AdminAuditLog, ManualUpload
from app.models.user import User
from app.schemas.admin import (
    ManualUploadInitResponse,
    ManualUploadListResponse,
    ManualUploadResponse,
)

router = APIRouter()

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
_REDIS_UPLOAD_TTL = 300  # 5 minutes
_PDF_MAGIC = b"%PDF"


async def _get_bytes_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    """Return a Redis client in bytes mode (no decode_responses) for raw PDF storage."""
    settings = get_settings()
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)  # type: ignore[return-value]


@router.post("/pdf", response_model=ManualUploadInitResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    doc_type: str = Form(default="OTHER"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ManualUploadInitResponse:
    """Accept a PDF upload, validate, store bytes in Redis, and dispatch Celery task."""
    # Validate content type
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        return ManualUploadInitResponse(
            success=False,  # type: ignore[call-arg]
            upload_id=uuid.UUID(int=0),
            message="Only PDF files are accepted",
        )

    # Read and validate
    pdf_bytes = await file.read()

    if len(pdf_bytes) > _MAX_FILE_SIZE:
        return ManualUploadInitResponse(
            success=False,  # type: ignore[call-arg]
            upload_id=uuid.UUID(int=0),
            message=f"File too large ({len(pdf_bytes) // (1024*1024)}MB). Maximum is 20MB.",
        )

    if not pdf_bytes[:4].startswith(_PDF_MAGIC):
        return ManualUploadInitResponse(
            success=False,  # type: ignore[call-arg]
            upload_id=uuid.UUID(int=0),
            message="File does not appear to be a valid PDF",
        )

    upload_id = uuid.uuid4()
    filename = file.filename or "upload.pdf"

    # Create tracking record
    upload_record = ManualUpload(
        id=upload_id,
        admin_id=admin.id,
        filename=filename,
        file_size_bytes=len(pdf_bytes),
        status="PENDING",
    )
    db.add(upload_record)

    # Audit log
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        actor_id=admin.id,
        action="upload_pdf",
        target_table="manual_uploads",
        target_id=upload_id,
        new_value={"filename": filename, "size_bytes": len(pdf_bytes), "doc_type": doc_type},
    )
    db.add(audit)
    await db.commit()

    # Store bytes in Redis (bytes mode)
    r = await _get_bytes_redis()
    try:
        await r.set(f"upload_pdf:{upload_id}", pdf_bytes, ex=_REDIS_UPLOAD_TTL)
    finally:
        await r.aclose()

    # Dispatch Celery task to scraper worker
    try:
        from scraper.tasks import process_uploaded_pdf

        process_uploaded_pdf.delay(
            upload_id=str(upload_id),
            title=title,
            doc_type=doc_type,
            admin_id=str(admin.id),
        )
    except ImportError:
        pass

    return ManualUploadInitResponse(
        upload_id=upload_id,
        message="PDF queued for processing",
    )


@router.get("", response_model=ManualUploadListResponse)
async def list_uploads(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ManualUploadListResponse:
    """List manual uploads with optional status filter."""
    base = select(ManualUpload)
    count_base = select(func.count(ManualUpload.id))

    if status:
        base = base.where(ManualUpload.status == status.upper())
        count_base = count_base.where(ManualUpload.status == status.upper())

    total = (await db.execute(count_base)).scalar() or 0
    stmt = base.order_by(desc(ManualUpload.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    uploads = list(result.scalars().all())

    return ManualUploadListResponse(
        data=[ManualUploadResponse.model_validate(u) for u in uploads],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{upload_id}", response_model=ManualUploadResponse)
async def get_upload(
    upload_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ManualUploadResponse:
    """Get a single upload status (for polling)."""
    upload = await db.get(ManualUpload, upload_id)
    if not upload:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Upload not found")
    return ManualUploadResponse.model_validate(upload)
