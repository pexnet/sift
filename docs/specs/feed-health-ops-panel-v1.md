# Feed Health Ops Panel v1

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependency: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)

## Context

Sift exposes feed-level operational fields (`last_fetched_at`, `last_fetch_error`) but does not yet provide an
aggregated health panel suitable for dashboard triage.

## Goal

Define a compact feed operations health model for dashboard command-center visibility.

## Non-Goals (v1)

1. No full infra observability suite replacement.
2. No distributed tracing requirement.
3. No deep per-feed history UI in dashboard card v1.

## Health Signals (v1)

1. `stale_feed_count`:
   - feeds whose fetch freshness is older than stale threshold.
2. `error_feed_count`:
   - feeds with non-empty `last_fetch_error`.
3. `oldest_success_age_hours`:
   - age of oldest successful fetch across active feeds.
4. `queue_lag_summary`:
   - ingest queue length
   - oldest queued job age (if available)
   - optional failed job count (24h window, if available)

### Stale Threshold Rule

A feed is stale when:

1. it is active, and
2. `last_fetched_at` is null, or
3. `now - last_fetched_at > max(6 hours, 4 * fetch_interval_minutes)`.

## API Surface (Planned)

1. `GET /api/v1/dashboard/cards/feed-health`
   - returns aggregate health payload + status metadata.
2. Optional follow-up endpoint for detail drill-down:
   - `GET /api/v1/feeds/health`
   - paginated feed-level health records.

## Response Shape (Card)

1. `status`: `ready` | `unavailable` | `degraded`
2. `reason`: nullable string
3. `dependency_spec`: path
4. `stale_feed_count`: int
5. `error_feed_count`: int
6. `oldest_success_age_hours`: number | null
7. `queue_lag`: object with `queue_length`, `oldest_job_age_seconds`, `failed_jobs_24h`
8. `last_updated_at`: timestamp

## Acceptance Criteria (for later implementation)

1. Dashboard health card returns deterministic aggregates for user-owned feeds.
2. Stale threshold logic is consistent and documented.
3. Queue lag fields degrade gracefully when queue telemetry is unavailable.
4. Health panel can be refreshed manually without affecting other cards.

## Test Plan (for later implementation)

1. Unit tests for stale threshold classification.
2. Service tests for aggregate calculations from feed fields.
3. Queue-lag adapter tests for unavailable/partial telemetry.
4. API tests for auth boundaries and payload contract.

## Rollout Notes

1. Start with aggregate-only card data.
2. Add deep per-feed health page in later deferred slice.
3. Keep health card resilient under partial telemetry.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Parent dashboard spec: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)
