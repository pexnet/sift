import logging
from collections.abc import Awaitable, Callable
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from sift.main import app, observability_middleware
from sift.observability.logging import get_request_id
from sift.observability.metrics import MetricSample, get_observability_metrics


def _sample_map(
    samples: list[MetricSample],
    *,
    label_keys: tuple[str, ...],
) -> dict[tuple[str, ...], float]:
    mapped: dict[tuple[str, ...], float] = {}
    for sample in samples:
        key = tuple(sample.labels[key] for key in label_keys)
        mapped[key] = sample.value
    return mapped


async def _receive() -> dict[str, object]:
    return {"type": "http.request", "body": b"", "more_body": False}


def _request_scope(*, path: str, method: str, headers: list[tuple[bytes, bytes]]) -> dict[str, object]:
    return {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }


def test_request_id_header_pass_through() -> None:
    get_observability_metrics().reset()
    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"X-Request-Id": "req-test-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-test-123"


def test_request_id_header_generated_when_missing() -> None:
    get_observability_metrics().reset()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    generated_request_id = response.headers.get("X-Request-Id")
    assert isinstance(generated_request_id, str)
    assert generated_request_id != ""


def test_metrics_endpoint_includes_observability_contract_names() -> None:
    get_observability_metrics().reset()
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    metrics_text = metrics_response.text
    expected_metric_names = [
        "sift_http_requests_total",
        "sift_http_request_duration_seconds",
        "sift_scheduler_loops_total",
        "sift_scheduler_loop_duration_seconds",
        "sift_scheduler_due_feeds_total",
        "sift_scheduler_enqueues_total",
        "sift_scheduler_enqueued_jobs_total",
        "sift_queue_depth",
        "sift_queue_oldest_job_age_seconds",
        "sift_worker_jobs_total",
        "sift_worker_job_duration_seconds",
        "sift_ingest_runs_total",
        "sift_ingest_run_duration_seconds",
        "sift_ingest_entries_fetched_total",
        "sift_ingest_entries_inserted_total",
        "sift_ingest_entries_duplicate_total",
        "sift_ingest_entries_filtered_total",
        "sift_ingest_plugin_processed_total",
        "sift_plugin_invocations_total",
    ]
    for metric_name in expected_metric_names:
        assert metric_name in metrics_text


@pytest.mark.asyncio
async def test_request_id_is_logged_and_metrics_recorded_on_exception(caplog: pytest.LogCaptureFixture) -> None:
    metrics = get_observability_metrics()
    metrics.reset()
    caplog.set_level(logging.ERROR, logger="sift.main")

    request = Request(
        _request_scope(path="/boom", method="GET", headers=[(b"x-request-id", b"req-exception-123")]),
        _receive,
    )

    async def failing_call_next(_request: Request) -> Response:
        raise RuntimeError("simulated failure")

    with pytest.raises(RuntimeError):
        await observability_middleware(
            request=request,
            call_next=cast(Callable[[Request], Awaitable[Response]], failing_call_next),
        )

    error_records = [record for record in caplog.records if getattr(record, "event", "") == "api.request.error"]
    assert error_records
    assert getattr(error_records[-1], "request_id", None) == "req-exception-123"
    assert get_request_id() is None

    snapshot = metrics.snapshot()
    totals = _sample_map(snapshot["sift_http_requests_total"], label_keys=("method", "route", "status_class"))
    assert totals[("GET", "/boom", "5xx")] == 1.0
