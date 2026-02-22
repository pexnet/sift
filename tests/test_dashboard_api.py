from fastapi.testclient import TestClient

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.main import app


def test_dashboard_summary_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"


def test_dashboard_summary_returns_card_availability_for_authenticated_user() -> None:
    async def override_current_user() -> User:
        return User(email="dashboard-user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/summary")
            assert response.status_code == 200
            payload = response.json()
            assert "last_updated_at" in payload
            assert len(payload["cards"]) >= 1
            by_id = {item["id"]: item for item in payload["cards"]}
            assert by_id["saved_followup"]["status"] == "ready"
            assert by_id["trends"]["status"] == "unavailable"
            assert by_id["trends"]["dependency_spec"] == "docs/specs/trends-detection-dashboard-v1.md"
    finally:
        app.dependency_overrides.clear()
