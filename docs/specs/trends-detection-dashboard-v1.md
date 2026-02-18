# Trends Detection for Dashboard v1

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependency: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)

## Context

Dashboard command-center design includes a trends card, but Sift has no dedicated trend-analysis pipeline or trend
snapshot storage yet.

## Goal

Define trend data contracts and readiness behavior so dashboard can safely include a trends card from day one with an
explicit unavailable state until the trend pipeline is implemented.

## Non-Goals (v1)

1. No ad-hoc temporary keyword-frequency hack in dashboard implementation.
2. No external NLP service requirement.
3. No replacement of existing monitoring signal flows.

## Dashboard Card Readiness Behavior

1. Before trend backend is ready:
   - trends card returns `status=unavailable`,
   - includes `reason` and `dependency_spec`.
2. After trend backend is ready:
   - trends card returns `status=ready` with trend topics and evidence.

## Trend Model (Planned)

### Inputs

1. Scoped article corpus (selected folders/feeds/system scope).
2. Rolling windows:
   - short window (for example 24h),
   - baseline window (for example prior 7d/14d).

### Outputs

1. Ranked trend topics/keyphrases.
2. Momentum signal:
   - short-window lift vs baseline.
3. Evidence summary:
   - supporting article count
   - source diversity count
   - representative article ids/links.

## Proposed Data Model

1. `trend_snapshots`
   - snapshot metadata per user/scope/window.
2. `trend_topics`
   - topic rows per snapshot with momentum/evidence fields.

## API Surface (Planned)

1. `GET /api/v1/dashboard/cards/trends`
   - always available as endpoint,
   - returns unavailable or ready payload based on dependency readiness.
2. Optional drill-down endpoint:
   - `GET /api/v1/trends/snapshots/{snapshot_id}`.

## Response Shape (Card)

1. `status`: `ready` | `unavailable` | `degraded`
2. `reason`: nullable string
3. `dependency_spec`: spec path
4. `window`: trend window metadata
5. `topics`: list of trend topic rows when ready
6. `last_updated_at`: timestamp

## Acceptance Criteria (for later implementation)

1. Trends card degrades gracefully to unavailable while backend is not implemented.
2. Ready-state payload includes explainable momentum and evidence fields.
3. Trend card behavior is deterministic for same snapshot.
4. Trend card stays user-scoped.

## Test Plan (for later implementation)

1. API tests for unavailable-state payload contract.
2. Trend computation tests for momentum math and topic ordering.
3. Scope filtering tests (folder/system boundaries).
4. Frontend rendering tests for unavailable vs ready states.

## Rollout Notes

1. Ship dashboard with explicit unavailable trends card first.
2. Enable ready-state trends only after trend pipeline + snapshot storage ships.
3. Keep trend card independent from monitoring-scoring card.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Parent dashboard spec: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)
