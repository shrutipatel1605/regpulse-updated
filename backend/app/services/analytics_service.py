"""Analytics service — track and query usage events.

Events are pseudonymised (user_hash = HMAC-SHA256 of user_id).
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AnalyticsEvent

logger = structlog.get_logger("regpulse.analytics")

_SALT = "regpulse-analytics-v1"


def _hash_user_id(user_id: str) -> str:
    """HMAC-SHA256 pseudonymisation of user ID."""
    return hmac.new(_SALT.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()


class AnalyticsService:
    """Track and query usage analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def track(
        self,
        *,
        user_id: str | None,
        event_type: str,
        event_data: dict | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Record an analytics event."""
        user_hash = _hash_user_id(user_id) if user_id else "anonymous"

        event = AnalyticsEvent(
            id=uuid.uuid4(),
            user_hash=user_hash,
            event_type=event_type,
            event_data=event_data or {},
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(event)
        await self._db.flush()

    async def get_event_counts(
        self,
        *,
        days: int = 30,
    ) -> list[dict]:
        """Get event type counts for the last N days."""
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0)
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=days)

        stmt = (
            select(
                AnalyticsEvent.event_type,
                func.count(AnalyticsEvent.id).label("count"),
            )
            .where(AnalyticsEvent.created_at >= cutoff)
            .group_by(AnalyticsEvent.event_type)
            .order_by(desc("count"))
        )
        result = await self._db.execute(stmt)
        return [{"event_type": row[0], "count": row[1]} for row in result.all()]
