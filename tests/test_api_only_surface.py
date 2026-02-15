from fastapi.testclient import TestClient

from sift.main import app


def test_web_routes_removed_api_only_surface() -> None:
    with TestClient(app) as client:
        for path in ("/app", "/login", "/register", "/account", "/logout"):
            response = client.get(path)
            assert response.status_code == 404
        assert client.get("/static/app.js").status_code == 404

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
