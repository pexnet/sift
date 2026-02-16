# Feed Recommendations v1 (Saved-Driven Discovery)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Sift already supports saving articles via `is_starred` (`Saved` scope). This spec defines a future feature that uses
those saved articles to discover related RSS/Atom feeds on the public internet and propose them to the user.

This document is a planning artifact and does not change backend/frontend behavior yet.

## Goal

Provide a practical recommendation workflow:

1. User triggers recommendation generation manually.
2. System analyzes saved articles as topic seeds.
3. A plugin-backed discovery provider finds candidate feeds.
4. User reviews candidates and explicitly accepts or denies each one.
5. Accepted candidates are added as feeds in Sift.

## Non-Goals (v1)

1. No automatic scheduled generation.
2. No separate `read later` state (Saved remains the source signal).
3. No automatic feed subscription without explicit user accept.
4. No ranking-model training pipeline.
5. No cross-user or global recommendation pool.

## User Flow (Planned)

1. Open workspace recommendations area (dedicated nav section).
2. Click `Generate recommendations`.
3. Review candidate rows/cards with feed title, URL, confidence, and evidence.
4. Choose:
   - `Accept`: add feed immediately.
   - `Deny`: mark recommendation as denied and remove from pending list.
5. Pending badge/count updates in workspace navigation.

## Proposed Data Model

Table: `feed_recommendations`

Proposed fields:

- `id` (UUID, primary key)
- `user_id` (UUID, required, indexed)
- `status` (`pending` | `accepted` | `denied`, indexed)
- `feed_url` (string, required)
- `feed_url_normalized` (string, required)
- `feed_title` (string, nullable)
- `site_url` (string, nullable)
- `confidence` (float, nullable)
- `provider` (string, required)
- `evidence_json` (text/json, nullable)
- `seed_article_ids_json` (text/json, nullable)
- `accepted_feed_id` (UUID, nullable, FK `feeds.id`)
- `decided_at` (timestamp, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Constraints and indexes:

1. Unique `(user_id, feed_url_normalized)`.
2. Index `(user_id, status, created_at)`.
3. Optional index on `accepted_feed_id`.

## Proposed API Endpoints

Base path: `/api/v1/recommendations/feeds`

1. `POST /generate`
   - Runs generation on demand for current user.
   - Collects saved article seeds.
   - Calls configured discovery plugin/provider.
   - Persists deduped `pending` recommendations.
   - Returns generation summary counts.

2. `GET /`
   - Lists recommendations.
   - Supports status filter and pagination.

3. `PATCH /{recommendation_id}`
   - Payload: `{ "decision": "accept" | "deny" }`
   - `accept`: creates feed immediately and links `accepted_feed_id`.
   - `deny`: updates status and decision timestamp.

4. `GET /summary`
   - Returns summary counters for workspace badge (for example, `pending_count`).

## Proposed Plugin Contract Additions

Add new discovery contract in plugin layer:

1. `FeedDiscoverySeed`
   - Seed article id/title/content and metadata fields.

2. `FeedDiscoveryCandidate`
   - Candidate feed URL/title/site URL/confidence/evidence/provider fields.

3. `discover_feeds(...)`
   - Plugin method to return candidates from provided seeds/options.

Provider strategy for v1:

- API-provider based web discovery (configured by env/settings), with strict request limits and timeouts.

## Workspace UI Placement (Planned)

1. Add a dedicated `Recommendations` area in workspace navigation.
2. Show pending recommendation badge/count.
3. Render a recommendations pane with:
   - Generate action
   - Candidate listing
   - `Accept` and `Deny` actions
4. Keep this separate from monitoring stream management UI.

## Acceptance Criteria (for later implementation)

1. User can generate recommendations manually from saved articles.
2. User can view pending candidates with evidence.
3. `Accept` adds a feed and updates recommendation status.
4. `Deny` updates recommendation status and removes it from pending views.
5. Workspace pending badge/count reflects current state.
6. Existing feed/monitoring/workspace flows remain unaffected.

## Test Plan (for later implementation)

Backend:

1. Unit tests for recommendation generation, URL normalization, dedupe, and conflict behavior.
2. API tests for auth boundaries, listing filters, pagination, and decision transitions.
3. Plugin tests for timeout/failure handling and candidate validation.

Frontend:

1. Workspace tests for nav entry, pending badge, and recommendations pane rendering.
2. Interaction tests for generate, accept, and deny actions.
3. Regression tests for existing workspace and monitoring routes.

## Rollout and Configuration Notes

1. Deliver behind explicit feature branch and config-driven provider settings.
2. If discovery provider config/key is missing, generation should fail with actionable user-facing error.
3. Keep generation manual-only in v1; scheduling can be a deferred follow-up.

## Backlog References

- Primary backlog item index: [docs/backlog.md](../backlog.md)
- Linked spec entry target: `Next (Prioritized) -> Linked Specifications`
