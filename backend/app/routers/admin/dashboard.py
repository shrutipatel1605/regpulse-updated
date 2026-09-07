"""Admin dashboard — aggregate stats + clustering heatmap."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.admin import QuestionCluster
from app.models.circular import CircularDocument
from app.models.question import Question
from app.models.user import User
from app.schemas.admin import (
    ClusterHeatmapResponse,
    ClusterInfo,
    ClusterTriggerResponse,
    DashboardResponse,
    DashboardStats,
)

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Return aggregate stats for the admin dashboard."""
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_30d = (await db.execute(select(func.count(User.id)).where(User.last_login_at >= thirty_days_ago))).scalar() or 0
    total_questions = (await db.execute(select(func.count(Question.id)))).scalar() or 0
    questions_today = (
        await db.execute(select(func.count(Question.id)).where(Question.created_at >= now.replace(hour=0, minute=0, second=0)))
    ).scalar() or 0
    total_circulars = (await db.execute(select(func.count(CircularDocument.id)))).scalar() or 0
    pending_reviews = (await db.execute(select(func.count(Question.id)).where(Question.feedback == -1, Question.reviewed.is_(False)))).scalar() or 0
    avg_feedback = (await db.execute(select(func.avg(Question.feedback)).where(Question.feedback.is_not(None)))).scalar()
    credits_30d = (
        await db.execute(
            select(func.count(Question.id)).where(
                Question.credit_deducted.is_(True),
                Question.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return DashboardResponse(
        data=DashboardStats(
            total_users=total_users,
            active_users_30d=active_30d,
            total_questions=total_questions,
            questions_today=questions_today,
            total_circulars=total_circulars,
            pending_reviews=pending_reviews,
            avg_feedback_score=round(float(avg_feedback), 2) if avg_feedback else None,
            credits_consumed_30d=credits_30d,
        )
    )


@router.get("/heatmap", response_model=ClusterHeatmapResponse)
async def get_cluster_heatmap(
    period_days: int = Query(default=30, ge=7, le=90),
    time_bucket: str = Query(default="day", pattern=r"^(day|week)$"),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ClusterHeatmapResponse:
    """Return cluster x time-bucket matrix for the heatmap visualization."""
    now = datetime.now(UTC)
    start_date = now - timedelta(days=period_days)

    # Fetch clusters for the period
    stmt = select(QuestionCluster).where(QuestionCluster.period_end >= start_date.date()).order_by(QuestionCluster.cluster_label)
    result = await db.execute(stmt)
    clusters = list(result.scalars().all())

    if not clusters:
        return ClusterHeatmapResponse(clusters=[], time_buckets=[], matrix=[])

    cluster_ids = [str(c.id) for c in clusters]
    cluster_info = [
        ClusterInfo(
            id=c.id,
            label=c.cluster_label,
            question_count=c.question_count,
            representative_questions=list(c.representative_questions or []),
        )
        for c in clusters
    ]

    # Generate time buckets — two static queries to avoid f-string in SQL (S608)
    _HEATMAP_SQL_DAY = text("""
        SELECT
            q.cluster_id::text,
            date_trunc('day', q.created_at)::date AS bucket_date,
            COUNT(*)::int AS question_count
        FROM questions q
        WHERE q.cluster_id IS NOT NULL
          AND q.created_at >= :start_date
        GROUP BY q.cluster_id, bucket_date
        ORDER BY bucket_date, q.cluster_id
    """)
    _HEATMAP_SQL_WEEK = text("""
        SELECT
            q.cluster_id::text,
            date_trunc('week', q.created_at)::date AS bucket_date,
            COUNT(*)::int AS question_count
        FROM questions q
        WHERE q.cluster_id IS NOT NULL
          AND q.created_at >= :start_date
        GROUP BY q.cluster_id, bucket_date
        ORDER BY bucket_date, q.cluster_id
    """)
    bucket_query = _HEATMAP_SQL_WEEK if time_bucket == "week" else _HEATMAP_SQL_DAY

    rows = (await db.execute(bucket_query, {"start_date": start_date})).fetchall()

    # Build time_buckets list and matrix
    all_dates: set[date] = set()
    counts: dict[tuple[str, date], int] = {}
    for row in rows:
        cid = row[0]
        d = row[1]
        cnt = row[2]
        all_dates.add(d)
        counts[(cid, d)] = cnt

    sorted_dates = sorted(all_dates)
    time_buckets = [d.isoformat() for d in sorted_dates]

    # Build matrix: [cluster_index][time_index] = count
    matrix = []
    for cid in cluster_ids:
        row_data = [counts.get((cid, d), 0) for d in sorted_dates]
        matrix.append(row_data)

    return ClusterHeatmapResponse(
        clusters=cluster_info,
        time_buckets=time_buckets,
        matrix=matrix,
    )


@router.post("/heatmap/refresh", response_model=ClusterTriggerResponse)
async def trigger_clustering(
    period_days: int = Query(default=30, ge=7, le=90),
    _admin: User = Depends(require_admin),
) -> ClusterTriggerResponse:
    """Manually trigger re-clustering."""
    try:
        from scraper.tasks import run_question_clustering

        run_question_clustering.delay(period_days=period_days)
    except ImportError:
        pass
    return ClusterTriggerResponse(message="Clustering job queued")
