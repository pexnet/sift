# Discover Feeds v1 (Discovery Streams)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

This spec defines a discovery workflow where users configure dedicated `Discovery streams` and run feed discovery
manually per stream. Discovery streams are separate from monitoring streams and are not seeded from saved/starred
articles in v1.

This document is a planning artifact and does not change backend/frontend behavior yet.

## Goal

Provide a practical discovery workflow:

1. User manages one or more discovery streams.
2. User triggers generation manually for a selected discovery stream.
3. A plugin-backed discovery provider finds candidate feeds from stream query/options.
4. User reviews candidates and explicitly accepts or denies each one.
5. Accepted candidates are added as feeds in Sift.

## Non-Goals (v1)

1. No automatic scheduled generation.
2. No saved/starred article signal blending.
3. No automatic feed subscription without explicit user accept.
4. No ranking-model training pipeline.
5. No cross-user or global recommendation pool.
6. No direct reuse of monitoring stream records for discovery execution.

## User Flow (Planned)

1. Open `/account/discovery` and create/update discovery streams.
2. Optional convenience action: copy query/keyword criteria from a monitoring stream into a discovery stream.
3. Open workspace `Discover feeds` area and run generation for a selected discovery stream.
4. Review candidate rows/cards with feed title, URL, confidence, source-stream chips, and evidence.
5. Choose:
   - `Accept`: add feed immediately.
   - `Deny`: mark recommendation as denied and suppress resurfacing until manual reset.
6. Pending badge/count updates in workspace navigation.

## Proposed Data Model

Table: `discovery_streams`

Proposed fields:

- `id` (UUID, primary key)
- `user_id` (UUID, required, indexed)
- `name` (string, required)
- `description` (string, nullable)
- `is_active` (boolean, indexed)
- `priority` (integer, indexed)
- `match_query` (text, nullable)
- `include_keywords_json` (text/json, default `[]`)
- `exclude_keywords_json` (text/json, default `[]`)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Constraints and indexes:

1. Unique `(user_id, name)`.
2. Index `(user_id, is_active, priority)`.

Table: `feed_recommendations`

Proposed fields:

- `id` (UUID, primary key)
- `user_id` (UUID, required, indexed)
- `status` (`pending` | `accepted` | `denied` | `resolved_existing`, indexed)
- `feed_url` (string, required)
- `feed_url_normalized` (string, required)
- `feed_title` (string, nullable)
- `site_url` (string, nullable)
- `confidence` (float, nullable)
- `provider` (string, required)
- `evidence_json` (text/json, nullable)
- `accepted_feed_id` (UUID, nullable, FK `feeds.id`)
- `decided_at` (timestamp, nullable)
- `last_seen_at` (timestamp, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Constraints and indexes:

1. Unique `(user_id, feed_url_normalized)`.
2. Index `(user_id, status, created_at)`.
3. Optional index on `accepted_feed_id`.

Table: `feed_recommendation_sources`

Proposed fields:

- `id` (UUID, primary key)
- `recommendation_id` (UUID, required, FK `feed_recommendations.id`)
- `discovery_stream_id` (UUID, required, FK `discovery_streams.id`)
- `provider_confidence` (float, nullable)
- `evidence_json` (text/json, nullable)
- `created_at` (timestamp)

Constraints and indexes:

1. Unique `(recommendation_id, discovery_stream_id)`.
2. Index `(discovery_stream_id, created_at)`.

## Proposed API Endpoints

Base path: `/api/v1/discovery`

1. Discovery stream management:
   - `GET /streams`
   - `POST /streams`
   - `PATCH /streams/{stream_id}`
   - `DELETE /streams/{stream_id}`

2. Stream generation:
   - `POST /streams/{stream_id}/generate`
   - Runs generation on demand for one discovery stream.
   - Builds provider query/options from `match_query` + keyword criteria.
   - Calls configured discovery plugin/provider.
   - Upserts deduped recommendations by normalized URL.
   - Stores source attribution rows in `feed_recommendation_sources`.
   - Returns generation summary counts.

3. Recommendation listing:
   - `GET /recommendations`
   - Supports status filter and pagination.

4. Recommendation decision:
   - `PATCH /recommendations/{recommendation_id}`
   - Payload: `{ "decision": "accept" | "deny" }`
   - `accept`: creates feed immediately and links `accepted_feed_id`, sets status `accepted`.
   - `deny`: sets status `denied` and suppresses resurfacing until manual reset.

5. Recommendation reset:
   - `POST /recommendations/{recommendation_id}/reset`
   - Allows previously denied recommendation to be reconsidered.

6. Recommendation summary:
   - `GET /recommendations/summary`
   - Returns summary counters for workspace badge (for example, `pending_count`).

7. Existing feed auto-resolution rule:
   - If a discovered URL is already subscribed by the user, recommendation is recorded as `resolved_existing` and not
     surfaced as pending work.

## Public API / Type Additions

1. Discovery stream schemas:
   - `DiscoveryStreamCreate`
   - `DiscoveryStreamUpdate`
   - `DiscoveryStreamOut`
2. Recommendation schemas:
   - `FeedRecommendationOut` with status including `resolved_existing`
   - `FeedRecommendationSourceOut` for contributing stream attribution
3. Aggregation behavior:
   - One candidate recommendation may map to many source discovery streams.

## Proposed Plugin Contract Additions

Add new discovery contract in plugin layer:

1. `FeedDiscoverySeed`
   - Discovery stream seed payload from query/options:
     - stream id/name
     - `match_query`
     - include/exclude keyword lists
     - provider options

2. `FeedDiscoveryCandidate`
   - Candidate feed URL/title/site URL/confidence/evidence/provider fields.

3. `discover_feeds(...)`
   - Plugin method to return candidates from provided query/options seed.

Provider strategy for v1:

1. Support an ordered provider chain via plugin config (first provider succeeds, then fallback).
2. Recommended default provider set:
   - `searxng` (self-hosted first choice).
   - `brave_search` (managed API fallback/alternative).
3. Optional provider adapters (config-gated):
   - `google_custom_search` (legacy/free-tier constrained path).
   - `duckduckgo_instant_answer` (metadata/seed helper only, not primary SERP discovery).
4. Exclude retired/deprecated providers from the default matrix.
5. All provider adapters must enforce strict request limits and timeouts.

## Discovery Execution Flow (Planned)

1. Compile provider query variants from discovery stream inputs:
   - `match_query`
   - include/exclude keywords
   - optional language/source hints
2. Execute provider search with per-run request budgets and timeout limits.
3. For each result URL, resolve feed candidates using staged extraction:
   - direct feed URL parse (RSS/Atom/XML)
   - HTML autodiscovery link extraction (`rel="alternate"` with feed MIME types)
   - constrained heuristic fallback paths (`/feed`, `/rss`, `/atom.xml`, etc.)
4. Validate discovered feed endpoints with existing ingestion parser before recommendation persistence.
5. Normalize and dedupe recommendations by `(user_id, feed_url_normalized)`.
6. Preserve source attribution per contributing discovery stream in `feed_recommendation_sources`.
7. Auto-mark already subscribed feeds as `resolved_existing` and exclude them from pending decision work.

## Rate Limiting and Free-Tier Budget Controls (Planned)

1. Introduce config-driven provider budgets in discovery plugin settings:
   - `max_requests_per_run`
   - `max_requests_per_day`
   - `min_interval_ms`
   - `max_query_variants_per_stream`
   - `max_results_per_query`
2. Use conservative defaults so discovery stays within free-tier limits by default.
3. Enforce limits before external calls; do not "best effort" beyond configured budgets.
4. If a budget is exhausted mid-generation, return partial results with explicit budget warning metadata.
5. Keep counters provider-scoped so one provider hitting limits does not block other configured providers.

## Workspace UI Placement (Planned)

1. Add a dedicated `Discover feeds` area in workspace navigation.
2. Show pending recommendation badge/count.
3. Render a discovery pane with:
   - Generate action for selected discovery stream
   - Candidate listing
   - Source discovery-stream chips
   - `Accept`, `Deny`, and reset actions
4. Keep this separate from monitoring stream management UI and data model.

## Acceptance Criteria (for later implementation)

1. User can manage discovery streams without modifying monitoring stream records.
2. User can generate feed discovery manually per discovery stream.
3. User can view pending candidates with source attribution and evidence.
4. `Accept` adds a feed and updates recommendation status.
5. `Deny` updates recommendation status and suppresses resurfacing until manual reset.
6. Existing subscribed feeds are auto-marked `resolved_existing` and excluded from pending decisions.
7. Workspace pending badge/count reflects current state.
8. Existing feed/monitoring/workspace flows remain unaffected.
9. Generation respects provider request budgets/rate limits and reports partial-result budget exhaustion clearly.

## Test Plan (for later implementation)

Backend:

1. Unit tests for stream query compilation, URL normalization, cross-stream dedupe, and conflict behavior.
2. API tests for auth boundaries, stream CRUD, listing filters/pagination, and decision transitions.
3. Decision rule tests for denied suppression, manual reset, and `resolved_existing`.
4. Plugin tests for timeout/failure handling and candidate validation.
5. Provider budget/rate-limit tests for per-run and daily caps with partial-result warning behavior.

Frontend:

1. Workspace tests for `Discover feeds` nav entry, pending badge, and candidate pane rendering.
2. Interaction tests for per-stream generate, accept, deny, and reset actions.
3. Account tests for discovery stream CRUD and copy-from-monitoring convenience action.
4. Regression tests for existing workspace and monitoring routes.

## Rollout and Configuration Notes

1. Deliver behind explicit feature branch and config-driven provider settings.
2. If discovery provider config/key is missing, generation should fail with actionable user-facing error.
3. Keep generation manual-only in v1; scheduling can be a deferred follow-up.
4. Keep discovery-stream and monitoring-stream storage/execution separate; share only optional copy convenience.
5. Default rollout profile should favor free-tier-safe request budgets; operators can opt into higher limits.

## Backlog References

- Primary backlog item index: [docs/backlog.md](../backlog.md)
- Linked spec entry target: `Next (Prioritized) -> Linked Specifications`
