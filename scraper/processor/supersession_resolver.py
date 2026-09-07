"""Supersession resolution for RBI circulars.

Standalone scraper module. NEVER imports from backend/app/.

When a new circular supersedes older ones, this resolver:
1. Exact match on circular_number, then rapidfuzz fuzzy match (threshold 90)
2. SELECT FOR UPDATE to atomically set status='SUPERSEDED', superseded_by
3. Flag saved_interpretations citing the superseded circular as needs_review=TRUE
4. Enqueue send_staleness_alerts Celery task for affected users

The circular_number list used for fuzzy matching is Redis-cached (TTL 1800s).
"""

from __future__ import annotations

import json
import os

import structlog
from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.orm import Session

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.supersession")

# ---------------------------------------------------------------------------
# Redis helper (optional — gracefully degrades if unavailable)
# ---------------------------------------------------------------------------

_CACHE_KEY = "regpulse:circular_numbers"
_CACHE_TTL = 1800  # 30 minutes


def _get_redis_client():  # noqa: ANN202
    """Get a sync Redis client. Returns None if unavailable."""
    try:
        import redis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def _get_cached_circular_numbers(
    session: Session,
) -> list[tuple[str, str]]:
    """Get all (circular_number, id) pairs, Redis-cached for 1800s.

    Returns list of (circular_number, document_id_str) tuples.
    """
    redis_client = _get_redis_client()

    # Try cache first
    if redis_client is not None:
        try:
            cached = redis_client.get(_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            logger.debug("redis_cache_read_failed", exc_info=True)

    # Cache miss or no Redis — query DB
    rows = session.execute(
        text(
            "SELECT circular_number, id::text FROM circular_documents "
            "WHERE circular_number IS NOT NULL AND status = 'ACTIVE'"
        )
    ).fetchall()
    result = [(row[0], row[1]) for row in rows]

    # Populate cache
    if redis_client is not None and result:
        try:
            redis_client.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(result))
        except Exception:
            logger.debug("redis_cache_write_failed", exc_info=True)

    return result


def _invalidate_cache() -> None:
    """Delete the cached circular numbers list after a supersession update."""
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.delete(_CACHE_KEY)
        except Exception:
            logger.debug("redis_cache_invalidate_failed", exc_info=True)


# ---------------------------------------------------------------------------
# SupersessionResolver
# ---------------------------------------------------------------------------


class SupersessionResolver:
    """Resolve supersession relationships between circulars.

    For each supersession reference:
    1. Exact DB lookup by circular_number
    2. Rapidfuzz fuzzy match (threshold 90) on Redis-cached list if no exact hit
    3. SELECT FOR UPDATE to atomically mark SUPERSEDED
    4. Flag saved_interpretations as needs_review
    5. Enqueue staleness alert emails
    """

    _FUZZY_THRESHOLD = 90

    def resolve(
        self,
        session: Session,
        new_document_id: str,
        supersession_refs: list[str],
    ) -> int:
        """Mark referenced circulars as superseded.

        Args:
            session: SQLAlchemy session (caller manages commit).
            new_document_id: UUID of the new circular that supersedes others.
            supersession_refs: List of circular numbers (e.g. ["RBI/2024-25/158"]).

        Returns:
            Number of circulars marked as superseded.
        """
        if not supersession_refs:
            return 0

        resolved_count = 0

        for ref in supersession_refs:
            old_id = self._find_circular(session, ref)
            if old_id is None:
                logger.info("supersession_ref_not_found", ref=ref)
                continue

            # Reverse check: don't supersede if the "old" doc already supersedes us
            reverse = session.execute(
                text(
                    "SELECT superseded_by FROM circular_documents "
                    "WHERE id = :old_id AND superseded_by = :new_id"
                ),
                {"old_id": old_id, "new_id": new_document_id},
            ).fetchone()
            if reverse:
                logger.warning(
                    "supersession_reverse_conflict",
                    ref=ref,
                    old_id=old_id,
                    new_document_id=new_document_id,
                )
                continue

            # SELECT FOR UPDATE — lock the row before updating
            row = session.execute(
                text(
                    "SELECT id, status, circular_number "
                    "FROM circular_documents WHERE id = :old_id FOR UPDATE"
                ),
                {"old_id": old_id},
            ).fetchone()

            if not row or row[1] != "ACTIVE":
                logger.info(
                    "supersession_skip_not_active",
                    ref=ref,
                    old_id=old_id,
                    current_status=row[1] if row else None,
                )
                continue

            # Atomically update status
            session.execute(
                text(
                    "UPDATE circular_documents "
                    "SET status = 'SUPERSEDED', superseded_by = :new_id, updated_at = NOW() "
                    "WHERE id = :old_id"
                ),
                {"new_id": new_document_id, "old_id": old_id},
            )

            superseded_cn = row[2]  # circular_number of the superseded doc

            logger.info(
                "circular_superseded",
                old_circular_number=superseded_cn,
                old_id=old_id,
                new_document_id=new_document_id,
            )

            # Flag saved_interpretations citing this circular as needs_review
            self._flag_stale_interpretations(session, superseded_cn)

            # Enqueue staleness alert email
            self._enqueue_staleness_alert(old_id)

            resolved_count += 1

        # Invalidate Redis cache if any circulars were superseded
        if resolved_count > 0:
            _invalidate_cache()

        logger.info(
            "supersession_resolution_complete",
            new_document_id=new_document_id,
            refs=supersession_refs,
            resolved_count=resolved_count,
        )

        return resolved_count

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _find_circular(self, session: Session, circular_number: str) -> str | None:
        """Find a circular by number: exact match first, then fuzzy.

        Returns document ID string or None.
        """
        # Exact match
        row = session.execute(
            text(
                "SELECT id::text FROM circular_documents "
                "WHERE circular_number = :cn AND status = 'ACTIVE'"
            ),
            {"cn": circular_number},
        ).fetchone()
        if row:
            return row[0]

        # Fuzzy match using rapidfuzz on cached list
        all_circulars = _get_cached_circular_numbers(session)
        if not all_circulars:
            return None

        best_score = 0.0
        best_id: str | None = None
        for cn, doc_id in all_circulars:
            score = fuzz.ratio(circular_number, cn)
            if score > best_score:
                best_score = score
                best_id = doc_id

        if best_score >= self._FUZZY_THRESHOLD and best_id is not None:
            logger.info(
                "supersession_fuzzy_match",
                ref=circular_number,
                matched_id=best_id,
                score=best_score,
            )
            return best_id

        return None

    @staticmethod
    def _flag_stale_interpretations(session: Session, circular_number: str) -> int:
        """Flag saved_interpretations citing a superseded circular as needs_review.

        Queries questions.citations JSONB for the circular_number, then updates
        all saved_interpretations linked to those questions.

        Returns count of updated saved_interpretations.
        """
        # Find questions that cite the superseded circular number
        pattern = json.dumps([{"circular_number": circular_number}])
        affected_questions = session.execute(
            text("SELECT id FROM questions WHERE citations @> :pattern::jsonb"),
            {"pattern": pattern},
        ).fetchall()

        if not affected_questions:
            return 0

        question_ids = [str(r[0]) for r in affected_questions]

        # Flag all saved_interpretations for those questions
        result = session.execute(
            text(
                "UPDATE saved_interpretations "
                "SET needs_review = TRUE "
                "WHERE question_id = ANY(:qids::uuid[])"
            ),
            {"qids": question_ids},
        )

        flagged = result.rowcount
        if flagged > 0:
            logger.info(
                "stale_interpretations_flagged",
                circular_number=circular_number,
                affected_questions=len(question_ids),
                flagged_interpretations=flagged,
            )
        return flagged

    @staticmethod
    def _enqueue_staleness_alert(circular_id: str) -> None:
        """Enqueue a Celery task to send staleness alert emails."""
        try:
            from scraper.tasks import send_staleness_alerts

            send_staleness_alerts.delay(circular_id=circular_id)
        except Exception:
            # Task may not be registered yet during initial setup
            logger.warning(
                "staleness_alert_enqueue_failed",
                circular_id=circular_id,
                exc_info=True,
            )
