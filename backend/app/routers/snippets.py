"""Public snippet sharing routes.

POST /api/v1/snippets             — owner creates a snippet for one of their questions
GET  /api/v1/snippets/{slug}      — public, returns the safe snippet (rate-limited)
GET  /api/v1/snippets/{slug}/og   — public, returns the OG image PNG
DELETE /api/v1/snippets/{slug}    — owner or admin revokes the snippet
GET  /api/v1/snippets             — owner lists their snippets
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models.user import User
from app.rate_limit import limiter
from app.schemas.snippet import (
    PublicSnippetResponse,
    PublicSnippetView,
    SnippetCreateRequest,
    SnippetListItem,
    SnippetListResponse,
)
from app.services import snippet_service
from app.services.og_image_service import render_snippet_og

router = APIRouter(tags=["snippets"])

settings = get_settings()
_PUBLIC_RATE_LIMIT = f"{settings.SNIPPET_RATE_LIMIT_PER_MIN}/minute"


@router.post("", response_model=PublicSnippetResponse, status_code=201)
async def create_snippet(
    body: SnippetCreateRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    snippet = await snippet_service.create_snippet(db, question_id=body.question_id, user_id=user.id)
    return snippet_service.to_owner_response(snippet)


@router.get("", response_model=SnippetListResponse)
async def list_my_snippets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> SnippetListResponse:
    items, total = await snippet_service.list_snippets_for_user(db, user_id=user.id, page=page, page_size=page_size)
    return SnippetListResponse(
        items=[SnippetListItem.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{slug}", response_model=PublicSnippetView)
@limiter.limit(_PUBLIC_RATE_LIMIT)
async def get_public_snippet(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public, no auth. Rate-limited per IP. Increments view counter."""
    snippet = await snippet_service.get_snippet_by_slug(db, slug)
    await snippet_service.increment_view_count(db, slug)
    return snippet_service.to_public_view(snippet)


@router.get("/{slug}/og")
@limiter.limit(_PUBLIC_RATE_LIMIT)
async def get_snippet_og_image(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Public OG image. Cached for 24h via response header."""
    snippet = await snippet_service.get_snippet_by_slug(db, slug)

    citation_label = None
    if snippet.top_citation and isinstance(snippet.top_citation, dict):
        citation_label = snippet.top_citation.get("circular_number")

    png = render_snippet_og(
        snippet_text=snippet.snippet_text,
        citation_label=citation_label,
        consult_expert=snippet.consult_expert,
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.delete("/{slug}")
async def revoke_snippet(
    slug: str,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await snippet_service.revoke_snippet(db, slug=slug, user_id=user.id, is_admin=user.is_admin)
    return {"success": True, "message": "Snippet revoked"}
