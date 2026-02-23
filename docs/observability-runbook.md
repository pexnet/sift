# Observability Runbook (v1)

This runbook documents the current backend observability contract for Sift API, scheduler, and worker runtimes.

## Scope

- Structured JSON logs with request/job correlation metadata.
- Prometheus-compatible metric names under `sift_*`.
- VMUI-first operational workflow with VictoriaMetrics and VictoriaLogs compatibility.

## Runtime Configuration

Set these environment variables (all use `SIFT_` prefix):

- `OBSERVABILITY_ENABLED` (`true` default)
- `METRICS_ENABLED` (`true` default)
- `METRICS_PATH` (`/metrics` default)
- `METRICS_BIND_HOST` (`0.0.0.0` default)
- `METRICS_SCHEDULER_PORT` (`9101` default)
- `METRICS_WORKER_PORT` (`9102` default)
- `LOG_LEVEL` (`INFO` default)
- `LOG_FORMAT` (`json` default)
- `LOG_REDACT_FIELDS` (comma-separated extra redact keys)
- `REQUEST_ID_HEADER` (`X-Request-Id` default)

## HTTP and Request Correlation

- API responses include `X-Request-Id`.
- Incoming request IDs are passed through when present.
- Missing request IDs are generated server-side.
- API lifecycle log events:
  - `api.request.start`
  - `api.request.complete`
  - `api.request.error`

## Metrics Endpoint

- API endpoint: `GET /metrics` (path configurable by `SIFT_METRICS_PATH`).
- Scheduler endpoint: `http://<scheduler-host>:<SIFT_METRICS_SCHEDULER_PORT><SIFT_METRICS_PATH>`.
- Worker endpoint: `http://<worker-host>:<SIFT_METRICS_WORKER_PORT><SIFT_METRICS_PATH>`.
- Format: Prometheus text exposition (`text/plain; version=0.0.4`).
- Current export surface:
  - API process runtime metrics + plugin runtime telemetry metrics
  - Scheduler process runtime metrics
  - Worker process runtime metrics

## Metric Dictionary

### HTTP

- `sift_http_requests_total{method,route,status_class}`
- `sift_http_request_duration_seconds{method,route,status_class}`

### Scheduler

- `sift_scheduler_loops_total{result}`
- `sift_scheduler_loop_duration_seconds`
- `sift_scheduler_due_feeds_total`
- `sift_scheduler_enqueues_total{result}`
- `sift_scheduler_enqueued_jobs_total`

### Queue/Worker

- `sift_queue_depth{queue}`
- `sift_queue_oldest_job_age_seconds{queue}`
- `sift_worker_jobs_total{result}`
- `sift_worker_job_duration_seconds{result}`

### Ingestion

- `sift_ingest_runs_total{result}`
- `sift_ingest_run_duration_seconds{result}`
- `sift_ingest_entries_fetched_total`
- `sift_ingest_entries_inserted_total`
- `sift_ingest_entries_duplicate_total`
- `sift_ingest_entries_filtered_total`
- `sift_ingest_plugin_processed_total`

### Plugin Runtime

- `sift_plugin_invocations_total{plugin_id,capability,result}`
- `sift_plugin_invocation_duration_seconds{plugin_id,capability,result}`
- `sift_plugin_timeouts_total{plugin_id,capability}`
- `sift_plugin_dispatch_failures_total{capability}`

## Log Event Catalog

### API

- `api.request.start`
- `api.request.complete`
- `api.request.error`

### Scheduler

- `scheduler.process.start`
- `scheduler.loop.start`
- `scheduler.loop.complete`
- `scheduler.loop.error`
- `scheduler.enqueue.success`
- `scheduler.enqueue.skip_due`
- `scheduler.enqueue.skip_active_job`
- `scheduler.enqueue.error`

### Worker

- `worker.process.start`
- `worker.job.start`
- `worker.job.complete`
- `worker.job.error`

### Ingestion

- `ingest.run.start`
- `ingest.run.complete`
- `ingest.run.error`

### Plugin Runtime

- `plugin.dispatch.start`
- `plugin.dispatch.complete`
- `plugin.dispatch.error`
- `plugin.dispatch.timeout`

## Required JSON Log Fields

- `ts`
- `level`
- `service`
- `env`
- `event`
- `message`

Common contextual fields:

- `request_id`
- `route`
- `method`
- `status_code`
- `duration_ms`
- `feed_id`
- `job_id`
- `queue_name`
- `error_type`

## Redaction Policy

- Sensitive fields are masked as `[REDACTED]`.
- Baseline sensitive keys include:
  - `password`, `password_hash`
  - `token`, `access_token`, `refresh_token`
  - `authorization`
  - `cookie`, `set-cookie`
  - `session_id`, `session_token`
  - `content`, `content_text`, `content_html`
  - `payload`
- Add environment-specific keys through `SIFT_LOG_REDACT_FIELDS`.

## VictoriaMetrics / VMUI Setup Notes

Minimal scrape target for API metrics:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: sift-api
    static_configs:
      - targets:
          - sift-api:8000
    metrics_path: /metrics
  - job_name: sift-scheduler
    static_configs:
      - targets:
          - sift-scheduler:9101
    metrics_path: /metrics
  - job_name: sift-worker
    static_configs:
      - targets:
          - sift-worker:9102
    metrics_path: /metrics
```

Load this into your metrics scraper (Prometheus or `vmagent`) and point it at Sift API.

Recommended initial VMUI panels:

- `sum(rate(sift_http_requests_total[5m])) by (route, status_class)`
- `sum(rate(sift_http_request_duration_seconds[5m])) by (route) / sum(rate(sift_http_requests_total[5m])) by (route)`
- `sum(rate(sift_ingest_runs_total[5m])) by (result)`
- `sum(rate(sift_worker_jobs_total[5m])) by (result)`
- `max(sift_queue_depth) by (queue)`
- `max(sift_queue_oldest_job_age_seconds) by (queue)`

## VictoriaLogs Notes

- Sift emits structured JSON logs to stdout/stderr.
- Ship logs to VictoriaLogs with your preferred log shipper.
- Filter by `event` and `request_id` for request/job correlation.

Suggested starter queries:

- `event:api.request.error`
- `event:ingest.run.error`
- `event:scheduler.enqueue.error`
- `event:worker.job.error`

## Operational Checks

- API health: `GET /api/v1/health`
- Metrics health: `GET /metrics` returns `200` and `sift_*` metric names.
- Request ID propagation:
  - send request with `X-Request-Id`
  - verify same header in response
  - verify logs include matching `request_id`
