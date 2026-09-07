"""Saved interpretations router — save, list, update, delete."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models.question import Question, SavedInterpretation
from app.models.user import User
from app.schemas.questions import (
    SavedInterpretationDetailResponse,
    SavedInterpretationListResponse,
    SavedInterpretationResponse,
    SavedInterpretationUpdateRequest,
    SaveInterpretationRequest,
)

router = APIRouter(tags=["saved"])


@router.get("", response_model=SavedInterpretationListResponse)
async def list_saved(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> SavedInterpretationListResponse:
    """List saved interpretations for the current user."""
    count_base = select(func.count(SavedInterpretation.id)).where(SavedInterpretation.user_id == user.id)
    total = (await db.execute(count_base)).scalar() or 0

    stmt = (
        select(SavedInterpretation)
        .where(SavedInterpretation.user_id == user.id)
        .order_by(desc(SavedInterpretation.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return SavedInterpretationListResponse(
        data=[SavedInterpretationResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SavedInterpretationResponse, status_code=201)
async def save_interpretation(
    body: SaveInterpretationRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> SavedInterpretationResponse | dict:
    """Save a question interpretation."""
    # Verify the question belongs to the user
    q_stmt = select(Question).where(Question.id == body.question_id, Question.user_id == user.id)
    q_result = await db.execute(q_stmt)
    if q_result.scalar_one_or_none() is None:
        return {"success": False, "error": "Question not found", "code": "QUESTION_NOT_FOUND"}

    saved = SavedInterpretation(
        id=uuid.uuid4(),
        user_id=user.id,
        question_id=body.question_id,
        name=body.name,
        tags=body.tags or [],
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return SavedInterpretationResponse.model_validate(saved)


@router.get("/{saved_id}", response_model=SavedInterpretationDetailResponse)
async def get_saved_detail(
    saved_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> SavedInterpretationDetailResponse | dict:
    """Get saved interpretation with full question detail."""
    stmt = (
        select(SavedInterpretation)
        .options(selectinload(SavedInterpretation.question))
        .where(SavedInterpretation.id == saved_id, SavedInterpretation.user_id == user.id)
    )
    result = await db.execute(stmt)
    saved = result.scalar_one_or_none()

    if saved is None:
        return {"success": False, "error": "Not found", "code": "NOT_FOUND"}

    return SavedInterpretationDetailResponse.model_validate(saved)


@router.patch("/{saved_id}", response_model=SavedInterpretationResponse)
async def update_saved(
    saved_id: uuid.UUID,
    body: SavedInterpretationUpdateRequest,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> SavedInterpretationResponse | dict:
    """Update a saved interpretation."""
    stmt = select(SavedInterpretation).where(SavedInterpretation.id == saved_id, SavedInterpretation.user_id == user.id)
    result = await db.execute(stmt)
    saved = result.scalar_one_or_none()

    if saved is None:
        return {"success": False, "error": "Not found", "code": "NOT_FOUND"}

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(saved, field, value)

    await db.commit()
    await db.refresh(saved)
    return SavedInterpretationResponse.model_validate(saved)


@router.delete("/{saved_id}")
async def delete_saved(
    saved_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a saved interpretation."""
    stmt = select(SavedInterpretation).where(SavedInterpretation.id == saved_id, SavedInterpretation.user_id == user.id)
    result = await db.execute(stmt)
    saved = result.scalar_one_or_none()

    if saved is None:
        return {"success": False, "error": "Not found", "code": "NOT_FOUND"}

    await db.delete(saved)
    await db.commit()
    return {"success": True, "message": "Saved interpretation deleted"}
