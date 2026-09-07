"""Admin prompt versions — CRUD + activate + test-question sandbox."""

from __future__ import annotations

import hashlib
import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.db import get_db
from app.dependencies.auth import require_admin
from app.dependencies.rag import build_llm_service, build_rag_service
from app.models.admin import AdminAuditLog, AnalyticsEvent, PromptVersion
from app.models.user import User
from app.schemas.admin import (
    PromptVersionCreate,
    PromptVersionListResponse,
    PromptVersionResponse,
)

router = APIRouter()
logger = structlog.get_logger("regpulse.admin.prompts")


@router.get("", response_model=PromptVersionListResponse)
async def list_prompts(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionListResponse:
    """List all prompt versions (newest first)."""
    stmt = select(PromptVersion).order_by(desc(PromptVersion.created_at))
    result = await db.execute(stmt)
    prompts = list(result.scalars().all())
    return PromptVersionListResponse(data=[PromptVersionResponse.model_validate(p) for p in prompts])


@router.post("", response_model=PromptVersionResponse)
async def create_prompt(
    body: PromptVersionCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionResponse:
    """Create a new prompt version and activate it."""
    # Deactivate all existing
    existing = await db.execute(select(PromptVersion).where(PromptVersion.is_active.is_(True)))
    for p in existing.scalars().all():
        p.is_active = False

    prompt = PromptVersion(
        id=uuid.uuid4(),
        version_tag=body.version_tag,
        prompt_text=body.prompt_text,
        is_active=True,
        created_by=admin.id,
    )
    db.add(prompt)

    audit = AdminAuditLog(
        id=uuid.uuid4(),
        actor_id=admin.id,
        action="create_prompt_version",
        target_table="prompt_versions",
        target_id=prompt.id,
        new_value={"version_tag": body.version_tag, "is_active": True},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(prompt)

    return PromptVersionResponse.model_validate(prompt)


@router.get("/test-question")
async def test_question_sandbox(
    request: Request,
    q: str = Query(..., min_length=5, max_length=500, description="Question text"),
    prompt_id: uuid.UUID | None = Query(default=None, description="Optional prompt version to test against"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    redis: object = Depends(get_redis),
) -> dict:
    """Admin-only sandbox — runs the full RAG + LLM pipeline but does NOT
    create a question record, deduct credits, or write to the answer cache.

    A single ``AnalyticsEvent`` row is written so we can audit admin usage.
    ``prompt_id``, when set, is validated to exist but the active prompt is
    not swapped — LLMService currently uses an in-module system prompt;
    future work wires PromptVersion through.
    """
    start = time.perf_counter()

    if prompt_id is not None:
        prompt = (await db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))).scalar_one_or_none()
        if prompt is None:
            return {
                "success": False,
                "error": "Prompt version not found",
                "code": "NOT_FOUND",
            }

    rag = build_rag_service(request, db, redis)
    llm = build_llm_service(request)

    chunks = await rag.retrieve(q)
    if not chunks:
        latency_ms = int((time.perf_counter() - start) * 1000)
        _log_admin_test(db, admin.id, q, prompt_id, latency_ms, matched=0)
        await db.commit()
        return {
            "success": True,
            "data": {
                "question": q,
                "answer": None,
                "quick_answer": None,
                "citations": [],
                "chunks_used": [],
                "confidence_score": None,
                "consult_expert": True,
                "model_used": None,
                "latency_ms": latency_ms,
                "note": "No relevant chunks retrieved.",
            },
        }

    llm_response, model_used = await llm.generate(q, chunks)
    latency_ms = int((time.perf_counter() - start) * 1000)

    _log_admin_test(db, admin.id, q, prompt_id, latency_ms, matched=len(chunks))
    # Do NOT commit a Question row, do NOT call deduct_credit, do NOT
    # cache the answer — this is explicitly a read-only admin tool.
    await db.commit()

    return {
        "success": True,
        "data": {
            "question": q,
            "answer": llm_response.get("detailed_interpretation"),
            "quick_answer": llm_response.get("quick_answer"),
            "risk_level": llm_response.get("risk_level"),
            "confidence_score": llm_response.get("confidence_score"),
            "consult_expert": bool(llm_response.get("consult_expert", False)),
            "affected_teams": llm_response.get("affected_teams", []),
            "citations": llm_response.get("citations", []),
            "recommended_actions": llm_response.get("recommended_actions", []),
            "chunks_used": [c.to_dict() for c in chunks],
            "model_used": model_used,
            "latency_ms": latency_ms,
            "prompt_id": str(prompt_id) if prompt_id else None,
        },
    }


def _log_admin_test(
    db: AsyncSession,
    admin_id: uuid.UUID,
    q: str,
    prompt_id: uuid.UUID | None,
    latency_ms: int,
    matched: int,
) -> None:
    """Append a single AnalyticsEvent row for the admin sandbox call."""
    event = AnalyticsEvent(
        id=uuid.uuid4(),
        user_hash=hashlib.sha256(str(admin_id).encode()).hexdigest(),
        event_type="admin_test_question",
        event_data={
            "q": q[:500],
            "prompt_id": str(prompt_id) if prompt_id else None,
            "latency_ms": latency_ms,
            "matched_chunks": matched,
        },
    )
    db.add(event)


@router.post("/{prompt_id}/activate")
async def activate_prompt(
    prompt_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Activate a specific prompt version (deactivates all others)."""
    stmt = select(PromptVersion).where(PromptVersion.id == prompt_id)
    result = await db.execute(stmt)
    target = result.scalar_one_or_none()

    if target is None:
        return {"success": False, "error": "Prompt version not found", "code": "NOT_FOUND"}

    # Deactivate all
    all_prompts = await db.execute(select(PromptVersion).where(PromptVersion.is_active.is_(True)))
    for p in all_prompts.scalars().all():
        p.is_active = False

    target.is_active = True
    await db.commit()

    return {"success": True, "message": f"Prompt {target.version_tag} activated"}
