# Scheduler and Ingestion Observability v1

## Status

- State: Completed (2026-02-23)
- Scope: Scheduler + ingestion observability backend runtime slice (implemented)
- Backlog reference: [docs/backlog.md](../../backlog.md)

## Context

Sift currently runs API, scheduler, and worker processes, but observability is not yet standardized. Logging is
inconsistent across services, scheduler/worker telemetry is limited, and operators do not have a defined
vendor-neutral contract for metrics and logs.

This spec defines an implementation-ready observability baseline that remains backend-agnostic while being explicitly
compatible with VictoriaMetrics and VictoriaLogs.

## Locked Decisions

1. OTel-aligned semantics with Prometheus-compatible metrics.
2. VMUI-first operational posture for resource-efficient self-hosting.
3. Metadata-only logs by default (no full payload/article content logging).
4. No collector required in v1.
5. Trace-ready contracts in v1; trace backend rollout deferred.

## Goals

1. Add stable metrics for scheduler/worker/ingestion health, latency, and failures.
2. Standardize structured logs with request/job correlation IDs.
3. Keep telemetry contracts backend-agnostic for operator choice.
4. Maintain low default resource overhead.

## Non-Goals (v1)

1. No mandatory OpenTelemetry Collector deployment.
2. No full distributed tracing storage/query stack rollout.
3. No frontend/browser telemetry in this slice.
4. No vendor-specific hardcoding in application telemetry contracts.

## Public Interfaces and Config

### API / Runtime Interfaces

1. Add `GET /metrics` (Prometheus text format).
2. Keep existing `/api/v1/*` endpoints unchanged.
3. Add response header `X-Request-Id` for API responses.

### Configuration Additions (Implemented)

1. `SIFT_OBSERVABILITY_ENABLED` (`true` default)
2. `SIFT_METRICS_ENABLED` (`true` default)
3. `SIFT_METRICS_PATH` (`/metrics` default)
4. `SIFT_LOG_LEVEL` (`INFO` default)
5. `SIFT_LOG_FORMAT` (`json` default)
6. `SIFT_LOG_REDACT_FIELDS` (sensible defaults including secrets/content fields)
7. `SIFT_REQUEST_ID_HEADER` (`X-Request-Id` default)

## Metrics Contract (v1)

### HTTP

1. `sift_http_requests_total{method,route,status_class}`
2. `sift_http_request_duration_seconds{method,route,status_class}`

### Scheduler

1. `sift_scheduler_loops_total{result}`
2. `sift_scheduler_loop_duration_seconds`
3. `sift_scheduler_due_feeds_total`
4. `sift_scheduler_enqueues_total{result}`
5. `sift_scheduler_enqueued_jobs_total`

### Queue and Worker

1. `sift_queue_depth{queue}`
2. `sift_queue_oldest_job_age_seconds{queue}`
3. `sift_worker_jobs_total{result}`
4. `sift_worker_job_duration_seconds{result}`

### Ingestion

1. `sift_ingest_runs_total{result}`
2. `sift_ingest_run_duration_seconds{result}`
3. `sift_ingest_entries_fetched_total`
4. `sift_ingest_entries_inserted_total`
5. `sift_ingest_entries_duplicate_total`
6. `sift_ingest_entries_filtered_total`
7. `sift_ingest_plugin_processed_total`

### Cardinality Rules

1. Do not include high-cardinality labels (`user_id`, `article_id`, URLs, free-form text).
2. Keep labels bounded to small static dimensions (`route`, `status_class`, `queue`, `result`).

## Logging Contract (v1)

### Structured JSON Fields

1. Required: `ts`, `level`, `service`, `env`, `event`, `message`
2. Correlation: `request_id`, `trace_id`, `span_id`
3. Contextual optional fields: `route`, `method`, `status_code`, `duration_ms`, `feed_id`, `job_id`, `queue_name`,
   `error_type`

### Required Event Catalog

1. API:
   - `api.request.start`
   - `api.request.complete`
   - `api.request.error`
2. Scheduler:
   - `scheduler.loop.start`
   - `scheduler.loop.complete`
   - `scheduler.enqueue.success`
   - `scheduler.enqueue.skip_due`
   - `scheduler.enqueue.skip_active_job`
   - `scheduler.enqueue.error`
3. Worker:
   - `worker.job.start`
   - `worker.job.complete`
   - `worker.job.error`
4. Ingestion:
   - `ingest.run.start`
   - `ingest.run.complete`
   - `ingest.run.error`

### Redaction Policy

1. Never log tokens, passwords, cookies, authorization headers, or session identifiers.
2. Never log full article body/payload by default.
3. Log operational metadata and counters only.

## Implementation Plan

### Phase 1: Logging Foundation

1. Add centralized structured logger setup shared by API, scheduler, and worker.
2. Replace scheduler/worker `print` diagnostics with structured log events.
3. Add request ID middleware for API request correlation and response header propagation.
4. Add ingestion start/complete/error structured event emission.

### Phase 2: Metrics Foundation

1. Add metrics registry and helper utilities.
2. Add `/metrics` endpoint export.
3. Instrument API request duration/count.
4. Instrument scheduler loop/enqueue outcomes and queue lag.
5. Instrument worker job outcomes and durations.
6. Instrument ingestion run outcomes and entry counters.

### Phase 3: Operator Documentation

1. Add observability runbook docs with metric dictionary and log event catalog.
2. Document VictoriaMetrics/VictoriaLogs compatibility and VMUI-first setup notes.
3. Document optional Grafana integration path as non-required.

## Implemented Checkpoint (2026-02-23)

1. Phase 1 completed:
   - centralized structured logger setup shared by API/scheduler/worker
   - scheduler/worker `print` diagnostics replaced with structured events
   - request-id middleware added with response header propagation
   - ingestion start/complete/error event emission implemented
2. Phase 2 completed:
   - metrics registry/helper implementation added
   - API `/metrics` endpoint export implemented
   - API request metrics instrumentation implemented
   - scheduler loop/enqueue + queue gauge instrumentation implemented
   - worker job outcome/duration instrumentation implemented
   - ingestion run/result + entry counter instrumentation implemented
   - scheduler and worker now expose dedicated scrape endpoints on configurable metrics ports
3. Phase 3 completed:
   - operator runbook added at `docs/observability-runbook.md`
   - VictoriaMetrics/VictoriaLogs setup notes included

## Test Cases and Scenarios

1. Redaction tests:
   - sensitive fields are excluded or masked in logs.
2. Metrics contract tests:
   - `/metrics` is reachable and includes expected metric names.
3. Scheduler metric tests:
   - enqueue success/failure/skip paths increment expected counters.
4. Worker metric tests:
   - job success/failure increments and durations are recorded.
5. Ingestion metric tests:
   - success/304/http error/network error paths map to correct `result` values.
6. Request ID tests:
   - inbound request ID pass-through and generated fallback behavior.
   - `X-Request-Id` response header presence.
7. Regression tests:
   - existing API behavior remains unchanged apart from additive observability surface.

## Assumptions and Defaults

1. Observability remains a standalone platform slice and is not merged into feed-health features.
2. Scope remains backend runtime only in v1.
3. No DB schema migration is required for v1 observability baseline.
4. Current priority order remains:
   - stream ranking first
   - scheduler/ingestion observability second

## Backlog References

- Product backlog: [docs/backlog.md](../../backlog.md)
- Related dashboard planning: [docs/specs/dashboard-command-center-v1.md](../dashboard-command-center-v1.md)
