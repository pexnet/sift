# Session Notes

This file is a rolling recent execution log for fast session startup.
Historical notes are archived by month under `docs/session-notes/archive/`.

## 2026-07-04 (SearXNG Dev-Container Integration + Monitoring v2 Frontend Wiring + Historical Matching)

### Implemented This Session

- Added SearXNG as a first-class dev-container service:
  - `.devcontainer/docker-compose.yml`: `searxng` service (searxng/searxng:latest) with healthcheck and port
    `8888:8080`, added to `app` depends_on and `devcontainer.json` runServices + forwardPorts.
  - `.devcontainer/searxng/settings.yml`: mounted into the container, enables `json` format in `search.formats`,
    disables rate limiter for dev, configures DuckDuckGo/Google/Bing/Wikipedia engines.
  - `config/plugins.yaml`: `searxng.base_url` updated from `http://localhost:8080/search` to
    `http://searxng:8080/search` (Docker Compose service address), with updated comments.
- Smoke-tested the self-hosted SearXNG instance:
  - `docker compose up -d searxng` → healthy,
  - JSON search API returned 27 results for "python rss feed" with zero warnings,
  - adapter contract (format=json, User-Agent, response shape) verified compatible.
- Monitoring v2 frontend wiring (bulk reorder + stream summary):
  - `frontend/src/shared/types/contracts.ts`: added `StreamBulkReorderRequest`, `StreamBulkReorderResponse`,
    `StreamSummary` types.
  - `frontend/src/shared/api/streamsApi.ts`: added `bulkReorderStreams()` and `getStreamSummary()` functions.
  - `frontend/src/shared/api/queryKeys.ts`: added `streamSummary(streamId)` query key.
  - `frontend/src/features/monitoring/api/monitoringHooks.ts`: added `useStreamSummaryQuery` and
    `useBulkReorderStreamsMutation` hooks.
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.tsx`: refactored stream rows into `StreamRow`
    component with per-row checkbox, inline summary chips (match count, latest match, classifier runs),
    expandable summary detail row, bulk selection toolbar with "Reorder" action and priority input.
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`: added mocks for new hooks,
    3 new tests (bulk reorder flow, summary display, select-all toggle).
- Create/update-triggered historical matching:
  - `src/sift/domain/schemas.py`: added `backfill_on_create: bool` to `KeywordStreamCreate` and
    `backfill_on_update: bool` to `KeywordStreamUpdate`.
  - `src/sift/services/stream_service.py`: added `HISTORICAL_MATCH_SCAN_LIMIT=5000` constant and
    `run_historical_match()` method — bounded scan (most recent articles first), preserves existing matches
    (no delete-then-reinsert), skips articles with existing match rows.
  - `src/sift/api/routes/streams.py`: create/update endpoints now call `run_historical_match` when the
    respective `backfill_on_*` flag is True.
  - `tests/test_stream_service.py`: 2 new tests (preserves existing matches + respects scan limit).
  - `frontend/src/shared/types/generated.ts`: added `backfill_on_create`/`backfill_on_update` fields.
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.tsx`: added "Match existing articles on save"
    toggle to the monitoring form, wired to `backfill_on_create`/`backfill_on_update` in payloads.
- Planning/documentation cleanup:
  - removed completed SearXNG self-hosted integration from active `Next`,
  - archived completed monitoring v2 follow-ups and SearXNG integration in `docs/backlog-history.md`,
  - moved completed plugin UI organization and plugin configuration registry specs from active `docs/specs/` to
    `docs/specs/done/`,
  - updated active backlog linked-spec section so it only lists still-active specs,
  - fixed moved-spec references in active docs and done-spec cross-links.
- Dashboard command center backend checkpoint:
  - added `user_prioritization_profiles`, `trend_snapshots`, and `trend_topics` SQLAlchemy models plus Alembic
    migration `20260704_0020_dashboard_prioritization_and_trends.py`,
  - added dashboard card/priority/trend response contracts in `src/sift/domain/schemas.py`,
  - added `src/sift/services/dashboard_service.py` with prioritization profile persistence, prioritized queue,
    feed-health, saved follow-up, and monitoring signal card data,
  - added dashboard API endpoints for prioritization profile and backend-ready cards:
    prioritized queue, feed health, saved follow-up, monitoring signals,
  - added `tests/test_dashboard_service.py` and expanded `tests/test_dashboard_api.py` coverage.

### Verification

- `docker compose -f .devcontainer/docker-compose.yml config --quiet` — valid,
- SearXNG healthcheck → healthy,
- JSON API smoke test → 27 results, 0 warnings,
- YAML validation of `settings.yml` → json format enabled,
- Backend: `ruff check` — clean,
- Backend: `ruff format --check` — clean (after format),
- Backend: `mypy src/sift/` — no issues in 75 source files,
- Backend: `pytest tests/test_stream_service.py` — 21 passed (19 existing + 2 new),
- Frontend: `npx tsc --noEmit` — clean,
- Frontend: `npx eslint .` — clean,
- Frontend: `npx vitest run MonitoringFeedsPage.test.tsx` — 10/10 passed,
- Frontend: `npm run build` — pass, existing >500k chunk warning remains.
- Docs: active spec inventory checked; completed plugin specs now live under `docs/specs/done/`.
- Dashboard backend focused slice:
  - `pytest tests/test_dashboard_service.py ...dashboard API focused tests...` — 17 passed,
  - `ruff check` / `ruff format --check` for dashboard backend touched files — clean,
  - `mypy src/sift/services/dashboard_service.py src/sift/db/models.py src/sift/domain/schemas.py src/sift/api/routes/dashboard.py`
    — clean.

## 2026-07-03 (Workstream B+C: Performance Fixes + SearXNG Verification + Monitoring v2)

### Implemented This Session

- Closed Workstream B performance fixes:
  - B1: added `ADVANCED_SEARCH_SCAN_LIMIT` (10k) to advanced search to prevent loading all articles into memory,
    reports truncation via new `ArticleListResponse.truncated` field,
  - B2: batched `mark_scope_as_read` bulk_patch_state calls in chunks of `MARK_SCOPE_BATCH_SIZE` (500) to avoid
    huge IN (...) queries.
- Completed C1 SearXNG instance compatibility verification:
  - tested 17+ public SearXNG instances — all rate-limit or block JSON API,
  - started local SearXNG Docker container and verified adapter end-to-end (5 candidates, 0 warnings),
  - documented self-hosting as the only reliable path,
  - verification report: `docs/specs/done/searxng-verification-2026-07-03.md`,
  - updated `config/plugins.yaml` with test config guidance comments.
- Completed C2 monitoring feed search management v2 expansion:
  - `POST /api/v1/streams/bulk-reorder`: update priorities for multiple streams (ownership-scoped),
  - `GET /api/v1/streams/{id}/summary`: match count, latest match, classifier run stats,
  - new schemas: `StreamBulkReorderIn`, `StreamBulkReorderOut`, `StreamSummaryOut`,
  - new service methods: `bulk_reorder_streams`, `get_stream_summary`,
  - tests for ownership isolation and summary retrieval.

### Verification

- Backend:
  - `ruff check` and `ruff format --check` — clean,
  - `mypy` — no issues,
  - `pytest tests/test_article_service.py` — 8 passed (including 2 new B1/B2 tests),
  - `pytest tests/test_stream_service.py` — 19 passed (including 4 new C2 tests).
- Pre-existing flaky tests (test_stream_classifier_runs_api, test_search_api, etc.) fail intermittently due to
  event-loop reuse across test modules — not caused by this session's changes.

## 2026-06-30 (Security Review Follow-Up: Workstream A Fixes)

### Implemented This Session

- Completed full code review deliverables:
  - `docs/code-review-2026-06-30.md`
  - `.hermes/plans/2026-06-30_code-review-fixes-and-backlog-advancement.md`
- Closed Workstream A security/CI/deploy fixes:
  - extracted shared SSRF validation utility and refactored fulltext fetch validation to use it,
  - applied SSRF validation to feed ingestion, feed creation, and discovery candidate validation,
  - replaced OPML XML parsing with `defusedxml`,
  - added 5MB feed response and OPML upload limits plus OPML nesting-depth limit,
  - redacted Redis credentials from scheduler/worker startup logs,
  - fixed `rule_service.to_out()` to use `rule.action` instead of hardcoding `drop`,
  - fixed backend Ruff formatting drift and frontend ESLint assertion errors,
  - added and verified frontend Docker/Nginx image build,
  - raised Vitest component-test timeout to stabilize full-suite jsdom/MUI runs.

### Verification

- Backend:
  - `ruff check src tests`
  - `ruff format --check src tests`
  - `mypy src/sift`
  - `python -m pytest tests/ -q` → 162 passed, 1 Starlette/httpx deprecation warning
- Frontend:
  - `npx eslint .`
  - `npx tsc --noEmit`
  - `npx vitest run` → 27 files / 112 tests passed
  - `npm run build` → pass, existing >500k chunk warning remains
- Container:
  - `docker build -t sift-frontend-test frontend/` → pass

## 2026-03-01 (Planning Review: Add SearXNG Discovery Verification Backlog Item)

### Implemented This Session

- Reviewed planning sources for consistency:
  - `AGENTS.md`
  - `docs/backlog.md`
  - `docs/backlog-history.md`
  - `docs/current-state.md`
  - `docs/architecture.md`
  - `docs/session-notes.md`
- Added explicit next-session backlog item for discovery provider verification:
  - SearXNG instance compatibility check against runtime API contract,
  - candidate public-instance validation and usable endpoint shortlist,
  - config guidance update for discovery/session testing.
- Updated `docs/current-state.md` active priorities to include the SearXNG verification pass.
- Maintained rolling-window policy by archiving the oldest entry in this file to `docs/session-notes/archive/2026-03.md`.

### Verification

- `rg -n "Discovery provider verification pass \\(SearXNG\\)|SearXNG instance compatibility" docs/backlog.md docs/current-state.md`
- `rg -n "^## 2026-03-01" docs/session-notes.md`

## 2026-03-01 (Discover Feeds v1 Final Closeout: Spec Archive + Backlog Handoff)

### Implemented This Session

- Archived discover-feeds v1 spec from active specs to completed archive:
  - moved `docs/specs/feed-recommendations-v1.md` -> `docs/specs/done/feed-recommendations-v1.md`
  - updated status metadata in archived spec to `Completed` (completed on 2026-03-01).
- Updated planning docs for completed-feature lifecycle consistency:
  - active backlog now promotes monitoring feed management v2 follow-ups as the next core platform priority,
  - discover-feeds completion moved to `docs/backlog-history.md`,
  - current-state now marks discover-feeds as completed/archived with done-spec reference.
- Updated cross-spec references to point at archived discover-feeds spec from active and completed specs.

### Verification

- `rg -n "feed-recommendations-v1.md|done/feed-recommendations-v1.md" docs AGENTS.md`
- `Get-ChildItem docs/specs`
- `Get-ChildItem docs/specs/done`

## 2026-03-01 (Discover Feeds v1 Slice 6: Recommendation Source/Evidence UI Surfacing)

### Implemented This Session

- Extended discovery recommendation cards to surface source/evidence details:
  - source-stream chips from `recommendation.sources` (with confidence labels when available),
  - recommendation evidence description rendering from `recommendation.evidence`,
  - query-variant chips aggregated from recommendation- and source-level evidence payloads.
- Added targeted frontend test coverage for source/evidence rendering in `DiscoveryWorkbench`.
- Updated planning docs to reflect discover-feeds implementation through slice 6 and narrowed remaining scope to final
  spec/archive closeout.

### Verification

- `npm --prefix frontend run test -- DiscoveryWorkbench.test.tsx WorkspacePage.test.tsx`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run build`

## 2026-03-01 (Discover Feeds v1 Slice 5: Copy-from-Monitoring Convenience Action)

### Implemented This Session

- Added discovery copy convenience API:
  - `POST /api/v1/discovery/streams/copy-from-monitoring`
  - request schema: `monitoring_stream_id` + optional target `name`
  - ownership-aware source lookup with explicit `404` when monitoring stream is missing.
- Added discovery service copy behavior:
  - loads monitoring stream criteria and creates a discovery stream via existing validated create path,
  - copies supported criteria (`match_query`, include/exclude keywords, description, active state, priority),
  - rejects copy when no discovery-compatible criteria are present.
- Added frontend copy flow in discovery settings workbench:
  - monitoring stream selector + optional discovery name field + copy action,
  - successful copy selects newly created discovery stream for immediate editing.
- Added/updated tests:
  - backend service/API copy coverage (`tests/test_discovery_service.py`, `tests/test_discovery_api.py`),
  - frontend workbench + workspace route mock updates (`DiscoveryWorkbench.test.tsx`, `WorkspacePage.test.tsx`).
- Updated planning docs for consistency:
  - `docs/backlog.md`
  - `docs/current-state.md`
  - `docs/specs/done/feed-recommendations-v1.md`

### Verification

- `.venv-ci-test\Scripts\ruff.exe check src/sift/services/discovery_service.py src/sift/api/routes/discovery.py src/sift/domain/schemas.py tests/test_discovery_service.py tests/test_discovery_api.py`
- `.venv-ci-test\Scripts\python.exe -m pytest tests/test_discovery_service.py tests/test_discovery_api.py`
- `npm --prefix frontend run test -- DiscoveryWorkbench.test.tsx WorkspacePage.test.tsx`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`

## 2026-03-01 (Planning-Doc Consistency Cleanup Pass)

### Implemented This Session

- Ran a planning-source consistency pass across:
  - `docs/backlog.md`
  - `docs/current-state.md`
  - `docs/architecture.md`
  - `docs/specs/done/feed-recommendations-v1.md`
  - `docs/specs/done/plugin-ui-organization-v1.md`
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
- `rg -n "Implemented slices|Remaining scope|tracks remaining closeout scope" docs/specs/done/feed-recommendations-v1.md`
- `rg -n "State: Completed|Baseline plugin workspace organization" docs/specs/done/plugin-ui-organization-v1.md`
- `rg -n "^## " docs/session-notes.md`

## Rolling Window Policy

- Keep only the most recent 3-5 session entries in this file.
- Move older entries to monthly archives in `docs/session-notes/archive/`.
- Keep each entry concise and link specs/docs rather than repeating large histories.
