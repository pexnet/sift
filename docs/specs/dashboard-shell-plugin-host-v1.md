# Dashboard Shell and Plugin Card Host v1

## Status

- State: Planned
- Scope: Dashboard route/shell foundation + plugin-ready card host
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependencies:
  - [docs/specs/plugin-platform-foundation-v1.md](plugin-platform-foundation-v1.md)
  - [docs/specs/frontend-plugin-host-workspace-areas-v1.md](frontend-plugin-host-workspace-areas-v1.md)

## Context

`/app/dashboard` is planned but not implemented. The desktop rail `Dashboard` action currently resets workspace scope
instead of navigating to a dashboard route. Product direction now requires an early shell/host slice so later dashboard
cards can be added without reworking routing/layout.

## Goals

1. Implement canonical dashboard route at `/app/dashboard`.
2. Keep left workspace chrome (rail + nav tree) visible.
3. Add plugin-ready dashboard card host container with deterministic fallback states.
4. Preserve compatibility with full command-center card/data rollout spec.

## Non-Goals (v1)

1. No full dashboard card data rollout in this slice.
2. No ranking/feed-health/trends/discovery backend implementation in this slice.
3. No dashboard-specific prioritization controls UI in this slice.

## Route and Layout Contract (Planned)

1. Add route `/app/dashboard`.
2. Dashboard rail action navigates to `/app/dashboard` (not scope reset).
3. Reuse workspace shell and navigation pane.
4. Replace list/reader content area with dashboard grid host when on dashboard route.

## Card Host Contract (Planned)

1. Card mounts support statuses:
   - `ready`
   - `unavailable`
   - `degraded`
2. Host renders unavailable/degraded cards deterministically.
3. Card mount failures are isolated per card.
4. Host accepts both built-in and plugin-provided `dashboard_card` entries.

## API Surface (Planned)

Phase-1 summary API (lightweight):

1. `GET /api/v1/dashboard/summary`
   - includes card availability metadata only (status/reason/dependency)
   - no heavy card data payload requirements in this slice

Compatibility rule:

1. Keep response contract aligned with full dashboard command-center spec.

## Acceptance Criteria (for later implementation)

1. `/app/dashboard` route loads with rail + navigation tree visible.
2. Dashboard rail action navigates to `/app/dashboard`.
3. Dashboard host renders card slots with deterministic unavailable/degraded states.
4. Plugin card host integration point is wired and failure-isolated.
5. Existing `/app` list/reader behavior remains unchanged.

## Test Plan (for later implementation)

1. Router/layout tests for `/app/dashboard`.
2. Rail action navigation tests.
3. Card host rendering tests for `ready`/`unavailable`/`degraded`.
4. Error-boundary tests for per-card mount failures.
5. API tests for summary endpoint auth and response contract.

## Rollout Notes

1. Ship shell/host first, then layer full card/data features by dependency specs.
2. Keep this slice additive and low-risk to existing workspace flows.
3. Coordinate endpoint naming/contracts with `dashboard-command-center-v1` spec to avoid drift.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related specs:
  - [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)
  - [docs/specs/stream-ranking-prioritization-controls-v1.md](stream-ranking-prioritization-controls-v1.md)
