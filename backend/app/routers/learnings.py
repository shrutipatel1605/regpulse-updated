"""Router for Team Learnings API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import get_db
from app.dependencies.auth import get_current_user
from app.models.learning import Learning
from app.models.user import User
from app.schemas.learnings import LearningCreate, LearningResponse, LearningUpdate

router = APIRouter(tags=["Learnings"])


@router.post("", response_model=LearningResponse, status_code=status.HTTP_201_CREATED)
async def create_learning(
    data: LearningCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new team learning."""
    learning = Learning(
        user_id=current_user.id,
        title=data.title,
        note=data.note,
        source_type=data.source_type,
        source_id=data.source_id,
        source_ref=data.source_ref,
        tags=data.tags,
    )
    db.add(learning)
    await db.commit()
    await db.refresh(learning)

    # Send email or notification here if notify_team is True
    # Deferred for future sprint / celery task integration.

    initials = "".join([n[0] for n in current_user.full_name.split() if n]) if current_user.full_name else "U"

    return {**learning.__dict__, "user_initials": initials}


@router.get("", response_model=list[LearningResponse])
async def list_learnings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all team learnings (for demo, just all learnings in system)."""
    # In a full implementation, we'd filter by team. For now we return all learnings.
    result = await db.execute(select(Learning).options(joinedload(Learning.user)).order_by(Learning.created_at.desc()))
    learnings = result.scalars().all()

    response = []
    for l in learnings:
        initials = "".join([n[0] for n in l.user.full_name.split() if n]) if l.user and l.user.full_name else "U"
        response.append({**l.__dict__, "user_initials": initials})
    return response


@router.put("/{learning_id}", response_model=LearningResponse)
async def update_learning(
    learning_id: uuid.UUID,
    data: LearningUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a team learning."""
    learning = await db.get(Learning, learning_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Learning not found")

    # Check permissions (only author or admin)
    if learning.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to edit this learning")

    if data.title is not None:
        learning.title = data.title
    if data.note is not None:
        learning.note = data.note
    if data.tags is not None:
        learning.tags = data.tags

    await db.commit()
    await db.refresh(learning)

    # We need user details for the response
    user_q = await db.get(User, learning.user_id)
    initials = "".join([n[0] for n in user_q.full_name.split() if n]) if user_q and user_q.full_name else "U"

    return {**learning.__dict__, "user_initials": initials}


@router.delete("/{learning_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_learning(
    learning_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a team learning."""
    learning = await db.get(Learning, learning_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Learning not found")

    if learning.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this learning")

    await db.delete(learning)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
