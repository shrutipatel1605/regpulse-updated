"""Admin circulars management — approve summaries, update metadata."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.admin import AdminAuditLog
from app.models.circular import CircularDocument
from app.models.user import User
from app.schemas.circulars import CircularListItem, CircularListResponse, CircularUpdateRequest

router = APIRouter()


@router.get("/pending-summaries", response_model=CircularListResponse)
async def list_pending_summaries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CircularListResponse:
    """List circulars with pending AI summary review."""
    import math

    base = select(CircularDocument).where(CircularDocument.pending_admin_review.is_(True))
    count_base = select(func.count(CircularDocument.id)).where(CircularDocument.pending_admin_review.is_(True))

    total = (await db.execute(count_base)).scalar() or 0
    stmt = base.order_by(desc(CircularDocument.indexed_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    circulars = list(result.scalars().all())

    return CircularListResponse(
        data=[CircularListItem.model_validate(c) for c in circulars],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.patch("/{circular_id}")
async def update_circular(
    circular_id: uuid.UUID,
    body: CircularUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update circular metadata (admin only)."""
    stmt = select(CircularDocument).where(CircularDocument.id == circular_id)
    result = await db.execute(stmt)
    circular = result.scalar_one_or_none()

    if circular is None:
        return {"success": False, "error": "Circular not found", "code": "CIRCULAR_NOT_FOUND"}

    old_values = {}
    new_values = {}
    updates = body.model_dump(exclude_unset=True)

    for field, value in updates.items():
        old_values[field] = str(getattr(circular, field))
        setattr(circular, field, value)
        new_values[field] = str(value)

    if new_values:
        audit = AdminAuditLog(
            id=uuid.uuid4(),
            actor_id=admin.id,
            action="update_circular",
            target_table="circular_documents",
            target_id=circular_id,
            old_value=old_values,
            new_value=new_values,
        )
        db.add(audit)

    await db.commit()
    return {"success": True, "message": "Circular updated"}


@router.post("/{circular_id}/approve-summary")
async def approve_summary(
    circular_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve AI-generated summary for public display."""
    stmt = select(CircularDocument).where(CircularDocument.id == circular_id)
    result = await db.execute(stmt)
    circular = result.scalar_one_or_none()

    if circular is None:
        return {"success": False, "error": "Circular not found", "code": "CIRCULAR_NOT_FOUND"}

    circular.pending_admin_review = False

    audit = AdminAuditLog(
        id=uuid.uuid4(),
        actor_id=admin.id,
        action="approve_summary",
        target_table="circular_documents",
        target_id=circular_id,
        new_value={"pending_admin_review": False},
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "message": "Summary approved"}
