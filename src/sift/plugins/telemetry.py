from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Final

_ALLOWED_RESULTS: Final[frozenset[str]] = frozenset({"success", "failure", "timeout"})

_METRIC_HELP: Final[dict[str, str]] = {
    "sift_plugin_invocations_total": "Total plugin invocations by plugin, capability, and result.",
    "sift_plugin_invocation_duration_seconds": "Total plugin invocation duration in seconds by result.",
    "sift_plugin_timeouts_total": "Total plugin timeouts by plugin and capability.",
    "sift_plugin_dispatch_failures_total": "Total plugin dispatch failures by capability.",
}

_METRIC_TYPE: Final[dict[str, str]] = {
    "sift_plugin_invocations_total": "counter",
    "sift_plugin_invocation_duration_seconds": "counter",
    "sift_plugin_timeouts_total": "counter",
    "sift_plugin_dispatch_failures_total": "counter",
}


@dataclass(frozen=True, slots=True)
class PluginMetricSample:
    labels: dict[str, str]
    value: float


class PluginTelemetryCollector:
    def __init__(self) -> None:
        self._invocations_total: dict[tuple[str, str, str], int] = defaultdict(int)
        self._invocation_duration_seconds: dict[tuple[str, str, str], float] = defaultdict(float)
        self._timeouts_total: dict[tuple[str, str], int] = defaultdict(int)
        self._dispatch_failures_total: dict[str, int] = defaultdict(int)
        self._lock = Lock()

    def record_invocation(self, *, plugin_id: str, capability: str, result: str, duration_seconds: float) -> None:
        normalized_result = result.strip().lower()
        if normalized_result not in _ALLOWED_RESULTS:
            raise ValueError(f"Unsupported plugin telemetry result '{result}'")

        safe_duration = max(0.0, duration_seconds)
        key = (plugin_id, capability, normalized_result)
        with self._lock:
            self._invocations_total[key] += 1
            self._invocation_duration_seconds[key] += safe_duration

    def record_timeout(self, *, plugin_id: str, capability: str) -> None:
        key = (plugin_id, capability)
        with self._lock:
            self._timeouts_total[key] += 1

    def record_dispatch_failure(self, *, capability: str) -> None:
        with self._lock:
            self._dispatch_failures_total[capability] += 1

    def snapshot(self) -> dict[str, list[PluginMetricSample]]:
        with self._lock:
            invocations = sorted(self._invocations_total.items(), key=lambda item: item[0])
            durations = sorted(self._invocation_duration_seconds.items(), key=lambda item: item[0])
            timeouts = sorted(self._timeouts_total.items(), key=lambda item: item[0])
            failures = sorted(self._dispatch_failures_total.items(), key=lambda item: item[0])

        return {
            "sift_plugin_invocations_total": [
                PluginMetricSample(
                    labels={"plugin_id": plugin_id, "capability": capability, "result": result},
                    value=float(value),
                )
                for (plugin_id, capability, result), value in invocations
            ],
            "sift_plugin_invocation_duration_seconds": [
                PluginMetricSample(
                    labels={"plugin_id": plugin_id, "capability": capability, "result": result},
                    value=value,
                )
                for (plugin_id, capability, result), value in durations
            ],
            "sift_plugin_timeouts_total": [
                PluginMetricSample(
                    labels={"plugin_id": plugin_id, "capability": capability},
                    value=float(value),
                )
                for (plugin_id, capability), value in timeouts
            ],
            "sift_plugin_dispatch_failures_total": [
                PluginMetricSample(
                    labels={"capability": capability},
                    value=float(value),
                )
                for capability, value in failures
            ],
        }

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
