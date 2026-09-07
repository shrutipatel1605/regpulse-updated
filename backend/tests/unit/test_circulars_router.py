"""Unit tests for the circulars router endpoints.

Uses TestClient with dependency overrides to test route logic
without requiring a real database or embedding service.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_db
from app.dependencies.auth import require_verified_user
from app.exceptions import RegPulseException, regpulse_exception_handler
from app.models.user import User
from app.routers.circulars import _get_service, router


def _make_circular(**overrides) -> MagicMock:  # noqa: ANN003
    """Create a mock CircularDocument with all required attributes."""
    defaults = {
        "id": uuid.uuid4(),
        "circular_number": "RBI/2024-25/01",
        "title": "Test Circular on KYC",
        "doc_type": "CIRCULAR",
        "department": "Department of Regulation",
        "issued_date": date(2024, 6, 15),
        "effective_date": date(2024, 7, 1),
        "rbi_url": "https://rbi.org.in/test",
        "status": "ACTIVE",
        "impact_level": "HIGH",
        "action_deadline": date(2024, 9, 30),
        "affected_teams": ["Compliance"],
        "tags": ["KYC"],
        "regulator": "RBI",
        "indexed_at": datetime(2024, 6, 16, tzinfo=UTC),
        "updated_at": datetime(2024, 6, 16, tzinfo=UTC),
        "ai_summary": "Test summary",
        "pending_admin_review": False,
        "superseded_by": None,
        "chunks": [],
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_user() -> MagicMock:
    """Create a mock verified user."""
    mock = MagicMock(spec=User)
    mock.id = uuid.uuid4()
    mock.email = "test@acmebank.com"
    mock.email_verified = True
    mock.is_active = True
    mock.is_admin = False
    mock.credit_balance = 10
    return mock


@pytest.fixture()
def mock_svc() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def app(mock_svc: AsyncMock) -> FastAPI:
    """Create a test FastAPI app with dependency overrides."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/circulars")
    test_app.add_exception_handler(RegPulseException, regpulse_exception_handler)  # type: ignore[arg-type]

    # Override service dependency
    test_app.dependency_overrides[_get_service] = lambda: mock_svc
    # Override DB (not used with service override, but prevents import errors)
    test_app.dependency_overrides[get_db] = lambda: AsyncMock()

    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestListEndpoint:
    """Test GET /api/v1/circulars."""

    def test_list_circulars_returns_200(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_circular = _make_circular()
        mock_svc.list_circulars.return_value = ([mock_circular], 1)

        response = client.get("/api/v1/circulars")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Test Circular on KYC"

    def test_list_with_filters(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.list_circulars.return_value = ([], 0)

        response = client.get(
            "/api/v1/circulars",
            params={
                "doc_type": "CIRCULAR",
                "status": "ACTIVE",
                "impact_level": "HIGH",
                "page": 1,
                "page_size": 10,
            },
        )
        assert response.status_code == 200
        mock_svc.list_circulars.assert_called_once()

    def test_list_pagination_metadata(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.list_circulars.return_value = ([], 50)

        response = client.get("/api/v1/circulars", params={"page": 2, "page_size": 10})
        data = response.json()
        assert data["total"] == 50
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_pages"] == 5

    def test_list_empty_result(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.list_circulars.return_value = ([], 0)
        response = client.get("/api/v1/circulars")
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 0
        assert data["data"] == []


class TestAutocompleteEndpoint:
    """Test GET /api/v1/circulars/autocomplete."""

    def test_autocomplete_returns_200(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_circular = _make_circular()
        mock_svc.autocomplete.return_value = [mock_circular]

        response = client.get("/api/v1/circulars/autocomplete", params={"q": "KYC"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Test Circular on KYC"

    def test_autocomplete_requires_query(self, client: TestClient, mock_svc: AsyncMock) -> None:
        response = client.get("/api/v1/circulars/autocomplete")
        assert response.status_code == 422  # Missing required param

    def test_autocomplete_empty_result(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.autocomplete.return_value = []
        response = client.get("/api/v1/circulars/autocomplete", params={"q": "xyz"})
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []


class TestDetailEndpoint:
    """Test GET /api/v1/circulars/{circular_id}."""

    def test_get_detail_returns_200(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_circular = _make_circular()
        mock_svc.get_detail.return_value = mock_circular

        response = client.get(f"/api/v1/circulars/{mock_circular.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Circular on KYC"
        assert data["data"]["rbi_url"] == "https://rbi.org.in/test"

    def test_get_detail_not_found(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.get_detail.return_value = None
        response = client.get(f"/api/v1/circulars/{uuid.uuid4()}")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["code"] == "CIRCULAR_NOT_FOUND"


class TestFacetEndpoints:
    """Test facet/filter data endpoints."""

    def test_departments_returns_200(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.get_departments.return_value = [
            "Dept of Regulation",
            "Dept of Supervision",
        ]

        response = client.get("/api/v1/circulars/departments")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_tags_returns_200(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.get_tags.return_value = ["KYC", "Digital Lending", "PSL"]

        response = client.get("/api/v1/circulars/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    def test_doc_types_returns_200(self, client: TestClient, mock_svc: AsyncMock) -> None:
        mock_svc.get_doc_types.return_value = ["CIRCULAR", "MASTER_DIRECTION"]

        response = client.get("/api/v1/circulars/doc-types")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2


class TestSearchEndpoint:
    """Test GET /api/v1/circulars/search."""

    def test_search_requires_auth(self, client: TestClient, mock_svc: AsyncMock) -> None:
        response = client.get("/api/v1/circulars/search", params={"query": "KYC requirements"})
        # Should fail without auth (401 or 403)
        assert response.status_code in (401, 403)

    def test_search_returns_results(self, app: FastAPI, mock_svc: AsyncMock) -> None:
        mock_circular = _make_circular()
        mock_svc.hybrid_search.return_value = (
            [
                {
                    "circular": mock_circular,
                    "relevance_score": 0.85,
                    "snippet": "KYC requirements for banks...",
                }
            ],
            1,
        )

        # Override auth dependency
        mock_user = _make_user()
        app.dependency_overrides[require_verified_user] = lambda: mock_user

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/circulars/search", params={"query": "KYC requirements"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["relevance_score"] == 0.85
        assert data["data"][0]["snippet"] == "KYC requirements for banks..."

    def test_search_query_too_short(self, app: FastAPI, mock_svc: AsyncMock) -> None:
        mock_user = _make_user()
        app.dependency_overrides[require_verified_user] = lambda: mock_user

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/circulars/search", params={"query": "ab"})
        assert response.status_code == 422

    def test_search_empty_results(self, app: FastAPI, mock_svc: AsyncMock) -> None:
        mock_svc.hybrid_search.return_value = ([], 0)
        mock_user = _make_user()
        app.dependency_overrides[require_verified_user] = lambda: mock_user

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/circulars/search", params={"query": "nonexistent query"})
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 0
        assert data["data"] == []
