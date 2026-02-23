import httpx

from sift.observability.metrics import get_observability_metrics
from sift.observability.metrics_server import start_metrics_http_server


def test_metrics_server_serves_prometheus_payload() -> None:
    metrics = get_observability_metrics()
    metrics.reset()
    metrics.record_worker_job(result="success", duration_seconds=0.25)

    server = start_metrics_http_server(
        service_name="test-service",
        enabled=True,
        host="127.0.0.1",
        port=0,
        path="/metrics",
    )
    assert server is not None

    try:
        response = httpx.get(f"http://127.0.0.1:{server.port}/metrics", timeout=2.0)
    finally:
        server.close()

    assert response.status_code == 200
    body = response.text
    assert "sift_worker_jobs_total{result=\"success\"} 1.0" in body


def test_metrics_server_returns_404_for_non_metrics_path() -> None:
    server = start_metrics_http_server(
        service_name="test-service",
        enabled=True,
        host="127.0.0.1",
        port=0,
        path="/metrics",
    )
    assert server is not None

    try:
        response = httpx.get(f"http://127.0.0.1:{server.port}/not-metrics", timeout=2.0)
    finally:
        server.close()

    assert response.status_code == 404


def test_metrics_server_not_started_when_disabled() -> None:
    server = start_metrics_http_server(
        service_name="test-service",
        enabled=False,
        host="127.0.0.1",
        port=0,
        path="/metrics",
    )
    assert server is None
