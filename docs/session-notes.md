# Session Notes

This file is a rolling recent execution log for fast session startup.
Historical notes are archived by month under `docs/session-notes/archive/`.

## 2026-03-01 (Planning-Doc Consistency Cleanup Pass)

### Implemented This Session

- Ran a planning-source consistency pass across:
  - `docs/backlog.md`
  - `docs/current-state.md`
  - `docs/architecture.md`
  - `docs/specs/feed-recommendations-v1.md`
  - `docs/specs/plugin-ui-organization-v1.md`
  - `docs/session-notes.md`
- Cleaned active backlog status so completed search-provider v1 is no longer listed as active `Next` work.
- Updated stale discovery status references (current-state and spec) to reflect implemented slices 1-4.
- Updated architecture route list to include implemented discovery settings route (`/account/discovery`).
- Enforced rolling-window policy in session notes and archived older 2026-03 entries to:
  - `docs/session-notes/archive/2026-03.md`

### Verification

- `rg -n "Core Platform Priorities|Search provider plugin v1 is completed and archived|Stream-Level Ranking" docs/backlog.md`
- `rg -n "slices 1-4 implemented|recommendation workflow hardening|discovery frontend wiring" docs/current-state.md`
- `rg -n "/account/discovery|Frontend owns routes" docs/architecture.md`
- `rg -n "Implemented slices|Remaining scope|tracks remaining closeout scope" docs/specs/feed-recommendations-v1.md`
- `rg -n "State: In progress|Baseline implementation is complete" docs/specs/plugin-ui-organization-v1.md`
- `rg -n "^## " docs/session-notes.md`

## 2026-03-01 (Discover Feeds v1 Slice 4: Frontend Coverage for Discovery Route + Workbench)

### Implemented This Session

- Added dedicated discovery frontend tests:
  - `DiscoveryWorkbench` interaction coverage for:
    - stream creation payload mapping,
    - stream edit/update + generation action,
    - recommendation decision actions (`accept`/`deny`) and `reset`,
    - recommendation filter propagation (`q`, status) into hook query filters.
  - `DiscoveryStreamsPage` route/page coverage to assert:
    - settings page scaffold renders expected title/description,
    - workbench mounts in `settings` mode.
- Preserved existing workspace/plugin discovery tests and kept new coverage isolated with discovery-hook mocks.

### Verification

- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run test -- src/features/discovery/components/DiscoveryWorkbench.test.tsx src/features/discovery/routes/DiscoveryStreamsPage.test.tsx`

## 2026-03-01 (Discover Feeds v1 Slice 3: Recommendation Listing Hardening + Endpoint Validation + Frontend Wiring)

### Implemented This Session

- Hardened recommendation listing/query behavior:
  - added `q` text filtering over recommendation title/url fields,
  - added `sort_by`/`sort_direction` controls on recommendations API,
  - added stricter decision transition rules (`accept`/`deny` only from `pending`, reset from `denied`).
- Added feed-endpoint validation before recommendation persistence:
  - candidate endpoint expansion (`/feed`, `/rss`, `/atom.xml`, `/feed.xml`),
  - HTML autodiscovery (`<link rel="alternate" ...>`),
  - feed payload parse validation and warning propagation for invalid/unresolvable candidates.
- Completed initial frontend discovery wiring:
  - new discovery API client + React Query hooks,
  - `DiscoveryWorkbench` UI for stream CRUD, generation, filtering, and recommendation decisions/reset,
  - new settings route `/account/discovery`,
  - plugin area host integration so discovery can render from plugin workspace area,
  - workspace plugin-nav pending badge wiring from recommendation summary (`discover_feeds` pending count).
- Updated tests:
  - backend discovery service/API coverage for transitions and recommendation list filtering/sorting,
  - workspace test updates for plugin-area host wiring/mocks.

### Verification

- `python -m ruff check src/sift/services/discovery_service.py src/sift/api/routes/discovery.py tests/test_discovery_service.py tests/test_discovery_api.py`
- `python -m mypy src/sift/services/discovery_service.py src/sift/api/routes/discovery.py tests/test_discovery_service.py tests/test_discovery_api.py --no-incremental`
- `python -m pytest tests/test_discovery_service.py tests/test_discovery_api.py`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- `npm --prefix frontend run test -- src/features/workspace/components/NavigationPane.test.tsx src/features/workspace/routes/WorkspacePage.test.tsx`

## 2026-03-01 (Discover Feeds v1 Slice 2: Recommendation Persistence + Decisions API)

### Implemented This Session

- Added discovery recommendation persistence model and source attribution:
  - `feed_recommendations`
  - `feed_recommendation_sources`
  - Alembic migration: `20260301_0019_feed_recommendations.py`
- Extended discovery generation behavior:
  - generation now upserts deduped recommendations by normalized URL,
  - source attribution rows are upserted per `(recommendation_id, discovery_stream_id)`,
  - existing user feed URLs are auto-marked `resolved_existing`.
- Added recommendation lifecycle APIs:
  - `GET /api/v1/discovery/recommendations`
  - `PATCH /api/v1/discovery/recommendations/{recommendation_id}` (`accept` / `deny`)
  - `POST /api/v1/discovery/recommendations/{recommendation_id}/reset`
  - `GET /api/v1/discovery/recommendations/summary`
- Added decision behavior:
  - `accept` creates feed for pending recommendations and links `accepted_feed_id`,
  - `deny` suppresses resurfacing until reset,
  - global-feed-URL conflict during accept resolves to `resolved_existing` when the feed already belongs to the user;
    otherwise returns actionable validation error.
- Added/updated tests:
  - `tests/test_discovery_service.py`
  - `tests/test_discovery_api.py`

### Verification

- `python -m ruff check src/sift/db/models.py alembic/versions/20260301_0019_feed_recommendations.py src/sift/domain/schemas.py src/sift/services/discovery_service.py src/sift/api/routes/discovery.py tests/test_discovery_service.py tests/test_discovery_api.py`
- `python -m mypy src/sift/services/discovery_service.py src/sift/api/routes/discovery.py src/sift/domain/schemas.py src/sift/db/models.py tests/test_discovery_service.py tests/test_discovery_api.py --no-incremental`
- `python -m pytest tests/test_discovery_service.py tests/test_discovery_api.py tests/test_search_api.py`

## 2026-03-01 (Discover Feeds v1 Slice 1: Discovery Streams + Manual Generation API)

### Implemented This Session

- Added discovery-stream persistence and migration:
  - SQLAlchemy model: `discovery_streams`
  - Alembic migration: `20260301_0018_discovery_streams.py`
- Added discovery-stream service and API baseline:
  - `GET /api/v1/discovery/streams`
  - `POST /api/v1/discovery/streams`
  - `PATCH /api/v1/discovery/streams/{stream_id}`
  - `DELETE /api/v1/discovery/streams/{stream_id}`
  - `POST /api/v1/discovery/streams/{stream_id}/generate`
- Generation behavior (slice 1):
  - compiles bounded query variants from `match_query` + include/exclude keywords,
  - resolves active search-provider runtime config from plugin-manager registry snapshot,
  - delegates provider execution to shared search-provider fallback/budget runtime,
  - returns deduped ephemeral candidates with warning details (no recommendation persistence yet).
- Added tests:
  - service tests (`tests/test_discovery_service.py`)
  - API tests (`tests/test_discovery_api.py`)

### Verification

- `python -m ruff check src/sift/api/router.py src/sift/api/routes/discovery.py src/sift/db/models.py src/sift/domain/schemas.py src/sift/services/discovery_service.py tests/test_discovery_api.py tests/test_discovery_service.py alembic/versions/20260301_0018_discovery_streams.py`
- `python -m mypy src/sift/api/routes/discovery.py src/sift/services/discovery_service.py src/sift/domain/schemas.py src/sift/db/models.py tests/test_discovery_api.py tests/test_discovery_service.py --no-incremental`
- `python -m pytest tests/test_discovery_service.py tests/test_discovery_api.py tests/test_search_api.py`

## Rolling Window Policy

- Keep only the most recent 3-5 session entries in this file.
- Move older entries to monthly archives in `docs/session-notes/archive/`.
- Keep each entry concise and link specs/docs rather than repeating large histories.
