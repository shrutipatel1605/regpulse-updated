"""Router for Team Debates API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import get_db
from app.dependencies.auth import get_current_user
from app.models.debate import DebateReply, DebateThread
from app.models.user import User
from app.schemas.debates import (
    DebateReplyCreate,
    DebateReplyResponse,
    DebateThreadCreate,
    DebateThreadResponse,
)

router = APIRouter(tags=["Debates"])


@router.post("", response_model=DebateThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_debate_thread(
    data: DebateThreadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new debate thread."""
    thread = DebateThread(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        source_circular_id=data.source_circular_id,
        source_ref=data.source_ref,
        tags=data.tags,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)

    return thread.__dict__ | {"replies": []}


@router.get("", response_model=list[DebateThreadResponse])
async def list_debate_threads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all debate threads."""
    result = await db.execute(
        select(DebateThread).options(joinedload(DebateThread.replies).joinedload(DebateReply.user)).order_by(DebateThread.created_at.desc())
    )
    threads = result.unique().scalars().all()

    response = []
    for t in threads:
        replies = []
        for r in sorted(t.replies, key=lambda x: x.created_at):
            who = "".join([n[0] for n in r.user.full_name.split() if n]) if r.user and r.user.full_name else "U"
            replies.append(r.__dict__ | {"who": who, "role": r.user.designation if r.user else ""})

        response.append(t.__dict__ | {"replies": replies})

    return response


@router.post("/{thread_id}/replies", response_model=DebateReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_debate_reply(
    thread_id: uuid.UUID,
    data: DebateReplyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a reply to a debate thread."""
    thread = await db.get(DebateThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Debate thread not found")

    reply = DebateReply(
        thread_id=thread_id,
        user_id=current_user.id,
        content=data.content,
        refs_count=data.refs_count,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    who = "".join([n[0] for n in current_user.full_name.split() if n]) if current_user.full_name else "U"

    return reply.__dict__ | {"who": who, "role": current_user.designation}


@router.post("/{thread_id}/stance")
async def update_stance(
    thread_id: uuid.UUID,
    stance: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update agree/disagree count (simple mock behavior for now)."""
    thread = await db.get(DebateThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Debate thread not found")

    if stance == "agree":
        thread.stance_agree += 1
    elif stance == "disagree":
        thread.stance_disagree += 1

    await db.commit()
    return {"status": "success", "agree": thread.stance_agree, "disagree": thread.stance_disagree}
