"""Subscriptions router — create order, verify payment, webhook, plan info.

POST  /subscriptions/order — create Razorpay order
POST  /subscriptions/verify — verify payment signature + activate plan
POST  /subscriptions/webhook — Razorpay webhook (no CORS, no auth)
GET   /subscriptions/plan — current plan info
GET   /subscriptions/history — payment history
GET   /subscriptions/plans — available plans
PATCH /subscriptions/auto-renew — toggle auto-renewal
"""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.models.user import User
from app.schemas.subscriptions import (
    AutoRenewRequest,
    CreateOrderRequest,
    OrderResponse,
    PaymentHistoryResponse,
    PlanInfo,
    PlanInfoResponse,
    SubscriptionEventResponse,
    VerifyPaymentRequest,
)
from app.services.subscription_service import PLANS, SubscriptionService

router = APIRouter(tags=["subscriptions"])
logger = structlog.get_logger("regpulse.subscriptions")


def _get_svc(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(db=db)


# ---------------------------------------------------------------------------
# GET /subscriptions/plans — available plans (public)
# ---------------------------------------------------------------------------


@router.get("/plans")
async def list_plans() -> dict:
    """Return available subscription plans."""
    plans = []
    for key, config in PLANS.items():
        plans.append(
            {
                "id": key,
                "name": config["name"],
                "amount_paise": config["amount_paise"],
                "amount_display": f"\u20b9{config['amount_paise'] // 100:,}",
                "credits": config["credits"],
                "duration_days": config["duration_days"],
            }
        )
    return {"success": True, "data": plans}


# ---------------------------------------------------------------------------
# POST /subscriptions/order — create Razorpay order
# ---------------------------------------------------------------------------


@router.post("/order", response_model=OrderResponse)
async def create_order(
    body: CreateOrderRequest,
    user: User = Depends(require_verified_user),
    svc: SubscriptionService = Depends(_get_svc),
) -> OrderResponse:
    """Create a Razorpay order for the selected plan."""
    try:
        result = await svc.create_order(user, body.plan)
    except ValueError as e:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"success": False, "error": str(e), "code": "INVALID_PLAN"},
        )
    except Exception:
        logger.error("order_creation_failed", exc_info=True)
        return JSONResponse(  # type: ignore[return-value]
            status_code=500,
            content={
                "success": False,
                "error": "Failed to create order",
                "code": "ORDER_CREATION_FAILED",
            },
        )

    return OrderResponse(
        order_id=result["order_id"],
        amount_paise=result["amount_paise"],
        currency=result["currency"],
        plan=result["plan"],
    )


# ---------------------------------------------------------------------------
# POST /subscriptions/verify — verify payment + activate plan
# ---------------------------------------------------------------------------


@router.post("/verify")
async def verify_payment(
    body: VerifyPaymentRequest,
    user: User = Depends(require_verified_user),
    svc: SubscriptionService = Depends(_get_svc),
) -> dict:
    """Verify Razorpay payment signature and activate plan."""
    try:
        new_balance = await svc.verify_payment(
            user=user,
            razorpay_order_id=body.razorpay_order_id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_signature=body.razorpay_signature,
        )
    except ValueError as e:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "code": "PAYMENT_VERIFICATION_FAILED",
            },
        )

    return {
        "success": True,
        "message": "Payment verified and plan activated",
        "credit_balance": new_balance,
    }


# ---------------------------------------------------------------------------
# POST /subscriptions/webhook — Razorpay webhook (no auth, no CORS)
# ---------------------------------------------------------------------------


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    svc: SubscriptionService = Depends(_get_svc),
) -> dict:
    """Handle Razorpay webhook events. No auth required — verified via HMAC."""
    signature = request.headers.get("x-razorpay-signature", "")
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"success": False, "error": "Invalid JSON"},
        )

    try:
        await svc.process_webhook(payload, signature)
    except Exception:
        logger.error("webhook_processing_failed", exc_info=True)
        # Return 200 to prevent Razorpay retries on internal errors
        return {"success": True, "message": "Webhook received"}

    return {"success": True, "message": "Webhook processed"}


# ---------------------------------------------------------------------------
# GET /subscriptions/plan — current plan info
# ---------------------------------------------------------------------------


@router.get("/plan", response_model=PlanInfoResponse)
async def get_plan_info(
    user: User = Depends(require_verified_user),
    svc: SubscriptionService = Depends(_get_svc),
) -> PlanInfoResponse:
    """Get current subscription plan info."""
    info = await svc.get_plan_info(user)
    return PlanInfoResponse(data=PlanInfo(**info))


# ---------------------------------------------------------------------------
# GET /subscriptions/history — payment history
# ---------------------------------------------------------------------------


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    user: User = Depends(require_verified_user),
    svc: SubscriptionService = Depends(_get_svc),
) -> PaymentHistoryResponse:
    """Get payment history for the current user."""
    events = await svc.get_payment_history(user)
    return PaymentHistoryResponse(data=[SubscriptionEventResponse.model_validate(e) for e in events])


# ---------------------------------------------------------------------------
# PATCH /subscriptions/auto-renew — toggle auto-renewal
# ---------------------------------------------------------------------------


@router.patch("/auto-renew")
async def toggle_auto_renew(
    body: AutoRenewRequest,
    user: User = Depends(require_verified_user),
    svc: SubscriptionService = Depends(_get_svc),
) -> dict:
    """Toggle subscription auto-renewal preference."""
    await svc.set_auto_renew(user, body.auto_renew)
    return {
        "success": True,
        "message": f"Auto-renewal {'enabled' if body.auto_renew else 'disabled'}",
        "auto_renew": body.auto_renew,
    }
