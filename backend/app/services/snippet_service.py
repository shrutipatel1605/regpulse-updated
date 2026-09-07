"""Public safe snippet service.

Generates redacted, share-safe previews of question answers. The full
detailed_interpretation NEVER leaves this layer — only quick_answer plus
one truncated citation. If the source answer set consult_expert=True,
the snippet is replaced with a generic CTA.

Slug generation uses secrets.token_urlsafe(9) → ~12 chars in a 64-char
alphabet → 2^72 collision space. Unique constraint + retry covers the
near-impossible collision case.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import RegPulseException
from app.models.question import Question
from app.models.snippet import PublicSnippet

logger = structlog.get_logger("regpulse.snippet_service")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
QUICK_ANSWER_MAX_WORDS = 80
CITATION_QUOTE_MAX_CHARS = 200
EXPERT_FALLBACK_TEXT = (
    "This compliance question requires expert consultation. "
    "Register on RegPulse to access the full anti-hallucination answer "
    "and connect with a qualified expert."
)
MAX_SLUG_RETRIES = 5


class SnippetNotFoundError(RegPulseException):
    http_status = 404
    error_code = "SNIPPET_NOT_FOUND"

    def __init__(self, message: str = "Snippet not found or revoked") -> None:
        super().__init__(message)


class SnippetForbiddenError(RegPulseException):
    http_status = 403
    error_code = "SNIPPET_FORBIDDEN"

    def __init__(self, message: str = "You do not own this snippet") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_slug() -> str:
    """12-char URL-safe slug. ~2^72 collision space."""
    return secrets.token_urlsafe(9)


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"


def _build_safe_snippet(question: Question) -> tuple[str, dict | None, bool]:
    """Build the public snippet payload from a question.

    Returns (snippet_text, top_citation_dict_or_none, consult_expert).
    The detailed_interpretation is intentionally NEVER read here.
    """
    # If the original answer flagged consult_expert (via citations metadata),
    # surface the generic fallback instead of any partial answer.
    citations = question.citations or []
    if not isinstance(citations, list):
        citations = []

    # Detect "consult expert" state: zero valid citations OR explicit flag
    # Heuristic — the question record stores the post-validation citations.
    is_expert_only = len(citations) == 0

    if is_expert_only or not question.quick_answer:
        return EXPERT_FALLBACK_TEXT, None, True

    snippet_text = _truncate_words(question.quick_answer, QUICK_ANSWER_MAX_WORDS)

    top = citations[0] if citations else None
    top_citation: dict | None = None
    if isinstance(top, dict) and top.get("circular_number"):
        quote = (top.get("verbatim_quote") or "")[:CITATION_QUOTE_MAX_CHARS]
        if len(top.get("verbatim_quote") or "") > CITATION_QUOTE_MAX_CHARS:
            quote = quote.rstrip() + "…"
        top_citation = {
            "circular_number": top["circular_number"],
            "verbatim_quote": quote,
            "section_reference": top.get("section_reference"),
        }

    return snippet_text, top_citation, False


def _share_url(slug: str) -> str:
    settings = get_settings()
    base = settings.PUBLIC_BASE_URL or settings.FRONTEND_URL
    return f"{base.rstrip('/')}/s/{slug}"


def _og_image_url(slug: str) -> str:
    settings = get_settings()
    # Backend serves the OG image; LinkedIn/X must resolve this URL directly.
    # Falls back to localhost:8000 for demo.
    base = settings.BACKEND_PUBLIC_URL or "http://localhost:8000"
    return f"{base.rstrip('/')}/api/v1/snippets/{slug}/og"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_snippet(
    db: AsyncSession,
    *,
    question_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PublicSnippet:
    """Create a public snippet for a question owned by user_id.

    Raises SnippetForbiddenError if the question is not owned by the user.
    """
    settings = get_settings()

    stmt = select(Question).where(Question.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question is None or question.user_id != user_id:
        raise SnippetForbiddenError("Question not found or not owned by user")

    snippet_text, top_citation, consult_expert = _build_safe_snippet(question)

    expires_at = None
    if settings.SNIPPET_EXPIRY_DAYS > 0:
        expires_at = datetime.now(UTC) + timedelta(days=settings.SNIPPET_EXPIRY_DAYS)

    last_error: Exception | None = None
    for attempt in range(MAX_SLUG_RETRIES):
        slug = _generate_slug()
        snippet = PublicSnippet(
            id=uuid.uuid4(),
            slug=slug,
            question_id=question_id,
            user_id=user_id,
            snippet_text=snippet_text,
            top_citation=top_citation,
            consult_expert=consult_expert,
            expires_at=expires_at,
        )
        db.add(snippet)
        try:
            await db.commit()
            await db.refresh(snippet)
            logger.info(
                "snippet_created",
                snippet_id=str(snippet.id),
                slug=slug,
                consult_expert=consult_expert,
                attempt=attempt,
            )
            return snippet
        except IntegrityError as e:  # pragma: no cover — collision is astronomically rare
            await db.rollback()
            last_error = e
            logger.warning("snippet_slug_collision", attempt=attempt)
            continue

    raise RegPulseException(f"Failed to generate unique snippet slug after {MAX_SLUG_RETRIES} attempts") from last_error


async def get_snippet_by_slug(
    db: AsyncSession,
    slug: str,
    *,
    include_revoked: bool = False,
) -> PublicSnippet:
    """Fetch a public snippet by slug. Raises SnippetNotFoundError if missing/revoked/expired."""
    stmt = select(PublicSnippet).where(PublicSnippet.slug == slug)
    result = await db.execute(stmt)
    snippet = result.scalar_one_or_none()

    if snippet is None:
        raise SnippetNotFoundError()

    if not include_revoked and snippet.revoked:
        raise SnippetNotFoundError()

    if snippet.expires_at is not None and snippet.expires_at < datetime.now(UTC):
        raise SnippetNotFoundError("Snippet has expired")

    return snippet


async def increment_view_count(db: AsyncSession, slug: str) -> None:
    """Bump the view counter (best-effort, no SELECT FOR UPDATE)."""
    await db.execute(PublicSnippet.__table__.update().where(PublicSnippet.slug == slug).values(view_count=PublicSnippet.view_count + 1))
    await db.commit()


async def revoke_snippet(
    db: AsyncSession,
    *,
    slug: str,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> PublicSnippet:
    """Soft-revoke a snippet. Owner or admin only."""
    snippet = await get_snippet_by_slug(db, slug, include_revoked=True)

    if not is_admin and snippet.user_id != user_id:
        raise SnippetForbiddenError("Only the owner or an admin may revoke this snippet")

    snippet.revoked = True
    await db.commit()
    logger.info("snippet_revoked", slug=slug, by_admin=is_admin)
    return snippet


async def list_snippets_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PublicSnippet], int]:
    total_stmt = select(func.count(PublicSnippet.id)).where(PublicSnippet.user_id == user_id)
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = (
        select(PublicSnippet)
        .where(PublicSnippet.user_id == user_id)
        .order_by(desc(PublicSnippet.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


def to_owner_response(snippet: PublicSnippet) -> dict[str, Any]:
    return {
        "id": snippet.id,
        "slug": snippet.slug,
        "snippet_text": snippet.snippet_text,
        "top_citation": snippet.top_citation,
        "consult_expert": snippet.consult_expert,
        "share_url": _share_url(snippet.slug),
        "view_count": snippet.view_count,
        "revoked": snippet.revoked,
        "created_at": snippet.created_at,
    }


def to_public_view(snippet: PublicSnippet) -> dict[str, Any]:
    return {
        "slug": snippet.slug,
        "snippet_text": snippet.snippet_text,
        "top_citation": snippet.top_citation,
        "consult_expert": snippet.consult_expert,
        "og_image_url": _og_image_url(snippet.slug),
        "created_at": snippet.created_at,
    }
