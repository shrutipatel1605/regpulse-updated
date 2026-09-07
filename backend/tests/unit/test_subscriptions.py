"""Unit tests for subscription service and router."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.exceptions import RegPulseException, regpulse_exception_handler
from app.models.user import User
from app.routers.subscriptions import _get_svc, router
from app.services.subscription_service import PLANS, SubscriptionService


def _make_user() -> MagicMock:
    mock = MagicMock(spec=User)
    mock.id = uuid.uuid4()
    mock.email = "test@acmebank.com"
    mock.email_verified = True
    mock.is_active = True
    mock.is_admin = False
    mock.credit_balance = 5
    mock.plan = "free"
    mock.plan_expires_at = None
    mock.plan_auto_renew = True
    mock.full_name = "Test User"
    return mock


@pytest.fixture()
def mock_svc() -> AsyncMock:
    return AsyncMock(spec=SubscriptionService)


@pytest.fixture()
def app(mock_svc: AsyncMock) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/subscriptions")
    test_app.add_exception_handler(RegPulseException, regpulse_exception_handler)  # type: ignore[arg-type]

    mock_user = _make_user()
    test_app.dependency_overrides[_get_svc] = lambda: mock_svc
    test_app.dependency_overrides[get_db] = lambda: AsyncMock()
    test_app.dependency_overrides[require_verified_user] = lambda: mock_user
    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestListPlans:
    def test_returns_plan_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        plan_ids = {p["id"] for p in data["data"]}
        assert "monthly" in plan_ids
        assert "annual" in plan_ids

    def test_plan_has_required_fields(self, client: TestClient) -> None:
        response = client.get("/api/v1/subscriptions/plans")
        plan = response.json()["data"][0]
        assert "name" in plan
        assert "amount_paise" in plan
        assert "credits" in plan
        assert "duration_days" in plan


class TestCreateOrder:
    def test_create_order_success(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.create_order.return_value = {
            "order_id": "order_test123",
            "amount_paise": 299900,
            "currency": "INR",
            "plan": "monthly",
            "key_id": "rzp_test",
        }
        response = client.post(
            "/api/v1/subscriptions/order",
            json={"plan": "monthly"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["order_id"] == "order_test123"

    def test_create_order_invalid_plan(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/subscriptions/order",
            json={"plan": "invalid_plan"},
        )
        assert response.status_code == 422  # Pydantic validation


class TestVerifyPayment:
    def test_verify_success(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.verify_payment.return_value = 255
        response = client.post(
            "/api/v1/subscriptions/verify",
            json={
                "razorpay_order_id": "order_123",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "sig_abc",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credit_balance"] == 255

    def test_verify_invalid_signature(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.verify_payment.side_effect = ValueError("Invalid payment signature")
        response = client.post(
            "/api/v1/subscriptions/verify",
            json={
                "razorpay_order_id": "order_123",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "bad_sig",
            },
        )
        assert response.status_code == 400


class TestPlanInfo:
    def test_get_plan_info(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.get_plan_info.return_value = {
            "plan": "monthly",
            "credit_balance": 245,
            "plan_expires_at": "2026-04-26T00:00:00+00:00",
            "plan_auto_renew": True,
        }
        response = client.get("/api/v1/subscriptions/plan")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["plan"] == "monthly"
        assert data["data"]["credit_balance"] == 245


class TestPaymentHistory:
    def test_empty_history(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.get_payment_history.return_value = []
        response = client.get("/api/v1/subscriptions/history")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []


class TestPlanConfig:
    def test_monthly_plan_exists(self) -> None:
        assert "monthly" in PLANS
        assert PLANS["monthly"]["credits"] == 250
        assert PLANS["monthly"]["amount_paise"] == 299900

    def test_annual_plan_exists(self) -> None:
        assert "annual" in PLANS
        assert PLANS["annual"]["credits"] == 3000
