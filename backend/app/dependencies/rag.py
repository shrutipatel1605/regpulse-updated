"""Shared builders for RAGService and LLMService.

Both the questions router (user-facing Q&A) and the admin sandbox router
(admin-only test-question) need to construct RAGService + LLMService from
``request.app.state``. The builders live here to avoid duplicating wiring
code across routers.

These are helpers — not FastAPI ``Depends()`` providers — because the two
services rely on ``request.app.state`` values (embedding_service,
cross_encoder, anthropic_client, openai_client) that are attached during
the application's lifespan startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.llm_service import LLMService
    from app.services.rag_service import RAGService


def build_rag_service(
    request: Request,
    db: AsyncSession,
    redis: object,
) -> RAGService:
    """Construct a RAGService wired to app.state services."""
    from app.services.rag_service import RAGService

    embedding_svc = getattr(request.app.state, "embedding_service", None)
    cross_encoder = getattr(request.app.state, "cross_encoder", None)
    return RAGService(
        db=db,
        embedding_service=embedding_svc,
        redis=redis,
        cross_encoder=cross_encoder,
    )


def build_llm_service(request: Request) -> LLMService:
    """Construct an LLMService wired to app.state LLM clients."""
    from app.services.llm_service import LLMService

    return LLMService(
        anthropic_client=request.app.state.anthropic_client,
        openai_client=request.app.state.openai_client,
    )
