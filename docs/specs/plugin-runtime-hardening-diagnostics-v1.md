# Plugin Runtime Hardening and Diagnostics v1

## Status

- State: Planned
- Scope: Backend runtime isolation, diagnostics, and telemetry baseline
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependency: [docs/specs/plugin-platform-foundation-v1.md](plugin-platform-foundation-v1.md)

## Context

Current plugin dispatch is functional but minimal. Error isolation, timeout policy, and operator visibility are not
fully standardized for multi-capability plugin growth.

## Goals

1. Add per-plugin fault isolation across all plugin capability dispatch paths.
2. Add bounded execution behavior (timeouts and deterministic failure handling).
3. Add operator-facing plugin diagnostics/status API.
4. Add plugin-level telemetry contract (logs + metrics dimensions).

## Non-Goals (v1)

1. No distributed tracing backend rollout.
2. No dynamic runtime plugin enable/disable API.
3. No per-user plugin diagnostics visibility model (system-level diagnostics only).

## Runtime Hardening Contract

### Isolation

1. One failing plugin must not block other plugins for the same capability.
2. Plugin runtime exceptions are converted into structured failure events.
3. Capability dispatch returns partial-success outcomes when some plugins fail.

### Timeout and Guardrails

1. Configurable per-capability timeout ceilings.
2. Timeout hit -> mark plugin invocation failed with `timeout` reason.
3. Optional bounded payload-size guards for plugin inputs/outputs where applicable.

### Determinism

1. Registration/dispatch order is stable.
2. Error handling and status mapping are deterministic for same inputs.

## Diagnostics API (Planned)

Endpoint: `GET /api/v1/plugins/status`

Response includes:

1. plugin id
2. enabled flag
3. loaded flag
4. declared capabilities
5. startup validation status
6. last_error summary (nullable)
7. disabled/unavailable reason (nullable)
8. runtime counters summary (success/failure/timeouts by capability)
9. last_updated_at

Auth/scope:

1. Auth-protected.
2. Initial v1: admin-only access.

## Telemetry Contract (Planned)

### Metrics

1. `sift_plugin_invocations_total{plugin_id,capability,result}`
2. `sift_plugin_invocation_duration_seconds{plugin_id,capability,result}`
3. `sift_plugin_timeouts_total{plugin_id,capability}`
4. `sift_plugin_dispatch_failures_total{capability}`

### Logging

Structured event names:

1. `plugin.dispatch.start`
2. `plugin.dispatch.complete`
3. `plugin.dispatch.error`
4. `plugin.dispatch.timeout`
5. `plugin.registry.validation_error`

Required fields:

1. `plugin_id`
2. `capability`
3. `result`
4. `duration_ms`
5. `error_type` (if error)

## Configuration Additions (Planned)

1. `SIFT_PLUGIN_TIMEOUT_INGEST_MS`
2. `SIFT_PLUGIN_TIMEOUT_CLASSIFIER_MS`
3. `SIFT_PLUGIN_TIMEOUT_DISCOVERY_MS`
4. `SIFT_PLUGIN_TIMEOUT_SUMMARY_MS`
5. `SIFT_PLUGIN_DIAGNOSTICS_ENABLED`

## Acceptance Criteria (for later implementation)

1. Plugin failures/timeouts do not crash or stall whole capability dispatch.
2. Diagnostics endpoint returns accurate plugin load and runtime status.
3. Plugin invocation metrics/logs are emitted with bounded cardinality.
4. Existing ingest/classifier behavior remains functionally correct with added guards.

## Test Plan (for later implementation)

1. Unit tests for timeout/error mapping and isolated dispatch behavior.
2. API tests for diagnostics response shape and auth boundaries.
3. Metrics/logging contract tests for event/metric name presence.
4. Regression tests for existing ingestion and stream classifier flows.

## Rollout Notes

1. Deliver runtime hardening before discovery/summary/dashboard plugin feature slices.
2. Keep diagnostics API read-only in v1.
3. Align metrics naming with scheduler/ingestion observability conventions.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related specs:
  - [docs/specs/plugin-platform-foundation-v1.md](plugin-platform-foundation-v1.md)
  - [docs/specs/scheduler-ingestion-observability-v1.md](scheduler-ingestion-observability-v1.md)
