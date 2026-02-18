# Stream Ranking and Prioritization Controls v1

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependency: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)

## Context

Sift currently supports stream/feed priority fields in data models, but there is no dashboard-ready prioritization model
that consistently ranks cross-source article candidates for command-center triage.

## Goal

Define a deterministic weighted heuristic model and controls for ranking top unread items in dashboard v1.

## Non-Goals (v1)

1. No machine-learning ranking model.
2. No personalized model training.
3. No cross-user/global scoring.

## Prioritization Model

### Score Formula

Compute `priority_score` per candidate article:

`priority_score = source_weight + recency_score + unread_bonus + saved_bonus + monitoring_signal_bonus + confidence_bonus`

Field definitions:

1. `source_weight`:
   - configured by user for source classes (`feed`, `monitoring_stream`, future scopes),
   - range: `0..100`.
2. `recency_score`:
   - based on hours since publish/create,
   - decay from `40` down toward `0` over configured horizon.
3. `unread_bonus`:
   - fixed `+20` for unread.
4. `saved_bonus`:
   - fixed `+15` for saved/starred.
5. `monitoring_signal_bonus`:
   - from monitoring signal score dependency (`0..40` normalized).
6. `confidence_bonus`:
   - classifier confidence-driven, `0..15` normalized when available.

Tie-breaks (in order):

1. Higher `priority_score`.
2. More recent publish timestamp.
3. Higher monitoring signal bonus.
4. Stable id order for deterministic pagination.

## User Controls

1. User-editable source weights in dashboard settings section.
2. Optional recency horizon control (for example 6h, 24h, 72h decay windows).
3. Reset-to-default controls for prioritization settings.

## Proposed Data Model

Table: `user_prioritization_profiles`

Proposed fields:

- `id` (UUID, primary key)
- `user_id` (UUID, unique, indexed)
- `source_weights_json` (json/text; validated map)
- `recency_horizon_hours` (int)
- `created_at` (timestamp)
- `updated_at` (timestamp)

## API Surface (Planned)

1. `GET /api/v1/dashboard/prioritization-profile`
2. `PATCH /api/v1/dashboard/prioritization-profile`
3. Ranked queue consumption endpoint:
   - `GET /api/v1/dashboard/cards/prioritized-queue`
   - supports pagination and optional scope filters.

## Acceptance Criteria (for later implementation)

1. Ranking output is deterministic and reproducible for same input snapshot.
2. User weight changes affect ranking order without requiring service restart.
3. Defaults exist for users without custom profiles.
4. Queue output remains user-scoped and auth-protected.

## Test Plan (for later implementation)

1. Unit tests for score math and tie-break determinism.
2. API tests for profile CRUD and validation.
3. Integration tests for queue ranking changes after profile updates.
4. Regression tests for pagination stability.

## Rollout Notes

1. Start with one default profile per user.
2. Keep formula explicit and explainable in API payload metadata.
3. Revisit with ML only after heuristic model stabilizes.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Parent dashboard spec: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)
