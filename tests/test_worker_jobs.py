from uuid import uuid4

import pytest

import sift.tasks.jobs as jobs_module
from sift.observability.metrics import MetricSample, get_observability_metrics


def _sample_map(samples: list[MetricSample], *, label_keys: tuple[str, ...]) -> dict[tuple[str, ...], float]:
    mapped: dict[tuple[str, ...], float] = {}
    for sample in samples:
        key = tuple(sample.labels[key] for key in label_keys)
        mapped[key] = sample.value
    return mapped


def test_ingest_feed_job_records_failure_metrics_for_invalid_feed_id() -> None:
    metrics = get_observability_metrics()
    metrics.reset()

    payload = jobs_module.ingest_feed_job("not-a-uuid")
    assert payload["status"] == "invalid"

    snapshot = metrics.snapshot()
    results = _sample_map(snapshot["sift_worker_jobs_total"], label_keys=("result",))
    assert results[("failure",)] == 1.0


def test_ingest_feed_job_records_success_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    metrics = get_observability_metrics()
    metrics.reset()

    async def fake_run_ingest(_feed_id):  # type: ignore[no-untyped-def]
        return {"feed_id": str(_feed_id), "errors": []}

    monkeypatch.setattr(jobs_module, "_run_ingest", fake_run_ingest)

    payload = jobs_module.ingest_feed_job(str(uuid4()))
    assert payload["status"] == "ok"

    snapshot = metrics.snapshot()
    results = _sample_map(snapshot["sift_worker_jobs_total"], label_keys=("result",))
    assert results[("success",)] == 1.0
