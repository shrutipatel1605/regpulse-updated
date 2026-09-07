"""Action items router — CRUD for user action items.

Action items are auto-generated from Q&A recommended_actions,
or manually created by users.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models.question import ActionItem
from app.models.user import User
from app.schemas.questions import (
    ActionItemCreateRequest,
    ActionItemListResponse,
    ActionItemResponse,
    ActionItemStatsResponse,
    ActionItemUpdateRequest,
)

router = APIRouter(tags=["action-items"])


def _with_overdue(item: ActionItem) -> ActionItemResponse:
    """Serialise an ActionItem, computing ``is_overdue`` on the fly."""
    data = ActionItemResponse.model_validate(item)
    data.is_overdue = bool(item.due_date is not None and item.due_date < date.today() and str(item.status) != "COMPLETED")
    return data


@router.get("", response_model=ActionItemListResponse)
async def list_action_items(
    status: str | None = Query(default=None),
    assigned_team: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> ActionItemListResponse:
    """List action items for the current user."""
    base = select(ActionItem).where(ActionItem.user_id == user.id)
    count_base = select(func.count(ActionItem.id)).where(ActionItem.user_id == user.id)

    if status:
        base = base.where(ActionItem.status == status)
        count_base = count_base.where(ActionItem.status == status)
    if assigned_team:
        base = base.where(ActionItem.assigned_team == assigned_team)
        count_base = count_base.where(ActionItem.assigned_team == assigned_team)
    if priority:
        base = base.where(ActionItem.priority == priority)
        count_base = count_base.where(ActionItem.priority == priority)

    total = (await db.execute(count_base)).scalar() or 0
    stmt = base.order_by(desc(ActionItem.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return ActionItemListResponse(
        data=[_with_overdue(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=ActionItemStatsResponse)
async def action_item_stats(
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> ActionItemStatsResponse:
    """Aggregate counts by status for the current user, plus overdue."""
    # Status counts — one row per distinct status.
    status_stmt = select(ActionItem.status, func.count(ActionItem.id)).where(ActionItem.user_id == user.id).group_by(ActionItem.status)
    counts: dict[str, int] = {}
    for status_value, n in (await db.execute(status_stmt)).all():
        counts[str(status_value)] = int(n)

    # Overdue = due_date in the past AND status != COMPLETED.
    overdue_stmt = select(func.count(ActionItem.id)).where(
        and_(
            ActionItem.user_id == user.id,
            ActionItem.due_date.is_not(None),
            ActionItem.due_date < date.today(),
            ActionItem.status != "COMPLETED",
        )
    )
    overdue = int((await db.execute(overdue_stmt)).scalar() or 0)

    return ActionItemStatsResponse(
        pending=counts.get("PENDING", 0),
        in_progress=counts.get("IN_PROGRESS", 0),
        completed=counts.get("COMPLETED", 0),
        overdue=overdue,
    )


@router.post("", response_model=ActionItemResponse, status_code=201)
async def create_action_item(
    body: ActionItemCreateRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse:
    """Create a new action item."""
    item = ActionItem(
        id=uuid.uuid4(),
        user_id=user.id,
        title=body.title,
        description=body.description,
        assigned_team=body.assigned_team,
        priority=body.priority,
        due_date=body.due_date,
        source_question_id=body.source_question_id,
        source_circular_id=body.source_circular_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _with_overdue(item)


@router.patch("/{item_id}", response_model=ActionItemResponse)
async def update_action_item(
    item_id: uuid.UUID,
    body: ActionItemUpdateRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> ActionItemResponse | dict:
    """Update an action item."""
    stmt = select(ActionItem).where(ActionItem.id == item_id, ActionItem.user_id == user.id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        return {"success": False, "error": "Action item not found", "code": "NOT_FOUND"}

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return _with_overdue(item)


@router.delete("/{item_id}")
async def delete_action_item(
    item_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an action item."""
    stmt = select(ActionItem).where(ActionItem.id == item_id, ActionItem.user_id == user.id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        return {"success": False, "error": "Action item not found", "code": "NOT_FOUND"}

    await db.delete(item)
    await db.commit()
    return {"success": True, "message": "Action item deleted"}
