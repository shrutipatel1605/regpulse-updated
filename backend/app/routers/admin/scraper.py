"""Admin scraper management — view runs, trigger scrapes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.scraper import ScraperRun
from app.models.user import User
from app.schemas.admin import ScraperRunListResponse, ScraperRunResponse

router = APIRouter()


@router.get("/runs", response_model=ScraperRunListResponse)
async def list_scraper_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ScraperRunListResponse:
    """List scraper runs (newest first)."""
    total = (await db.execute(select(func.count(ScraperRun.id)))).scalar() or 0
    stmt = select(ScraperRun).order_by(desc(ScraperRun.started_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    runs = list(result.scalars().all())

    return ScraperRunListResponse(
        data=[ScraperRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/trigger")
async def trigger_scrape(
    mode: str = Query(default="priority", regex=r"^(priority|full)$"),
    _admin: User = Depends(require_admin),
) -> dict:
    """Trigger a scraper run. Enqueues a Celery task."""
    try:
        if mode == "priority":
            from scraper.tasks import priority_scrape

            priority_scrape.delay()
        else:
            from scraper.tasks import daily_scrape

            daily_scrape.delay()
    except ImportError:
        return {
            "success": True,
            "message": f"Scrape '{mode}' would be triggered (scraper not available in this env)",
        }

    return {"success": True, "message": f"Scrape '{mode}' triggered"}
