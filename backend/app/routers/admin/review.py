"""Admin Q&A review — list flagged questions, override answers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.admin import AdminAuditLog
from app.models.question import Question
from app.models.user import User
from app.schemas.admin import AdminQuestionOverride
from app.schemas.questions import QuestionListResponse, QuestionSummary

router = APIRouter()


@router.get("", response_model=QuestionListResponse)
async def list_flagged_questions(
    feedback: int | None = Query(default=-1),
    reviewed: bool | None = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> QuestionListResponse:
    """List questions for review (default: thumbs-down, unreviewed)."""
    base = select(Question)
    count_base = select(func.count(Question.id))

    if feedback is not None:
        base = base.where(Question.feedback == feedback)
        count_base = count_base.where(Question.feedback == feedback)
    if reviewed is not None:
        base = base.where(Question.reviewed == reviewed)
        count_base = count_base.where(Question.reviewed == reviewed)

    total = (await db.execute(count_base)).scalar() or 0
    stmt = base.order_by(desc(Question.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    questions = list(result.scalars().all())

    return QuestionListResponse(
        data=[QuestionSummary.model_validate(q) for q in questions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{question_id}/override")
async def override_answer(
    question_id: uuid.UUID,
    body: AdminQuestionOverride,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Override an answer with admin-corrected text."""
    stmt = select(Question).where(Question.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question is None:
        return {"success": False, "error": "Question not found", "code": "QUESTION_NOT_FOUND"}

    old_answer = question.admin_override
    question.admin_override = body.admin_override
    question.reviewed = True
    question.reviewed_at = datetime.now(UTC)

    # Audit log
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        actor_id=admin.id,
        action="override_answer",
        target_table="questions",
        target_id=question_id,
        old_value={"admin_override": old_answer},
        new_value={"admin_override": body.admin_override},
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "message": "Answer overridden"}


@router.patch("/{question_id}/mark-reviewed")
async def mark_reviewed(
    question_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a question as reviewed without overriding."""
    stmt = select(Question).where(Question.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if question is None:
        return {"success": False, "error": "Question not found", "code": "QUESTION_NOT_FOUND"}

    question.reviewed = True
    question.reviewed_at = datetime.now(UTC)
    await db.commit()

    return {"success": True, "message": "Marked as reviewed"}
