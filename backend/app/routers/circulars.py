"""Circulars router — list, detail, hybrid search, autocomplete, facets.

All endpoints at /api/v1/circulars/ (prefix set in main.py).
Browsing endpoints are public; search requires a verified user.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.exceptions import CircularNotFoundError
from app.models.circular import CircularDocument
from app.models.user import User
from app.schemas.circulars import (
    AutocompleteItem,
    AutocompleteResponse,
    CircularDetail,
    CircularDetailResponse,
    CircularListItem,
    CircularListResponse,
    CircularSearchResponse,
    CircularSearchResultItem,
    DepartmentListResponse,
    TagListResponse,
    UpdatesFeedResponse,
)
from app.services.circular_library_service import CircularLibraryService

router = APIRouter(tags=["circulars"])


# ---------------------------------------------------------------------------
# Dependency: build CircularLibraryService per-request
# ---------------------------------------------------------------------------


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> CircularLibraryService:  # noqa: B008
    embedding_svc = getattr(request.app.state, "embedding_service", None)
    return CircularLibraryService(db=db, embedding_service=embedding_svc)


# ---------------------------------------------------------------------------
# GET /circulars — paginated list with filters
# ---------------------------------------------------------------------------


@router.get("", response_model=CircularListResponse)
async def list_circulars(
    doc_type: str | None = Query(default=None, description="Filter by document type"),
    status: str | None = Query(default=None, description="ACTIVE/SUPERSEDED/DRAFT"),
    impact_level: str | None = Query(default=None, description="HIGH/MEDIUM/LOW"),
    department: str | None = Query(default=None, description="Partial match"),
    regulator: str | None = Query(default=None, description="Filter by regulator"),
    tags: list[str] | None = Query(default=None, description="Filter by tags"),
    date_from: date | None = Query(default=None, description="Issued date from (inclusive)"),
    date_to: date | None = Query(default=None, description="Issued date to (inclusive)"),
    sort_by: str = Query(default="issued_date", description="Sort field"),
    sort_order: str = Query(default="desc", pattern=r"^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> CircularListResponse:
    """List circulars with optional filters, pagination, and sorting."""
    circulars, total = await svc.list_circulars(
        doc_type=doc_type,
        status=status,
        impact_level=impact_level,
        department=department,
        regulator=regulator,
        tags=tags,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, math.ceil(total / page_size))

    return CircularListResponse(
        data=[CircularListItem.model_validate(c) for c in circulars],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# GET /circulars/search — hybrid vector + BM25 search
# ---------------------------------------------------------------------------


@router.get("/search", response_model=CircularSearchResponse)
async def search_circulars(
    query: str = Query(..., min_length=3, max_length=500, description="Search query"),
    doc_type: str | None = Query(default=None),
    status: str | None = Query(default="ACTIVE"),
    impact_level: str | None = Query(default=None),
    department: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_verified_user),  # noqa: B008
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> CircularSearchResponse:
    """Hybrid search combining vector similarity and BM25 full-text search.

    Requires authenticated, verified user (uses embedding API).
    Results are ranked using Reciprocal Rank Fusion (RRF).
    """
    results, total = await svc.hybrid_search(
        query=query,
        doc_type=doc_type,
        status=status,
        impact_level=impact_level,
        department=department,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, math.ceil(total / page_size))

    data = []
    for item in results:
        circ = item["circular"]
        search_item = CircularSearchResultItem(
            id=circ.id,
            circular_number=circ.circular_number,
            title=circ.title,
            doc_type=circ.doc_type,
            department=circ.department,
            issued_date=circ.issued_date,
            status=circ.status,
            impact_level=circ.impact_level,
            action_deadline=circ.action_deadline,
            affected_teams=circ.affected_teams,
            tags=circ.tags,
            regulator=circ.regulator,
            indexed_at=circ.indexed_at,
            relevance_score=item["relevance_score"],
            snippet=item.get("snippet"),
        )
        data.append(search_item)

    return CircularSearchResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# GET /circulars/autocomplete — prefix matching
# ---------------------------------------------------------------------------


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete_circulars(
    q: str = Query(..., min_length=1, max_length=200, description="Autocomplete query"),
    limit: int = Query(default=10, ge=1, le=50),
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> AutocompleteResponse:
    """Autocomplete suggestions for circular title/number."""
    circulars = await svc.autocomplete(q=q, limit=limit)
    return AutocompleteResponse(
        data=[
            AutocompleteItem(
                id=c.id,
                circular_number=c.circular_number,
                title=c.title,
                doc_type=c.doc_type,
            )
            for c in circulars
        ]
    )


# ---------------------------------------------------------------------------
# GET /circulars/departments — facet data
# ---------------------------------------------------------------------------


@router.get("/departments", response_model=DepartmentListResponse)
async def list_departments(
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> DepartmentListResponse:
    """Return distinct department values for filter dropdowns."""
    departments = await svc.get_departments()
    return DepartmentListResponse(data=departments)


# ---------------------------------------------------------------------------
# GET /circulars/tags — facet data
# ---------------------------------------------------------------------------


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> TagListResponse:
    """Return distinct tag values for filter dropdowns."""
    tags = await svc.get_tags()
    return TagListResponse(data=tags)


# ---------------------------------------------------------------------------
# GET /circulars/doc-types — facet data
# ---------------------------------------------------------------------------


@router.get("/doc-types", response_model=TagListResponse)
async def list_doc_types(
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> TagListResponse:
    """Return distinct document type values."""
    doc_types = await svc.get_doc_types()
    return TagListResponse(data=doc_types)


# ---------------------------------------------------------------------------
# GET /circulars/updates — recent circulars feed with unread tracking
# ---------------------------------------------------------------------------


@router.get("/updates", response_model=UpdatesFeedResponse)
async def list_updates(
    days: int = Query(default=7, ge=1, le=90, description="Window in days"),
    impact_level: str | None = Query(default=None, description="HIGH/MEDIUM/LOW"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_verified_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),
) -> UpdatesFeedResponse:
    """Recent circulars (by indexed_at) plus unread count since last visit.

    ``unread_count`` is the number of circulars indexed after the current
    user's ``last_seen_updates`` timestamp (or all, if never visited).
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    conditions = [CircularDocument.indexed_at >= cutoff]
    if impact_level:
        conditions.append(CircularDocument.impact_level == impact_level)

    base = select(CircularDocument).where(and_(*conditions))
    count_stmt = select(func.count(CircularDocument.id)).where(and_(*conditions))

    total = int((await db.execute(count_stmt)).scalar() or 0)

    list_stmt = base.order_by(desc(CircularDocument.indexed_at)).offset((page - 1) * page_size).limit(page_size)
    circulars = list((await db.execute(list_stmt)).scalars().all())

    # Unread count: indexed after user.last_seen_updates (no cutoff limit).
    unread_conditions: list = []
    if user.last_seen_updates is not None:
        unread_conditions.append(CircularDocument.indexed_at > user.last_seen_updates)
    unread_stmt = select(func.count(CircularDocument.id))
    if unread_conditions:
        unread_stmt = unread_stmt.where(and_(*unread_conditions))
    unread_count = int((await db.execute(unread_stmt)).scalar() or 0)

    total_pages = max(1, math.ceil(total / page_size))

    return UpdatesFeedResponse(
        data=[CircularListItem.model_validate(c) for c in circulars],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        unread_count=unread_count,
    )


@router.post("/updates/mark-seen")
async def mark_updates_seen(
    user: User = Depends(require_verified_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set ``users.last_seen_updates = now()`` for the current user.

    Uses a direct UPDATE so the write lands regardless of whether the
    ``user`` object is attached to ``db``'s session.
    """
    now = datetime.now(UTC)
    await db.execute(update(User).where(User.id == user.id).values(last_seen_updates=now))
    await db.commit()
    user.last_seen_updates = now
    return {"success": True, "message": "Updates marked as seen"}


# ---------------------------------------------------------------------------
# GET /circulars/{circular_id} — detail with chunks
# ---------------------------------------------------------------------------


@router.get("/{circular_id}", response_model=CircularDetailResponse)
async def get_circular_detail(
    circular_id: uuid.UUID,
    svc: CircularLibraryService = Depends(_get_service),  # noqa: B008
) -> CircularDetailResponse:
    """Get full circular detail including text chunks."""
    circular = await svc.get_detail(circular_id)
    if circular is None:
        raise CircularNotFoundError()

    return CircularDetailResponse(
        data=CircularDetail.model_validate(circular),
    )
