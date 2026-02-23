# Search Provider Plugin v1 (Standalone Provider Infrastructure)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Discovery recommendations and provider execution have been planned together, which makes implementation boundaries
unclear. This spec separates provider infrastructure from recommendation workflow so search adapters can be delivered as
shared backend capability.

This document is a planning artifact and does not change backend/frontend behavior yet.

## Goal

Deliver a standalone search-provider plugin foundation that can be reused by discovery and future search surfaces:

1. Add a dedicated `search_provider` plugin capability.
2. Support ordered provider fallback through centralized plugin config.
3. Enforce strict per-provider budgets, request spacing, and timeout limits.
4. Return ephemeral feed/blog discovery candidates through authenticated API endpoints.
5. Keep recommendation lifecycle concerns out of this slice.

## Non-Goals (v1)

1. No recommendation persistence model (`feed_recommendations`) in this spec.
2. No accept/deny/reset workflow in this spec.
3. No discovery stream CRUD in this spec.
4. No dashboard card implementation in this spec.
5. No frontend implementation requirement in this spec (backend-first scope).

## Planned Plugin Capability and Method Contract

1. Capability: `search_provider`
2. Method: `search_feeds(request)`
3. Behavior requirements:
   - ordered provider chain evaluation (first success returns results)
   - fallback to next provider on timeout/error/no-result according to policy
   - strict timeout guard per provider call
   - strict budget/rate enforcement before calls

## Provider Matrix (v1)

Default providers:

1. `searxng` (self-hosted first choice)
2. `brave_search` (managed API fallback/alternative)

Optional adapters (config-gated):

1. `google_custom_search` (legacy/free-tier constrained path)
2. `duckduckgo_instant_answer` (metadata/seed helper only, not primary SERP discovery)

Policy:

1. Retired/deprecated providers are excluded from the default matrix.
2. Unknown provider ids are rejected by config validation.

## Planned API Surface (Backend-First, Ephemeral Results)

1. `POST /api/v1/search/feeds`
   - on-demand search for feed/blog candidates
   - returns ephemeral results only (no persistent recommendation queue in v1)
2. `GET /api/v1/search/providers`
   - returns configured provider chain and effective budget/timeout metadata

## Configuration and Enforcement Contract

Primary source: plugin registry (`config/plugins.yaml`).

Planned settings under search-provider plugin:

1. `provider_chain`
2. `provider_budgets`
   - `max_requests_per_run`
   - `max_requests_per_day`
   - `min_interval_ms`
   - `max_query_variants_per_stream`
   - `max_results_per_query`
3. provider credentials and endpoint settings (env-ref based for sensitive values)

Enforcement requirements:

1. Budgets are enforced before outbound requests.
2. Daily/run caps are hard limits, not best-effort.
3. Timeout is enforced per adapter call.
4. Budget exhaustion returns explicit warning metadata and partial results when applicable.

## Integration with Discover Feeds

1. Discover-feeds workflow (`docs/specs/feed-recommendations-v1.md`) consumes `search_provider`.
2. Discovery stream generation compiles query/options and delegates provider execution to this capability.
3. Recommendation status lifecycle remains in discover-feeds spec and is out of scope here.

## Acceptance Criteria (for later implementation)

1. Plugin capability contract includes `search_provider` and `search_feeds(request)`.
2. Ordered fallback behavior is configurable and deterministic.
3. Default provider chain supports `searxng` then `brave_search`.
4. Optional adapters are disabled unless explicitly configured.
5. Provider budgets/timeouts are enforced strictly with explicit exhaustion/timeout reporting.
6. Planned search endpoints are documented as authenticated, backend-only contracts.
7. Discover-feeds planning references this spec for provider execution.

## Test Plan (for later implementation)

1. Registry validation tests for provider-chain allowlist and budget schema bounds.
2. Runtime tests for fallback ordering and short-circuit on first successful provider.
3. Timeout/failure isolation tests per provider adapter.
4. Budget enforcement tests for run/day caps and request spacing.
5. API contract tests for auth boundaries and response metadata shape.
6. Integration tests for discovery workflow consuming `search_provider` without provider-specific coupling.

## Rollout Notes

1. Implement as backend-first foundation before discovery recommendation persistence workflows.
2. Keep v1 output ephemeral to reduce migration and state-management risk.
3. Add UI consumers later after API and provider runtime are stable.
4. Maintain conservative default budgets for free-tier-safe operation.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Dependent workflow spec: [docs/specs/feed-recommendations-v1.md](feed-recommendations-v1.md)
