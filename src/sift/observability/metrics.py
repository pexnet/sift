from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Final

_METRIC_HELP: Final[dict[str, str]] = {
    "sift_http_requests_total": "Total HTTP requests by method, route, and status class.",
    "sift_http_request_duration_seconds": "Total HTTP request duration in seconds by method, route, and status class.",
    "sift_scheduler_loops_total": "Total scheduler loop executions by result.",
    "sift_scheduler_loop_duration_seconds": "Total scheduler loop duration in seconds.",
    "sift_scheduler_due_feeds_total": "Total due feeds seen by scheduler.",
    "sift_scheduler_enqueues_total": "Total scheduler enqueue attempts by result.",
    "sift_scheduler_enqueued_jobs_total": "Total jobs enqueued by scheduler.",
    "sift_queue_depth": "Current queue depth by queue name.",
    "sift_queue_oldest_job_age_seconds": "Current oldest queued job age in seconds by queue name.",
    "sift_worker_jobs_total": "Total worker jobs processed by result.",
    "sift_worker_job_duration_seconds": "Total worker job duration in seconds by result.",
    "sift_ingest_runs_total": "Total ingestion runs by result.",
    "sift_ingest_run_duration_seconds": "Total ingestion run duration in seconds by result.",
    "sift_ingest_entries_fetched_total": "Total fetched entries observed during ingestion runs.",
    "sift_ingest_entries_inserted_total": "Total inserted entries observed during ingestion runs.",
    "sift_ingest_entries_duplicate_total": "Total duplicate entries observed during ingestion runs.",
    "sift_ingest_entries_filtered_total": "Total filtered entries observed during ingestion runs.",
    "sift_ingest_plugin_processed_total": "Total plugin-processed entries observed during ingestion runs.",
}

_METRIC_TYPE: Final[dict[str, str]] = {
    "sift_http_requests_total": "counter",
    "sift_http_request_duration_seconds": "counter",
    "sift_scheduler_loops_total": "counter",
    "sift_scheduler_loop_duration_seconds": "counter",
    "sift_scheduler_due_feeds_total": "counter",
    "sift_scheduler_enqueues_total": "counter",
    "sift_scheduler_enqueued_jobs_total": "counter",
    "sift_queue_depth": "gauge",
    "sift_queue_oldest_job_age_seconds": "gauge",
    "sift_worker_jobs_total": "counter",
    "sift_worker_job_duration_seconds": "counter",
    "sift_ingest_runs_total": "counter",
    "sift_ingest_run_duration_seconds": "counter",
    "sift_ingest_entries_fetched_total": "counter",
    "sift_ingest_entries_inserted_total": "counter",
    "sift_ingest_entries_duplicate_total": "counter",
    "sift_ingest_entries_filtered_total": "counter",
    "sift_ingest_plugin_processed_total": "counter",
}


@dataclass(frozen=True, slots=True)
class MetricSample:
    labels: dict[str, str]
    value: float


def _sanitize_result(value: str) -> str:
    normalized = value.strip().lower()
    return normalized or "unknown"


def _sanitize_route(route: str) -> str:
    normalized = route.strip()
    return normalized or "/"


def _sanitize_method(method: str) -> str:
    normalized = method.strip().upper()
    return normalized or "GET"


def _status_class(status_code: int) -> str:
    clamped = min(max(status_code, 100), 599)
    return f"{clamped // 100}xx"


def _safe_count(value: int) -> float:
    return float(max(0, value))


def _safe_seconds(value: float) -> float:
    return max(0.0, value)


class ObservabilityMetrics:
    def __init__(self) -> None:
        counter_names = [name for name, metric_type in _METRIC_TYPE.items() if metric_type == "counter"]
        gauge_names = [name for name, metric_type in _METRIC_TYPE.items() if metric_type == "gauge"]
        self._counter_values: dict[str, dict[tuple[tuple[str, str], ...], float]] = {
            metric_name: defaultdict(float) for metric_name in counter_names
        }
        self._gauge_values: dict[str, dict[tuple[tuple[str, str], ...], float]] = {
            metric_name: {} for metric_name in gauge_names
        }
        self._lock = Lock()

    def _label_key(self, labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted((key, value) for key, value in labels.items()))

    def _inc_counter(self, metric_name: str, *, labels: dict[str, str], amount: float) -> None:
        safe_amount = _safe_seconds(amount)
        if safe_amount <= 0:
            return
        key = self._label_key(labels)
        with self._lock:
            self._counter_values[metric_name][key] += safe_amount

    def _set_gauge(self, metric_name: str, *, labels: dict[str, str], value: float) -> None:
        key = self._label_key(labels)
        safe_value = _safe_seconds(value)
        with self._lock:
            self._gauge_values[metric_name][key] = safe_value

    def reset(self) -> None:
        with self._lock:
            for metric_name in self._counter_values:
                self._counter_values[metric_name].clear()
            for metric_name in self._gauge_values:
                self._gauge_values[metric_name].clear()

    def record_http_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        labels = {
            "method": _sanitize_method(method),
            "route": _sanitize_route(route),
            "status_class": _status_class(status_code),
        }
        self._inc_counter("sift_http_requests_total", labels=labels, amount=1.0)
        self._inc_counter(
            "sift_http_request_duration_seconds",
            labels=labels,
            amount=_safe_seconds(duration_seconds),
        )

    def record_scheduler_loop(self, *, result: str, duration_seconds: float) -> None:
        self._inc_counter(
            "sift_scheduler_loops_total",
            labels={"result": _sanitize_result(result)},
            amount=1.0,
        )
        self._inc_counter(
            "sift_scheduler_loop_duration_seconds",
            labels={},
            amount=_safe_seconds(duration_seconds),
        )

    def record_scheduler_due_feeds(self, *, count: int) -> None:
        self._inc_counter(
            "sift_scheduler_due_feeds_total",
            labels={},
            amount=_safe_count(count),
        )

    def record_scheduler_enqueue(self, *, result: str, count: int = 1) -> None:
        self._inc_counter(
            "sift_scheduler_enqueues_total",
            labels={"result": _sanitize_result(result)},
            amount=_safe_count(count),
        )

    def record_scheduler_enqueued_jobs(self, *, count: int) -> None:
        self._inc_counter(
            "sift_scheduler_enqueued_jobs_total",
            labels={},
            amount=_safe_count(count),
        )

    def set_queue_depth(self, *, queue: str, depth: int) -> None:
        self._set_gauge(
            "sift_queue_depth",
            labels={"queue": queue},
            value=_safe_count(depth),
        )

    def set_queue_oldest_job_age(self, *, queue: str, age_seconds: float) -> None:
        self._set_gauge(
            "sift_queue_oldest_job_age_seconds",
            labels={"queue": queue},
            value=_safe_seconds(age_seconds),
        )

    def record_worker_job(self, *, result: str, duration_seconds: float) -> None:
        labels = {"result": _sanitize_result(result)}
        self._inc_counter("sift_worker_jobs_total", labels=labels, amount=1.0)
        self._inc_counter(
            "sift_worker_job_duration_seconds",
            labels=labels,
            amount=_safe_seconds(duration_seconds),
        )

    def record_ingest_run(
        self,
        *,
        result: str,
        duration_seconds: float,
        fetched_count: int,
        inserted_count: int,
        duplicate_count: int,
        filtered_count: int,
        plugin_processed_count: int,
    ) -> None:
        labels = {"result": _sanitize_result(result)}
        self._inc_counter("sift_ingest_runs_total", labels=labels, amount=1.0)
        self._inc_counter(
            "sift_ingest_run_duration_seconds",
            labels=labels,
            amount=_safe_seconds(duration_seconds),
        )
        self._inc_counter(
            "sift_ingest_entries_fetched_total",
            labels={},
            amount=_safe_count(fetched_count),
        )
        self._inc_counter(
            "sift_ingest_entries_inserted_total",
            labels={},
            amount=_safe_count(inserted_count),
        )
        self._inc_counter(
            "sift_ingest_entries_duplicate_total",
            labels={},
            amount=_safe_count(duplicate_count),
        )
        self._inc_counter(
            "sift_ingest_entries_filtered_total",
            labels={},
            amount=_safe_count(filtered_count),
        )
        self._inc_counter(
            "sift_ingest_plugin_processed_total",
            labels={},
            amount=_safe_count(plugin_processed_count),
        )

    def snapshot(self) -> dict[str, list[MetricSample]]:
        with self._lock:
            counters = {
                metric_name: sorted(values.items(), key=lambda item: item[0])
                for metric_name, values in self._counter_values.items()
            }
            gauges = {
                metric_name: sorted(values.items(), key=lambda item: item[0])
                for metric_name, values in self._gauge_values.items()
            }

        snapshot: dict[str, list[MetricSample]] = {}
        for metric_name in _METRIC_HELP:
            counter_items = counters.get(metric_name, [])
            gauge_items = gauges.get(metric_name, [])
            source_items = counter_items if counter_items else gauge_items
            snapshot[metric_name] = [
                MetricSample(labels=dict(label_key), value=value) for label_key, value in source_items
            ]
        return snapshot

    def render_prometheus(self) -> str:
        snapshot = self.snapshot()
        lines: list[str] = []
        for metric_name in _METRIC_HELP:
            lines.append(f"# HELP {metric_name} {_METRIC_HELP[metric_name]}")
            lines.append(f"# TYPE {metric_name} {_METRIC_TYPE[metric_name]}")
            for sample in snapshot.get(metric_name, []):
                labels = ",".join(
                    f'{label_key}="{_escape_label_value(label_value)}"'
                    for label_key, label_value in sorted(sample.labels.items())
                )
                if labels:
                    lines.append(f"{metric_name}{{{labels}}} {sample.value}")
                else:
                    lines.append(f"{metric_name} {sample.value}")
        return "\n".join(lines) + "\n"


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@lru_cache
def get_observability_metrics() -> ObservabilityMetrics:
    return ObservabilityMetrics()

