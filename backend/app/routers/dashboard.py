"""User Dashboard router — Pulse metrics and activity feed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import get_current_user
from app.models.circular import CircularDocument
from app.models.question import Question, SavedInterpretation
from app.models.user import User
from app.schemas.dashboard import (
    ActivityItem,
    DashboardPulseResponse,
    HeatmapData,
    HeatmapRow,
    PulseMetrics,
)

router = APIRouter(tags=["Dashboard"])


@router.get("/pulse", response_model=DashboardPulseResponse)
async def get_pulse(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardPulseResponse:
    """Return dashboard pulse metrics, semantic heatmap, and activity stream."""
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    # 1. Pulse Metrics
    total_circs = (await db.execute(select(func.count(CircularDocument.id)))).scalar() or 0
    this_week_circs = (await db.execute(select(func.count(CircularDocument.id)).where(CircularDocument.indexed_at >= seven_days_ago))).scalar() or 0
    superseded = (
        await db.execute(
            select(func.count(CircularDocument.id)).where(
                CircularDocument.status == "SUPERSEDED",
                CircularDocument.updated_at >= seven_days_ago,
            )
        )
    ).scalar() or 0

    questions_asked = (await db.execute(select(func.count(Question.id)).where(Question.user_id == current_user.id))).scalar() or 0

    # Mock learnings captured since we don't have the table yet
    learnings_captured = 0

    # Mock sparkline for now (we'd calculate questions asked per day for last 14 days)
    sparkline = [3, 5, 2, 8, 6, 9, 4, 11, 7, 10, 12, 9, 13, 15]

    pulse = PulseMetrics(
        total_circulars=total_circs,
        this_week=this_week_circs,
        superseded=superseded,
        questions_asked=questions_asked,
        questions_answered=questions_asked,
        learnings_captured=learnings_captured,
        sparkline=sparkline,
    )

    # 2. Semantic Heatmap
    # Reusing logic from admin dashboard for cluster distribution over last 7 days
    # (Simplified mock logic here to bootstrap the endpoint before full table integration)
    heatmap = HeatmapData(
        cols=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        rows=[
            HeatmapRow(name="KYC / AML", vals=[3, 2, 7, 4, 5, 1, 0]),
            HeatmapRow(name="Priority Sector", vals=[1, 4, 2, 6, 8, 2, 0]),
            HeatmapRow(name="SBR Framework", vals=[5, 2, 3, 9, 7, 3, 1]),
            HeatmapRow(name="Digital Lending", vals=[2, 1, 4, 3, 2, 1, 0]),
        ],
    )

    # 3. Activity Stream
    activity_items = []

    circs_query = await db.execute(select(CircularDocument).order_by(CircularDocument.indexed_at.desc()).limit(3))
    for c in circs_query.scalars():
        impact_str = "high" if c.impact_level == "HIGH" else "med" if c.impact_level == "MEDIUM" else "low"
        activity_items.append(
            {
                "when": c.indexed_at,
                "item": ActivityItem(
                    when=(c.indexed_at.strftime("%H:%M") if c.indexed_at.date() == now.date() else c.indexed_at.strftime("%d %b")),
                    type="circ",
                    text=f"{c.circular_number} indexed — {c.title}",
                    impact=impact_str,
                ),
            }
        )

    qs_query = await db.execute(select(Question).where(Question.user_id == current_user.id).order_by(Question.created_at.desc()).limit(3))
    for q in qs_query.scalars():
        name = current_user.full_name.split()[0] if current_user.full_name else "You"
        activity_items.append(
            {
                "when": q.created_at,
                "item": ActivityItem(
                    when=(q.created_at.strftime("%H:%M") if q.created_at.date() == now.date() else q.created_at.strftime("%d %b")),
                    type="ask",
                    text=f"{name} asked: '{q.question_text[:40]}...'",
                ),
            }
        )

    saved_query = await db.execute(
        select(SavedInterpretation).where(SavedInterpretation.user_id == current_user.id).order_by(SavedInterpretation.created_at.desc()).limit(2)
    )
    for s in saved_query.scalars():
        name = current_user.full_name.split()[0] if current_user.full_name else "You"
        activity_items.append(
            {
                "when": s.created_at,
                "item": ActivityItem(
                    when=(s.created_at.strftime("%H:%M") if s.created_at.date() == now.date() else s.created_at.strftime("%d %b")),
                    type="save",
                    text=f"{name} saved an interpretation: '{s.name[:40]}...'",
                ),
            }
        )

    activity_items.sort(key=lambda x: x["when"], reverse=True)
    activity = [a["item"] for a in activity_items[:8]]

    # Ensure we return empty array if no items
    if not activity:
        activity = []

    return DashboardPulseResponse(
        pulse=pulse,
        heatmap=heatmap,
        activity=activity,
    )
