"""Admin news router — review/dismiss news items."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.news import NewsItem, NewsStatus
from app.models.user import User
from app.schemas.news import NewsItemSummary, NewsListResponse, NewsStatusUpdate

router = APIRouter(tags=["admin-news"])


@router.get("", response_model=NewsListResponse)
async def list_all_news(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> NewsListResponse:
    """Admin view — includes dismissed items, filterable by status."""
    base = select(NewsItem)
    if status:
        base = base.where(NewsItem.status == status)

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = base.order_by(desc(NewsItem.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return NewsListResponse(
        items=[NewsItemSummary.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{news_id}", response_model=NewsItemSummary)
async def update_news_status(
    news_id: uuid.UUID,
    body: NewsStatusUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> NewsItemSummary | dict:
    stmt = select(NewsItem).where(NewsItem.id == news_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        return {"success": False, "error": "Not found", "code": "NEWS_NOT_FOUND"}

    item.status = NewsStatus(body.status)
    await db.commit()
    await db.refresh(item)
    return NewsItemSummary.model_validate(item)
