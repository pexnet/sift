# Monitoring Signal Scoring v1 (High-Value Streams + Candidate Articles)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependency: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)

## Context

Monitoring streams already capture match events and classifier runs, but there is no dashboard-oriented scoring model for
identifying high-value monitoring feeds/streams and surfacing candidate discovery articles.

## Goal

Define a deterministic monitoring signal score and produce:

1. ranked high-value monitoring streams,
2. monitoring-first candidate articles for dashboard discovery workflows.

## Non-Goals (v1)

1. No semantic/vector ranking dependency.
2. No external provider intelligence dependency.
3. No user-managed pinning model in v1.

## Signal Scoring Model

### Stream Score Formula

For each stream in a rolling window (default 24 hours):

`stream_signal_score = volume_component + confidence_component + unread_impact_component + recency_component`

Components:

1. `volume_component`:
   - normalized matched article count, `0..40`.
2. `confidence_component`:
   - classifier confidence median/average where available, `0..25`.
3. `unread_impact_component`:
   - unread matched count normalized, `0..25`.
4. `recency_component`:
   - freshness of last high-confidence match, `0..10`.

Tie-breaks:

1. higher score,
2. higher unread impact,
3. newer latest match timestamp,
4. stream name stable ordering.

## Candidate Discovery Articles (Monitoring-First v1)

1. Candidate set source:
   - monitoring-matched articles only.
2. Candidate rank basis:
   - parent stream signal score
   - article recency
   - classifier confidence when present
   - unread/saved state bonus
3. Purpose:
   - highlight likely high-value follow-up items directly from monitoring evidence.

## API Surface (Planned)

1. `GET /api/v1/dashboard/cards/monitoring-signals`
   - returns ranked stream list + score breakdown.
2. `GET /api/v1/dashboard/cards/discovery-candidates`
   - returns:
     - candidate feed recommendation summary (when discovery is implemented),
     - monitoring-first candidate articles payload.

## Response Contract Highlights

1. Card-level status metadata:
   - `status`, `reason`, `dependency_spec`, `last_updated_at`.
2. Stream rows include:
   - `stream_id`, `stream_name`, `signal_score`,
   - `matched_count_window`, `unread_count_window`,
   - `confidence_summary`, `latest_match_at`.
3. Candidate article rows include:
   - `article_id`, `title`, `canonical_url`, `published_at`,
   - `stream_id`, `stream_name`,
   - `candidate_score`, `why_candidate`.

## Acceptance Criteria (for later implementation)

1. Monitoring card ranks streams deterministically.
2. Candidate article list is monitoring-first and user-scoped.
3. Score breakdown is available for explainability/debugging.
4. Card remains functional when classifier confidence is absent for some matches.

## Test Plan (for later implementation)

1. Unit tests for score component normalization and tie-break order.
2. Integration tests for stream/article candidate ranking from seeded matches.
3. API tests for auth boundary and response contract stability.
4. Regression tests for streams with rules-only matching and no classifier runs.

## Rollout Notes

1. Start with one fixed rolling window default (24h) and optional 7d extension later.
2. Keep payload compact for dashboard latency budgets.
3. Add vector/trend candidate blending in later versions only.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Parent dashboard spec: [docs/specs/dashboard-command-center-v1.md](dashboard-command-center-v1.md)
