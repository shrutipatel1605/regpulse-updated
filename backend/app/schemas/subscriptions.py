"""Subscription and payment schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Requests ---


class CreateOrderRequest(BaseModel):
    plan: str = Field(pattern=r"^(monthly|annual)$")


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class AutoRenewRequest(BaseModel):
    auto_renew: bool


# --- Responses ---


class OrderResponse(BaseModel):
    success: bool = True
    order_id: str
    amount_paise: int
    currency: str = "INR"
    plan: str


class SubscriptionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: str | None = None
    razorpay_event_id: str | None = None
    plan: str
    amount_paise: int
    status: str
    created_at: datetime


class PaymentHistoryResponse(BaseModel):
    success: bool = True
    data: list[SubscriptionEventResponse]


class PlanInfo(BaseModel):
    plan: str
    credit_balance: int
    plan_expires_at: datetime | None = None
    plan_auto_renew: bool


class PlanInfoResponse(BaseModel):
    success: bool = True
    data: PlanInfo
