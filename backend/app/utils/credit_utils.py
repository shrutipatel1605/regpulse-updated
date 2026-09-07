"""Credit deduction utility — atomic SELECT FOR UPDATE."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientCreditsError
from app.models.user import User

logger = structlog.get_logger("regpulse.credits")


async def deduct_credit(db: AsyncSession, user_id: object) -> int:
    """Atomically deduct 1 credit. Returns new balance.

    Uses SELECT FOR UPDATE to prevent race conditions.
    Raises InsufficientCreditsError if balance is 0.
    """
    stmt = select(User).where(User.id == user_id).with_for_update()
    result = await db.execute(stmt)
    user = result.scalar_one()

    if user.credit_balance <= 0:
        raise InsufficientCreditsError()

    user.credit_balance -= 1
    await db.flush()

    logger.info(
        "credit_deducted",
        user_id=str(user_id),
        new_balance=user.credit_balance,
    )
    return user.credit_balance
