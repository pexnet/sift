# Dashboard Command Center v1

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)
- Foundation dependency: [docs/specs/done/dashboard-shell-plugin-host-v1.md](done/dashboard-shell-plugin-host-v1.md)

## Context

Sift currently has a reader-first workspace at `/app` plus a baseline `/app/dashboard` shell with availability-only
card metadata. The full command-center data/card rollout remains unimplemented.

Users need a true command center that supports daily triage and prioritization decisions without replacing existing list
/ reader workflows.

## Goal

Deliver a dashboard planning blueprint that is implementation-ready once dependency specs are drafted and the shell host
slice is in place:

1. dedicated route at `/app/dashboard`,
2. left workspace chrome preserved (rail + navigation tree),
3. dashboard cards for priority, health, saved follow-up, monitoring signal, trends, and discovery candidates,
4. explicit card availability states for dependencies not yet implemented,
5. hybrid refresh model (light auto-refresh + manual per-card refresh).

## Non-Goals (v1)

1. No replacement of `/app` list/reader workflows.
2. No ML ranking model training in v1.
3. No hard dependency on unimplemented trend/discovery backend slices for initial dashboard shell.
4. No full plugin marketplace or plugin permission redesign.

## Route and Layout

1. Canonical route: `/app/dashboard`.
2. Preserve left workspace chrome:
   - rail actions
   - navigation tree
3. Replace current list/reader content area with a dashboard grid shell.
4. Dashboard rail action should navigate to `/app/dashboard` (instead of resetting `/app` scope).

## Card Set (v1 Blueprint)

1. Prioritized Queue card:
   - top unread items ranked by weighted heuristic.
2. Feed Ops Health card:
   - stale feeds, recent failures, ingest freshness, queue lag summary.
3. Saved Follow-up card:
   - latest saved/starred items + follow-up counts.
4. High-Value Monitoring card:
   - ranked monitoring streams based on recent signal score.
5. Trends card:
   - explicit unavailable state until trend dependency is implemented.
6. Discovery Candidates card:
   - feed recommendation candidate summary (from discovery stream workflow when available),
   - candidate discovery articles (monitoring-first article candidates).
7. Optional future cards/tabs:
   - alerts
   - follow-up queue details

## Card Availability Contract

Every card payload should include:

1. `status`: `ready` | `unavailable` | `degraded`
2. `reason`: nullable string
3. `dependency_spec`: nullable spec path
4. `last_updated_at`: timestamp

Dashboard shell must render unavailable cards deterministically and keep the rest of the dashboard usable.

## API Surface (Planned)

1. Summary endpoint:
   - `GET /api/v1/dashboard/summary`
   - purpose: lightweight counters + card availability flags.
2. Card data endpoints:
   - `GET /api/v1/dashboard/cards/prioritized-queue`
   - `GET /api/v1/dashboard/cards/feed-health`
   - `GET /api/v1/dashboard/cards/saved-followup`
   - `GET /api/v1/dashboard/cards/monitoring-signals`
   - `GET /api/v1/dashboard/cards/trends`
   - `GET /api/v1/dashboard/cards/discovery-candidates`
3. All endpoints remain user-scoped and auth-protected.
4. Existing `/api/v1/articles`, `/api/v1/navigation`, `/api/v1/feeds`, `/api/v1/health` remain unchanged.

## Refresh Model

1. Auto-refresh:
   - summary-level counters every 60-120 seconds.
2. Manual refresh:
   - each card exposes a refresh control.
3. Heavy cards should not use aggressive polling in v1.

## Dependency Gate (Required Before Build)

Dashboard implementation is blocked until these specs are drafted and linked:

1. [docs/specs/done/dashboard-shell-plugin-host-v1.md](done/dashboard-shell-plugin-host-v1.md)
2. [docs/specs/stream-ranking-prioritization-controls-v1.md](stream-ranking-prioritization-controls-v1.md)
3. [docs/specs/feed-health-ops-panel-v1.md](feed-health-ops-panel-v1.md)
4. [docs/specs/monitoring-signal-scoring-v1.md](monitoring-signal-scoring-v1.md)
5. [docs/specs/trends-detection-dashboard-v1.md](trends-detection-dashboard-v1.md)
6. [docs/specs/search-provider-plugin-v1.md](search-provider-plugin-v1.md)
7. [docs/specs/feed-recommendations-v1.md](feed-recommendations-v1.md)

## Frontend Plan (for later implementation)

1. Add route in router for `/app/dashboard`.
2. Reuse workspace shell and navigation context; render dashboard in content area.
3. Add dashboard feature module with card grid and card-level loading/error/unavailable states.
4. Add summary polling and per-card manual refresh actions.
5. Preserve keyboard and accessibility patterns used in workspace.

## Acceptance Criteria (for later implementation)

1. Dashboard loads at `/app/dashboard` while left rail + nav tree stay visible.
2. Core cards render with deterministic availability state handling.
3. Trend/dependency-unready cards render explicit unavailable state without breaking dashboard.
4. Summary auto-refresh and per-card manual refresh both work.
5. Data remains user-scoped and consistent with existing auth boundaries.

## Test Plan (for later implementation)

Frontend:

1. Route/layout tests for `/app/dashboard` shell composition.
2. Card rendering tests for `ready`, `unavailable`, and `degraded`.
3. Refresh tests (auto summary polling + manual card refresh).
4. Accessibility tests for card actions, labels, and keyboard focus flow.

Backend:

1. API auth boundary tests for all dashboard endpoints.
2. Summary payload contract tests (card availability metadata included).
3. Card endpoint tests for deterministic fallback/unavailable responses.

## Rollout Notes

1. Deliver dashboard in phased mode:
   - shell + ready cards first,
   - dependency-backed cards enabled as underlying features ship.
2. Keep `/app` workspace behavior unchanged.
3. Preserve compatibility with future `dashboard_card` plugin extension point.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related spec: [docs/specs/search-provider-plugin-v1.md](search-provider-plugin-v1.md)
- Related spec: [docs/specs/feed-recommendations-v1.md](feed-recommendations-v1.md)
