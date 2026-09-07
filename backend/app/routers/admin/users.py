"""Admin user management — list, update, credit grants."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.admin import AdminAuditLog
from app.models.user import User
from app.schemas.admin import AdminUserUpdate

router = APIRouter()


@router.get("")
async def list_users(
    search: str | None = Query(default=None),
    plan: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List users with optional filters."""
    base = select(User)
    count_base = select(func.count(User.id))

    if search:
        pattern = f"%{search}%"
        filt = or_(User.email.ilike(pattern), User.full_name.ilike(pattern))
        base = base.where(filt)
        count_base = count_base.where(filt)
    if plan:
        base = base.where(User.plan == plan)
        count_base = count_base.where(User.plan == plan)
    if is_active is not None:
        base = base.where(User.is_active == is_active)
        count_base = count_base.where(User.is_active == is_active)

    total = (await db.execute(count_base)).scalar() or 0
    stmt = base.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "plan": u.plan,
                "credit_balance": u.credit_balance,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "email_verified": u.email_verified,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update user fields (admin only)."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return {"success": False, "error": "User not found", "code": "USER_NOT_FOUND"}

    old_values = {}
    new_values = {}
    updates = body.model_dump(exclude_unset=True)

    for field, value in updates.items():
        old_values[field] = getattr(user, field)
        setattr(user, field, value)
        new_values[field] = value

    if new_values:
        audit = AdminAuditLog(
            id=uuid.uuid4(),
            actor_id=admin.id,
            action="update_user",
            target_table="users",
            target_id=user_id,
            old_value=old_values,
            new_value=new_values,
        )
        db.add(audit)

    await db.commit()
    return {"success": True, "message": "User updated"}
