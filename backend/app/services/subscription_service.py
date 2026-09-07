"""Subscription service — plan configuration, Razorpay order creation, payment verification.

Handles:
- Plan definitions (monthly/annual pricing, credit grants)
- Razorpay order creation
- Payment signature verification (HMAC-SHA256)
- Webhook event processing (payment.captured)
- Credit grant + plan activation on successful payment
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.subscription import SubscriptionEvent
from app.models.user import User

logger = structlog.get_logger("regpulse.subscriptions")

# Plan definitions
PLANS = {
    "monthly": {
        "name": "Professional Monthly",
        "amount_paise": 299900,  # ₹2,999
        "credits": 250,
        "duration_days": 30,
    },
    "annual": {
        "name": "Professional Annual",
        "amount_paise": 2999900,  # ₹29,999
        "credits": 3000,
        "duration_days": 365,
    },
}


class SubscriptionService:
    """Manages subscription orders, verification, and credit grants."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()

    async def create_order(self, user: User, plan: str) -> dict:
        """Create a Razorpay order for the given plan.

        Returns dict with order_id, amount_paise, currency, plan.
        """
        plan_config = PLANS.get(plan)
        if not plan_config:
            raise ValueError(f"Unknown plan: {plan}")

        import razorpay

        client = razorpay.Client(auth=(self._settings.RAZORPAY_KEY_ID, self._settings.RAZORPAY_KEY_SECRET))

        order = client.order.create(
            {
                "amount": plan_config["amount_paise"],
                "currency": "INR",
                "receipt": f"regpulse_{user.id}_{plan}_{uuid.uuid4().hex[:8]}",
                "notes": {
                    "user_id": str(user.id),
                    "plan": plan,
                    "email": user.email,
                },
            }
        )

        # Record the pending order
        event = SubscriptionEvent(
            id=uuid.uuid4(),
            user_id=user.id,
            order_id=order["id"],
            plan=plan,
            amount_paise=plan_config["amount_paise"],
            status="created",
        )
        self._db.add(event)
        await self._db.commit()

        logger.info(
            "order_created",
            order_id=order["id"],
            user_id=str(user.id),
            plan=plan,
        )

        return {
            "order_id": order["id"],
            "amount_paise": plan_config["amount_paise"],
            "currency": "INR",
            "plan": plan,
            "key_id": self._settings.RAZORPAY_KEY_ID,
        }

    async def verify_payment(
        self,
        user: User,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> int:
        """Verify Razorpay payment signature and activate plan.

        Returns new credit balance.
        """
        # 1. Verify HMAC signature
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected = hmac.new(
            self._settings.RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, razorpay_signature):
            logger.warning(
                "payment_signature_invalid",
                order_id=razorpay_order_id,
            )
            raise ValueError("Invalid payment signature")

        # 2. Find the order event
        stmt = select(SubscriptionEvent).where(
            SubscriptionEvent.order_id == razorpay_order_id,
            SubscriptionEvent.user_id == user.id,
        )
        result = await self._db.execute(stmt)
        event = result.scalar_one_or_none()

        if event is None:
            raise ValueError("Order not found")

        if event.status == "captured":
            # Already processed — idempotent
            return user.credit_balance

        # 3. Update event
        event.razorpay_event_id = razorpay_payment_id
        event.status = "captured"

        # 4. Activate plan + add credits
        new_balance = await self._activate_plan(user, event.plan)
        await self._db.commit()

        logger.info(
            "payment_verified",
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            plan=event.plan,
            new_balance=new_balance,
        )

        return new_balance

    async def process_webhook(
        self,
        payload: dict,
        signature: str,
    ) -> None:
        """Process Razorpay webhook event (payment.captured).

        Verifies webhook signature and grants credits.
        """
        # 1. Verify webhook signature
        expected = hmac.new(
            self._settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            str(payload).encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            logger.warning("webhook_signature_invalid")
            return

        event_type = payload.get("event")
        if event_type != "payment.captured":
            logger.debug("webhook_ignored", event=event_type)
            return

        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment.get("order_id")
        payment_id = payment.get("id")
        notes = payment.get("notes", {})
        user_id = notes.get("user_id")
        plan = notes.get("plan")

        if not all([order_id, payment_id, user_id, plan]):
            logger.warning("webhook_missing_fields", payment=payment)
            return

        # Check idempotency
        existing = await self._db.execute(select(SubscriptionEvent).where(SubscriptionEvent.razorpay_event_id == payment_id))
        if existing.scalar_one_or_none():
            logger.info("webhook_already_processed", payment_id=payment_id)
            return

        # Find or create event
        stmt = select(SubscriptionEvent).where(SubscriptionEvent.order_id == order_id)
        result = await self._db.execute(stmt)
        event = result.scalar_one_or_none()

        if event:
            event.razorpay_event_id = payment_id
            event.status = "captured"
        else:
            plan_config = PLANS.get(plan, PLANS["monthly"])
            event = SubscriptionEvent(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                order_id=order_id,
                razorpay_event_id=payment_id,
                plan=plan,
                amount_paise=plan_config["amount_paise"],
                status="captured",
            )
            self._db.add(event)

        # Grant credits
        user_result = await self._db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = user_result.scalar_one_or_none()
        if user:
            await self._activate_plan(user, plan)

        await self._db.commit()
        logger.info(
            "webhook_processed",
            order_id=order_id,
            payment_id=payment_id,
            plan=plan,
        )

    async def get_plan_info(self, user: User) -> dict:
        """Get current plan info for user."""
        return {
            "plan": user.plan,
            "credit_balance": user.credit_balance,
            "plan_expires_at": (user.plan_expires_at.isoformat() if user.plan_expires_at else None),
            "plan_auto_renew": user.plan_auto_renew,
        }

    async def get_payment_history(self, user: User) -> list[SubscriptionEvent]:
        """Get payment history for user."""
        stmt = select(SubscriptionEvent).where(SubscriptionEvent.user_id == user.id).order_by(SubscriptionEvent.created_at.desc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def set_auto_renew(self, user: User, auto_renew: bool) -> None:
        """Toggle the user's auto-renewal preference."""
        from sqlalchemy import update

        await self._db.execute(update(User).where(User.id == user.id).values(plan_auto_renew=auto_renew))
        await self._db.commit()
        logger.info(
            "auto_renew_toggled",
            user_id=str(user.id),
            auto_renew=auto_renew,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _activate_plan(self, user: User, plan: str) -> int:
        """Add credits and set plan expiry."""
        plan_config = PLANS.get(plan, PLANS["monthly"])

        user.plan = plan
        user.credit_balance += plan_config["credits"]
        user.plan_expires_at = datetime.now(UTC) + timedelta(days=plan_config["duration_days"])
        await self._db.flush()

        return user.credit_balance
