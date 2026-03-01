# Session Notes

This file is a rolling recent execution log for fast session startup.
Historical notes are archived by month under `docs/session-notes/archive/`.

## 2026-03-01 (Search Provider Plugin v1 Completion: Provider Hardening Closeout + Spec Archive)

### Implemented This Session

- Completed search-provider runtime hardening:
  - adapter-level warning-coded failure mapping for timeout/network/http/json/payload failures,
  - URL normalization and candidate de-duplication in runtime adapters.
- Preserved provider warning codes through search orchestration into API `warning_details` metadata.
- Added runtime hardening tests:
  - timeout handling
  - HTTP 429 warning mapping
  - invalid JSON handling
  - candidate dedupe/normalization
  - missing Brave API key behavior
- Added service-level warning-code preservation test for fallback behavior.
- Marked search-provider v1 complete and archived spec to:
  - `docs/specs/done/search-provider-plugin-v1.md`
- Updated planning docs so next active platform priority is now discover-feeds v1.

### Verification

- `python -m ruff check src/sift/plugins/builtin/search_provider_runtime.py src/sift/services/search_service.py tests/test_search_provider_runtime.py tests/test_search_service.py`
- `python -m mypy src/sift/plugins/builtin/search_provider_runtime.py src/sift/services/search_service.py tests/test_search_provider_runtime.py tests/test_search_service.py --no-incremental`
- `python -m pytest tests/test_search_provider_runtime.py tests/test_search_service.py tests/test_search_api.py`

## 2026-03-01 (Plugin Architecture Hardening + Search Provider v1 Slice 3)

### Implemented This Session

- Plugin architecture/runtime consistency hardening:
  - added shared capability contract metadata (`src/sift/plugins/capabilities.py`),
  - plugin manager now stores/exposes runtime-loaded registry entries (`get_registry_entries()`),
  - `/api/v1/plugins/areas` and `/api/v1/search/*` now resolve config from runtime manager snapshot rather than
    per-request registry reload.
- Search provider v1 slice 3:
  - added DB-backed daily provider budget ledger (`search_provider_budget_daily` + Alembic migration
    `20260301_0017`),
  - enforced persistent `max_requests_per_day` and `min_interval_ms` budget constraints in search orchestration,
  - retained run-local `max_requests_per_run` cap enforcement,
  - added explicit response warning metadata (`warning_details`) with stable warning codes.
- Added/updated tests for:
  - persistent daily budget enforcement across service instances,
  - search API/runtime behavior with runtime snapshot-backed registry resolution,
  - plugin areas API runtime snapshot behavior,
  - plugin manager runtime registry snapshot access.

### Verification

- `python -m ruff check src/sift/plugins/capabilities.py src/sift/plugins/registry.py src/sift/plugins/manager.py src/sift/api/routes/plugins.py src/sift/api/routes/search.py src/sift/services/search_service.py src/sift/db/models.py tests/test_search_service.py tests/test_search_api.py tests/test_plugins_api.py tests/test_plugin_runtime_manager.py alembic/versions/20260301_0017_search_provider_budget_daily.py`
- `python -m mypy src/sift/plugins src/sift/api/routes/search.py src/sift/api/routes/plugins.py src/sift/services/search_service.py src/sift/db/models.py tests/test_search_service.py tests/test_search_api.py tests/test_plugins_api.py tests/test_plugin_runtime_manager.py --no-incremental`
- `python -m pytest tests/test_search_service.py tests/test_search_api.py tests/test_plugins_api.py tests/test_plugin_runtime_manager.py tests/test_plugin_registry.py`

## 2026-03-01 (Search Provider Plugin v1 Slice 2: Ordered Fallback + Budget Enforcement + Adapter Baseline)

### Implemented This Session

- Added search-provider orchestration service:
  - ordered provider fallback over configured `provider_chain`,
  - strict in-process provider budget/rate enforcement:
    - `max_requests_per_run`
    - `max_requests_per_day`
    - `min_interval_ms`
- Added runtime provider adapter baseline plugin:
  - `sift.plugins.builtin.search_provider_runtime:SearchProviderRuntimePlugin`
  - provider adapters:
    - `searxng`
    - `brave_search`
  - provider-specific settings wiring via registry `settings.search_provider.providers`.
- Updated default search-provider plugin registry config:
  - switched runtime class path to `SearchProviderRuntimePlugin`
  - added provider adapter settings block (`searxng.base_url`, `brave_search.endpoint`, `brave_search.api_key`)
- Hardened registry validation:
  - requires budget entries for every provider listed in provider chain.
- Added tests for:
  - fallback behavior,
  - min-interval and per-run budget enforcement,
  - missing provider-budget validation.

### Verification

- `python -m ruff check src/sift/plugins/builtin/search_provider_runtime.py src/sift/services/search_service.py src/sift/api/routes/search.py tests/test_search_service.py tests/test_search_api.py tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py`
- `python -m mypy src/sift/plugins src/sift/services/search_service.py src/sift/api/routes/search.py --no-incremental`
- `python -m pytest tests/test_search_service.py tests/test_search_api.py tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py`

## 2026-03-01 (Search Provider Plugin v1 Slice 1: Runtime Contract + Registry Validation + API Baseline)

### Implemented This Session

- Added `search_provider` plugin capability contract and runtime dispatch:
  - plugin manager now supports `search_feeds(request)` capability invocation and timeout control.
  - new plugin timeout setting: `SIFT_PLUGIN_TIMEOUT_SEARCH_PROVIDER_MS`.
- Added search-provider registry validation:
  - `settings.search_provider` is now required when `search_provider` capability is enabled.
  - validates non-empty provider chain, provider budget contract, and allowlisted provider ids.
- Added baseline no-op search-provider plugin implementation:
  - `src/sift/plugins/builtin/search_provider_noop.py`
- Added first authenticated search-provider APIs:
  - `GET /api/v1/search/providers`
  - `POST /api/v1/search/feeds`
- Updated default plugin registry to include enabled `search_provider` plugin entry with conservative provider budgets.

### Verification

- `python -m ruff check src/sift/plugins/base.py src/sift/plugins/manager.py src/sift/plugins/registry.py src/sift/plugins/builtin/search_provider_noop.py src/sift/api/routes/search.py src/sift/api/router.py src/sift/config.py src/sift/core/runtime.py src/sift/domain/schemas.py tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py tests/test_search_api.py`
- `python -m mypy src/sift/plugins src/sift/api/routes/search.py src/sift/config.py src/sift/core/runtime.py src/sift/domain/schemas.py --no-incremental`
- `python -m pytest tests/test_plugin_runtime_manager.py tests/test_plugin_registry.py tests/test_plugins_api.py tests/test_search_api.py`

## 2026-03-01 (Reprioritization: Search Provider First, Stream Ranking Deferred)

### Implemented This Session

- Updated active core priorities so search-provider infrastructure is now the immediate implementation focus.
- Moved stream-level ranking/prioritization controls out of `Next` and into `Deferred` for now.
- Updated:
  - `docs/backlog.md`
  - `docs/current-state.md`

### Verification

- `rg -n "Core Platform Priorities|Stream-level ranking|Search provider plugin platform v1|Deferred for now" docs/backlog.md docs/current-state.md`

## 2026-03-01 (Architecture Compaction Pass + Planning Context Review)

### Implemented This Session

- Compacted `docs/architecture.md` a second time:
  - reduced `Frontend Plugin Surface` from verbose per-point contract details to a concise extension-point contract.
  - reduced `Implemented Service Slices` from endpoint-level chronology to capability-level architecture summary.
- Preserved architecture intent while shifting implementation chronology to:
  - `docs/current-state.md`
  - `docs/backlog-history.md`
  - `docs/session-notes/archive/`
- Ran cross-doc consistency checks for context-window policy, startup sources, and planning-source pointers.

### Verification

- `rg -n "docs/current-state.md|docs/backlog.md|docs/session-notes/archive|Rolling Window Policy|Planning Sources|Implemented Service Slices|Frontend Plugin Surface" AGENTS.md docs/architecture.md docs/session-notes.md`
- section size check in `docs/architecture.md` confirms compaction of the two largest sections.

## 2026-03-01 (Context Window Optimization and Planning Doc Compaction)

### Implemented This Session

- Compacted `AGENTS.md` to stable guidance only and removed volatile roadmap/history duplication.
- Added `docs/current-state.md` as the startup snapshot for implementation status and constraints.
- Archived the previous full session log to:
  - `docs/session-notes/archive/2026-02.md`
- Replaced this file with a rolling-window format.
- Pruned roadmap/backlog sections from `docs/architecture.md` and added explicit planning source pointers.

### Verification

- `rg -n "Context Window Policy|Planning Workflow For Future Sessions|docs/current-state.md" AGENTS.md`
- `rg -n "Planning Sources|Planned Next Moves|Long-Term Product Backlog" docs/architecture.md`
- `Test-Path docs/session-notes/archive/2026-02.md`
- `Get-Content docs/session-notes.md -TotalCount 80`

## 2026-02-23 (Observability v1 Close + Local Observability Bootstrap)

### Implemented This Session

- Closed scheduler/ingestion observability v1 and archived spec to `docs/specs/done/`.
- Completed scheduler/worker scrape endpoint integration and observability runbook updates.
- Added local VictoriaMetrics/VictoriaLogs/Vector bootstrap assets in `ops/observability/`.

### Verification

- `python -m pytest tests/test_metrics_server.py tests/test_scheduler.py tests/test_worker_jobs.py tests/test_observability_api.py tests/test_observability_logging.py tests/test_ingestion_service.py`
- `docker compose -f docker-compose.yml -f ops/observability/docker-compose.observability.yml config`

## 2026-02-22 (Planning Split: Search Provider Infrastructure vs Discover Workflow)

### Implemented This Session

- Split provider runtime planning into `docs/specs/search-provider-plugin-v1.md`.
- Refocused discover workflow planning in `docs/specs/feed-recommendations-v1.md`.
- Updated planning/backlog docs for dependency ordering and ownership boundaries.

### Verification

- `rg -n "search-provider-plugin-v1.md|feed-recommendations-v1.md" docs AGENTS.md`

## Rolling Window Policy

- Keep only the most recent 3-5 session entries in this file.
- Move older entries to monthly archives in `docs/session-notes/archive/`.
- Keep each entry concise and link specs/docs rather than repeating large histories.
