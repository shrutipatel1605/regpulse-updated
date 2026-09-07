"""News feed router (Sprint 3 Pillar B).

GET /api/v1/news        — paginated, verified users
GET /api/v1/news/{id}   — detail, verified users
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models.news import NewsItem, NewsStatus
from app.models.user import User
from app.schemas.news import NewsItemDetail, NewsItemSummary, NewsListResponse

router = APIRouter(tags=["news"])


@router.get("", response_model=NewsListResponse)
async def list_news(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source: str | None = Query(default=None),
    only_linked: bool = Query(default=False),
    _user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> NewsListResponse:
    """Paginated news feed. Filters: source, only_linked (linked to circular)."""
    base = select(NewsItem).where(NewsItem.status != NewsStatus.DISMISSED)

    if source:
        base = base.where(NewsItem.source == source)
    if only_linked:
        base = base.where(NewsItem.linked_circular_id.is_not(None))

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = base.order_by(desc(NewsItem.published_at), desc(NewsItem.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return NewsListResponse(
        items=[NewsItemSummary.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{news_id}", response_model=NewsItemDetail)
async def get_news_detail(
    news_id: uuid.UUID,
    _user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> NewsItemDetail | dict:
    stmt = select(NewsItem).where(NewsItem.id == news_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        return {"success": False, "error": "Not found", "code": "NEWS_NOT_FOUND"}
    return NewsItemDetail.model_validate(item)
