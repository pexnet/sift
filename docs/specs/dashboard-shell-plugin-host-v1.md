# Dashboard Shell and Plugin Card Host v1

## Status

- State: In Progress
- Scope: Dashboard route/shell + summary metadata endpoint + card host baseline implemented
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

## Implemented Checkpoint (2026-02-22)

1. Added canonical dashboard route:
   - `/app/dashboard` implemented in frontend router
2. Updated dashboard rail behavior:
   - `Dashboard` rail action now navigates to `/app/dashboard`
3. Preserved workspace shell layout:
   - left rail + navigation tree remain visible in dashboard view
   - list/reader panes are replaced by dashboard host content area
4. Added plugin-ready dashboard host baseline:
   - deterministic card availability rendering (`ready`/`unavailable`/`degraded`)
   - per-card failure isolation via card-level error boundaries
   - registry seam for built-in and plugin-provided `dashboard_card` entries
5. Added dashboard summary metadata API:
   - `GET /api/v1/dashboard/summary`
   - returns card availability metadata only (`status`, `reason`, `dependency_spec`, `last_updated_at`)

## Route and Layout Contract

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

## API Surface

Phase-1 summary API (lightweight):

1. `GET /api/v1/dashboard/summary`
   - implemented: includes card availability metadata only (status/reason/dependency)
   - no heavy card data payload requirements in this slice

Compatibility rule:

1. Keep response contract aligned with full dashboard command-center spec.

## Acceptance Criteria

1. [x] `/app/dashboard` route loads with rail + navigation tree visible.
2. [x] Dashboard rail action navigates to `/app/dashboard`.
3. [x] Dashboard host renders card slots with deterministic unavailable/degraded states.
4. [x] Plugin card host integration point is wired and failure-isolated.
5. [x] Existing `/app` list/reader behavior remains unchanged.

## Test Plan

1. [x] Router/layout behavior tests for dashboard mode in workspace shell.
2. [x] Rail action navigation tests.
3. [x] Card host rendering tests for `ready`/`unavailable`/`degraded`.
4. [ ] Error-boundary tests for per-card mount failures.
5. [x] API tests for summary endpoint auth and response contract.

## Rollout Notes

1. Ship shell/host first, then layer full card/data features by dependency specs.
2. Keep this slice additive and low-risk to existing workspace flows.
3. Coordinate endpoint naming/contracts with `dashboard-command-center-v1` spec to avoid drift.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related specs:
  - [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)
  - [docs/specs/stream-ranking-prioritization-controls-v1.md](stream-ranking-prioritization-controls-v1.md)
