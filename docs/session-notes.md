# Session Notes

## 2026-02-22 (GitFlow + CI/CD + GHCR Release Pipeline Implementation)

### Implemented This Session

- Replaced single legacy CI workflow with split GitFlow-oriented automation:
  - added `.github/workflows/ci-fast.yml` for PRs into `develop`
  - added `.github/workflows/release-readiness.yml` for PRs into `main`
  - added `.github/workflows/release-main.yml` for release/tag/image automation on `main` pushes
  - added `.github/workflows/codeql.yml` for code scanning on `develop`/`main` PR+push and weekly schedule
- Added security/dependency automation:
  - added `.github/dependabot.yml`
  - added `.github/release.yml` release notes categorization
  - added `.github/labeler.yml` path-based auto-label mapping config
- Added production release container topology:
  - `docker/backend.Dockerfile`
  - `docker/frontend.Dockerfile` (multi-stage build + Nginx runtime)
  - `docker/nginx.conf` (SPA fallback + `/api` reverse proxy to app)
  - `docker-compose.release.yml` for GHCR image-based upgrades
- Added frontend formatting gate:
  - installed `prettier` in frontend dev deps
  - added `frontend/.prettierrc` and `frontend/.prettierignore`
  - added `frontend` script: `format:check`
- Updated project docs for development/deployment/release model:
  - `README.md`
  - `docs/development.md`
  - `docs/deployment.md`
  - `docs/architecture.md`
  - new `docs/release-cycle.md`
  - updated `AGENTS.md` branching/release working agreement notes

### Notes

- GitHub repository settings (default branch switch + branch protection rulesets + required checks/labels) must still be
  applied manually in repository settings.

## 2026-02-22 (Full Article Fetch On-Demand v1 Implemented End-to-End)

### Implemented This Session

- Completed backend fulltext fetch foundation:
  - added `article_fulltexts` model + migration (`alembic/versions/20260222_0016_article_fulltexts.py`)
  - added fulltext fetch runtime service (`src/sift/services/article_fulltext_service.py`) with URL safety checks
  - added endpoint `POST /api/v1/articles/{article_id}/fulltext/fetch`
  - extended article detail projection with fulltext status/content fields and `content_source`
- Completed frontend reader integration:
  - added reader action (`Fetch full article` / `Refetch full article`) with pending/error behavior
  - wired fetch mutation + detail invalidation in workspace hooks
  - reader now renders full extracted content when available and shows source label
  - regenerated OpenAPI frontend types for new API/schema contracts
- Closed planning/docs for this slice:
  - moved spec to `docs/specs/done/full-article-fetch-on-demand-v1.md`
  - updated `docs/backlog.md`, `docs/backlog-history.md`, `docs/architecture.md`, and `AGENTS.md`
    to mark full-article-fetch as completed and shift next priorities back to ranking/observability

### Verification

- backend:
  - `python -m pytest tests/test_article_fulltext_service.py tests/test_article_fulltext_api.py`
  - `python -m ruff check src/sift/api/routes/articles.py src/sift/services/article_fulltext_service.py src/sift/services/article_service.py src/sift/db/models.py src/sift/domain/schemas.py tests/test_article_fulltext_service.py tests/test_article_fulltext_api.py`
  - `python -m mypy src/sift/services/article_fulltext_service.py src/sift/services/article_service.py src/sift/api/routes/articles.py src/sift/domain/schemas.py --no-incremental`
- frontend:
  - `npm --prefix frontend run test -- src/features/workspace/components/ReaderPane.test.tsx src/features/workspace/routes/WorkspacePage.test.tsx src/entities/article/model.test.ts`
  - `npm --prefix frontend run typecheck`
  - `npm --prefix frontend run lint`

## 2026-02-22 (Reprioritization: Full Article Fetch On-Demand to Top Priority)

### Implemented This Session

- Promoted `full article fetch on-demand v1` to the top active implementation priority.
- Updated planning docs for alignment:
  - `docs/backlog.md`
  - `AGENTS.md`
  - `docs/architecture.md`
- Removed stale deferred references so `full article fetch` is no longer tracked as deferred.
- Confirmed spec already exists and remains the implementation source:
  - `docs/specs/done/full-article-fetch-on-demand-v1.md`

### Verification

- planning/docs consistency checks:
  - `rg -n "full article fetch|full-article-fetch-on-demand|Next Delivery Sequence|Planned Next Moves|Deferred" docs/backlog.md AGENTS.md docs/architecture.md docs/session-notes.md`

## 2026-02-22 (Plugin Configuration Registry Follow-Up: Security + Budget Contracts)

### Implemented This Session

- Added plugin registry security validation for sensitive settings keys in `src/sift/plugins/registry.py`:
  - plaintext secret/token/password/api-key style values are rejected
  - sensitive values must use env references (for example `${SIFT_API_KEY}`)
- Added discover-feeds provider budget contract validation in `src/sift/plugins/registry.py`:
  - validates provider-chain shape
  - validates per-provider budget fields and integer bounds
  - validates `max_requests_per_day >= max_requests_per_run`
- Added baseline discover-feeds budget config in `config/plugins.yaml`.
- Added registry tests in `tests/test_plugin_registry.py` for:
  - sensitive-value rejection
  - env-reference acceptance
  - invalid discover budget contract rejection
  - valid discover budget contract acceptance
- Updated planning docs to advance active priorities to post-plugin-foundation slices.

### Verification

- `python -m pytest tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py tests/test_plugins_api.py`
- `python -m ruff check src/sift/plugins/registry.py tests/test_plugin_registry.py`
- `python -m mypy src/sift/plugins/registry.py tests/test_plugin_registry.py --no-incremental`

## 2026-02-22 (Plugin Runtime Telemetry Contract Closure)

### Implemented This Session

- Added runtime plugin telemetry collector wiring in `PluginManager`:
  - `sift_plugin_invocations_total{plugin_id,capability,result}`
  - `sift_plugin_invocation_duration_seconds{plugin_id,capability,result}`
  - `sift_plugin_timeouts_total{plugin_id,capability}`
  - `sift_plugin_dispatch_failures_total{capability}`
- Added exporter surfaces for plugin metrics:
  - in-memory typed snapshot (`get_telemetry_snapshot`)
  - Prometheus-text rendering (`render_telemetry_prometheus`)
- Added contract-level runtime tests in `tests/test_plugin_runtime_manager.py` for:
  - metrics emission and label/value mapping
  - rendered metrics name presence
  - structured logging required field assertions
- Marked runtime hardening spec complete and archived to:
  - `docs/specs/done/plugin-runtime-hardening-diagnostics-v1.md`
- Updated planning docs to remove runtime hardening from active Next priorities:
  - `docs/backlog.md`
  - `AGENTS.md`
  - `docs/architecture.md`
  - `docs/backlog-history.md`

### Verification

- `python -m pytest tests/test_plugin_runtime_manager.py tests/test_plugin_registry.py tests/test_plugins_api.py tests/test_dashboard_api.py`
- `python -m ruff check src/sift/plugins tests/test_plugin_runtime_manager.py`
- `python -m mypy src/sift/plugins tests/test_plugin_runtime_manager.py --no-incremental`

## 2026-02-22 (Plugin Verification + Backlog/Spec Cleanup Pass)

### Implemented This Session

- Verified plugin-platform implementation status against current backend/frontend tests and static checks.
- Archived completed plugin/dashboard foundation specs to `docs/specs/done/`:
  - `plugin-platform-foundation-v1.md`
  - `frontend-plugin-host-workspace-areas-v1.md`
  - `dashboard-shell-plugin-host-v1.md`
- Updated planning docs so active backlog reflects remaining work only:
  - `docs/backlog.md`
  - `AGENTS.md`
  - `docs/architecture.md`
  - `docs/backlog-history.md`
- Updated spec references to use archived paths where applicable and corrected moved-spec relative links.
- Clarified remaining plugin backlog scope:
  - telemetry metrics export + contract assertions (`plugin-runtime-hardening-diagnostics-v1`)
  - config security and provider-budget contract follow-ups (`plugin-configuration-registry-v1`)

### Verification

- backend tests:
  - `python -m pytest tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py tests/test_plugins_api.py tests/test_dashboard_api.py`
- frontend tests:
  - `npm --prefix frontend run test -- --run src/features/workspace/plugins/registry.test.tsx src/features/workspace/plugins/PluginAreaHost.test.tsx src/features/workspace/components/NavigationPane.test.tsx src/features/workspace/routes/WorkspacePage.test.tsx src/features/dashboard/components/DashboardHost.test.tsx`
- static checks:
  - `python -m ruff check src/sift/plugins src/sift/core/runtime.py src/sift/api/routes/plugins.py src/sift/api/routes/dashboard.py tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py tests/test_plugins_api.py tests/test_dashboard_api.py`
  - `python -m mypy src/sift/plugins src/sift/core/runtime.py src/sift/api/routes/plugins.py src/sift/api/routes/dashboard.py --no-incremental`

### Notes

- `uv run` remains blocked in this local environment by `.venv/lib64` access errors; direct `python -m ...` commands
  were used for backend verification.

## 2026-02-22 (Dashboard Shell + Plugin Card Host Baseline)

### Implemented This Session

- Added dashboard summary metadata API:
  - new endpoint `GET /api/v1/dashboard/summary` in `src/sift/api/routes/dashboard.py`
  - endpoint returns deterministic card availability metadata (`ready` / `unavailable` / `degraded`)
- Added frontend dashboard shell route and host:
  - `/app/dashboard` route in frontend router
  - dashboard rail action now navigates to `/app/dashboard`
  - workspace rail + navigation remain visible while dashboard host replaces list/reader panes
- Added plugin-ready dashboard card host baseline:
  - `frontend/src/features/dashboard/components/DashboardHost.tsx`
  - card-level isolation boundary and deterministic fallback handling
  - built-in baseline `saved_followup` card registration plus unavailable/degraded fallback rendering

### Verification

- backend:
  - `python -m ruff check src tests`
  - `python -m mypy src --no-incremental`
  - `python -m pytest tests/test_dashboard_api.py tests/test_plugins_api.py tests/test_plugin_runtime_manager.py tests/test_plugin_registry.py tests/test_stream_service.py tests/test_ingestion_service.py`
- frontend:
  - `npm --prefix frontend run lint`
  - `npm --prefix frontend run typecheck`
  - `npm --prefix frontend run test`
  - `npm --prefix frontend run build`

### Remaining Scope

- Keep `docs/specs/done/dashboard-shell-plugin-host-v1.md` in progress for:
  - broader plugin-provided `dashboard_card` mount coverage prior to command-center card/data rollout

## 2026-02-22 (Frontend Plugin Host + Workspace Areas Baseline)

### Implemented This Session

- Added backend plugin area metadata endpoint:
  - `GET /api/v1/plugins/areas` in `src/sift/api/routes/plugins.py`
  - endpoint returns enabled, loaded workspace plugin areas from registry UI metadata
- Added frontend plugin area host baseline:
  - typed plugin area registration/runtime in `frontend/src/features/workspace/plugins/registry.ts`
  - baseline plugin mount host + error-boundary isolation in
    `frontend/src/features/workspace/plugins/PluginAreaHost.tsx`
- Added workspace plugin navigation and route integration:
  - `Plugins` section in `NavigationPane`
  - plugin area route branch `/app/plugins/$areaId` in router
  - plugin area rendering inside existing workspace shell in `WorkspacePage`
- Added baseline `discover_feeds` plugin area metadata in `config/plugins.yaml`.

### Verification

- backend:
  - `python -m ruff check src tests`
  - `python -m mypy src --no-incremental`
  - `python -m pytest tests/test_plugins_api.py tests/test_plugin_runtime_manager.py tests/test_plugin_registry.py tests/test_stream_service.py tests/test_ingestion_service.py`
- frontend:
  - `npm --prefix frontend run lint`
  - `npm --prefix frontend run typecheck`
  - `npm --prefix frontend run test`
  - `npm --prefix frontend run build`

### Remaining Scope

- Keep `docs/specs/done/frontend-plugin-host-workspace-areas-v1.md` in progress for:
  - broader extension-point coverage beyond workspace-area baseline

## 2026-02-22 (Plugin Runtime Hardening + Diagnostics Baseline)

### Implemented This Session

- Completed runtime guardrails and diagnostics baseline for plugins:
  - `src/sift/plugins/manager.py` now provides timeout-guarded, fault-isolated dispatch for ingest/classifier hooks
  - runtime counters and status snapshots are tracked per plugin/capability (success/failure/timeout)
  - plugin load/capability contract failures are non-fatal per plugin and remain visible in status output
- Added admin diagnostics API:
  - new endpoint `GET /api/v1/plugins/status` via `src/sift/api/routes/plugins.py`
  - endpoint is auth-protected + admin-only and can be disabled with `SIFT_PLUGIN_DIAGNOSTICS_ENABLED`
- Added configuration controls and docs wiring:
  - timeout settings added in `src/sift/config.py` and `.env.example`
  - API/router wiring updated for plugin diagnostics route
- Added coverage:
  - `tests/test_plugin_runtime_manager.py`
  - `tests/test_plugins_api.py`

### Verification

- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `python -m pytest tests/test_plugin_registry.py tests/test_plugin_runtime_manager.py tests/test_plugins_api.py tests/test_stream_service.py tests/test_ingestion_service.py`

### Remaining Scope

- Keep `docs/specs/done/plugin-runtime-hardening-diagnostics-v1.md` in progress for:
  - explicit metrics backend export wiring (`sift_plugin_*` names)
  - dedicated telemetry contract assertions beyond current runtime/API behavior tests

## 2026-02-22 (Plugin Platform Foundation v1: Registry + Runtime Cutover Baseline)

### Implemented This Session

- Implemented centralized plugin registry loading/validation:
  - added `src/sift/plugins/registry.py` with strict schema validation for:
    - unique plugin ids
    - known capability keys only
    - strict field-set enforcement (`extra=forbid`)
  - added default registry file `config/plugins.yaml` with first-party built-ins
- Cut over runtime plugin initialization:
  - `src/sift/core/runtime.py` now loads plugins from registry (`SIFT_PLUGIN_REGISTRY_PATH`)
  - `src/sift/config.py` now uses `plugin_registry_path` and no longer relies on legacy `plugin_paths`
  - `.env.example` now exposes `SIFT_PLUGIN_REGISTRY_PATH=config/plugins.yaml`
- Updated plugin manager behavior to registry/capability model:
  - `src/sift/plugins/manager.py` now loads `PluginRegistryEntry` records
  - ingest and classifier dispatch are capability-gated by declared plugin capabilities
- Added regression coverage:
  - new `tests/test_plugin_registry.py` for validation, capability gating, and runtime registry-path loading

### Verification

- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `python -m pytest tests/test_plugin_registry.py tests/test_stream_service.py tests/test_ingestion_service.py`

### Notes / Remaining Scope

- `uv run ...` could not be used in this local environment due a `.venv\\lib64` access error; direct `python -m ...`
  commands were used for verification.
- Remaining plugin-platform scope stays active:
  - runtime hardening/diagnostics (`docs/specs/done/plugin-runtime-hardening-diagnostics-v1.md`)
  - frontend plugin host/workspace areas (`docs/specs/done/frontend-plugin-host-workspace-areas-v1.md`)
  - dashboard shell host (`docs/specs/done/dashboard-shell-plugin-host-v1.md`)

## 2026-02-22 (Plugin-First Planning Session: Spec Set Authored)

### Implemented This Session

- Authored new active planning specs for the plugin-first priority stack:
  - `docs/specs/done/plugin-platform-foundation-v1.md`
  - `docs/specs/done/plugin-runtime-hardening-diagnostics-v1.md`
  - `docs/specs/done/frontend-plugin-host-workspace-areas-v1.md`
  - `docs/specs/done/dashboard-shell-plugin-host-v1.md`
- Updated dashboard planning dependency wiring:
  - `docs/specs/dashboard-command-center-v1.md` now references dashboard shell host as an explicit foundation
    dependency/spec gate item
- Updated source-of-truth planning docs to reference new specs and sequencing:
  - `docs/backlog.md` core priorities now include direct spec links for each plugin-first step
  - `AGENTS.md` `Next Delivery Sequence` now includes direct spec links
  - `docs/architecture.md` `Planned Next Moves` now includes direct spec links
  - dashboard spec-gate checklists in backlog/architecture/AGENTS now include
    `docs/specs/done/dashboard-shell-plugin-host-v1.md`

### Verification

- Documentation/planning update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- Consistency checks:
  - `rg -n "plugin-platform-foundation-v1|plugin-runtime-hardening-diagnostics-v1|frontend-plugin-host-workspace-areas-v1|dashboard-shell-plugin-host-v1|dashboard-shell-plugin-host" docs/backlog.md AGENTS.md docs/architecture.md docs/specs docs/session-notes.md`

## 2026-02-22 (Planning Reprioritization: Plugin Architecture First)

### Implemented This Session

- Reprioritized active planning from feature-first sequencing to plugin-platform-first sequencing:
  - `docs/backlog.md` `Core Platform Priorities` now starts with plugin registry/runtime/frontend-host/dashboard-host
    foundation work
  - `AGENTS.md` `Next Delivery Sequence` now mirrors the same plugin-first order
  - `docs/architecture.md` `Planned Next Moves` now mirrors the same plugin-first order
- Removed deferred duplicate plugin-foundation item after promotion to active priorities:
  - removed deferred `Plugin UI Areas + Centralized Plugin Configuration` item from `docs/backlog.md`
  - updated deferred sequence ordering in `docs/backlog.md` and `docs/architecture.md`
- Locked planning decision for plugin configuration migration:
  - direct cutover to centralized plugin registry
  - no legacy `plugin_paths` compatibility mode
  - updated `docs/specs/plugin-configuration-registry-v1.md` rollout notes accordingly

### Verification

- Documentation/planning update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- Consistency checks:
  - `rg -n "Core Platform Priorities|Next Delivery Sequence|Planned Next Moves|plugin_paths|Deferred Delivery Sequence" docs/backlog.md AGENTS.md docs/architecture.md docs/specs/plugin-configuration-registry-v1.md`

## 2026-02-22 (Desktop Reader/Workspace Polish v2 Closure Verification)

### Implemented This Session

- Verified closure criteria for `Desktop reader/workspace polish v2` and aligned planning docs:
  - updated `docs/backlog.md` to remove active UI-only polish scope and mark the slice closed
  - updated `AGENTS.md` and `docs/architecture.md` to reflect the same closed status and evidence
- Verified screenshot gate evidence from:
  - `artifacts/desktop-review-2026-02-21T23-27-06-123Z`
  - capture set includes `1920x1080` and `1366x768` screenshots for `/app`, `/account`, `/account/feed-health`,
    `/account/monitoring`, and `/help`

### Verification

- frontend quality gates (rerun at close):
  - `npm --prefix frontend run lint`
  - `npm --prefix frontend run typecheck`
  - `npm --prefix frontend run test`
  - `npm --prefix frontend run build`
- screenshot dimensions check:
  - verified PNG dimensions in `artifacts/desktop-review-2026-02-21T23-27-06-123Z` match target viewports
    (`1920x1080`, `1366x768`)

## 2026-02-22 (Session Close Consolidation / Next-Session Handoff)

### Session Close State

- Branch: `develop`
- Latest pushed commits:
  - `b047508` (`Polish desktop readability and track deferred mobile planning`)
  - `ebf9025` (`Enforce mobile read-only mode for workspace and settings`)
- Working tree is clean at close.

### Backlog Consolidation

- `docs/backlog.md` now marks a single active UI slice: `Desktop reader/workspace polish v2`.
- Mobile planning remains explicitly deferred as a dedicated future planning session.
- `AGENTS.md` is aligned with the same active/deferred UI direction.
- `docs/backlog-history.md` now records the completed 2026-02-22 mobile read-focus + desktop readability pass.

### Next Session Quick Start

1. Read:
   - `AGENTS.md`
   - `docs/backlog.md`
   - `docs/session-notes.md` (top two 2026-02-22 entries)
2. Run baseline validation:
   - `npm --prefix frontend run lint`
   - `npm --prefix frontend run typecheck`
   - `npm --prefix frontend run test`
3. Start `Desktop reader/workspace polish v2` with screenshot QA gate at:
   - `1920x1080`
   - `1366x768`

## 2026-02-22 (Mobile Read-Only Mode + Desktop Readability Tightening)

### Implemented This Session

- Enforced mobile read-only behavior for app focus on feed reading:
  - mobile routes now redirect from `/account`, `/account/feed-health`, `/account/monitoring`, and `/help` to `/app`
  - mobile workspace rail now exposes reading-only actions (`Nav`, `Saved`, `Search`)
  - mobile navigation pane now hides feed/folder management controls and action menus/dialogs
- Added test coverage for mobile/read-only behavior:
  - read-only management controls hidden in `NavigationPane` tests
  - mobile workspace rail behavior updated in `WorkspacePage` route tests
- Applied desktop readability/alignment polish pass:
  - improved article-list readability by reducing read-row fade and strengthening metadata text
  - refined reader header rhythm (title scale + top spacing) for tighter vertical alignment
  - improved feed-health/monitoring table legibility with slightly stronger caption sizing and row separators
  - monitoring rules summary text now uses a larger, easier-to-scan type style
- Backlog update:
  - added deferred item for a dedicated future mobile UX planning session in `docs/backlog.md`

### Verification

- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- desktop screenshot review capture:
  - `artifacts/desktop-review-2026-02-21T23-27-06-123Z`

## 2026-02-21 (Viewport Balance Polish Pass)

### Implemented This Session

- Applied a visual-balance-only responsive polish pass in `frontend/src/app/styles.css` for target viewports:
  - `1920x1080` / `1366x768`:
    - tightened list/reader spacing and row rhythm
    - normalized panel shell spacing for settings routes
  - `768x1024`:
    - tuned rail sizing and typography
    - made tablet workspace composition read as two-pane (`list + reader`) while nav remains drawer-based
  - `390x844` / `320x480`:
    - compacted top rail into icon-first mobile strip
    - improved list header/control stacking and sticky offsets
    - enabled two-line mobile article titles and tighter reader typography/padding
  - feed health and monitoring tables:
    - added controlled horizontal overflow behavior with stable minimum row-content width
    - preserved one-row operational density without destructive text clipping

### Verification

- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`

## 2026-02-21 (Workspace/UI Alignment + Responsive Single-Route Pass)

### Implemented This Session

- Delivered phased UI touch-up implementation for workspace and settings surfaces:
  - tokenized alignment pass in `frontend/src/app/styles.css`:
    - normalized layout tokens (`--rail-width`, `--nav-width`, `--list-width`, splitter/control/rhythm tokens)
    - unified control sizing/radius and baseline line-height rhythm
    - added table row/name-cell style hooks for condensed feed-health/monitoring rows
  - workspace responsive mode contract in `frontend/src/features/workspace/routes/WorkspacePage.tsx`:
    - explicit breakpoint-driven layout modes (`desktop`, `tablet`, `mobile`)
    - desktop: 3-pane with splitters and resizable panes
    - tablet: 2-pane with collapsible nav drawer
    - mobile: single active pane flow with nav drawer + list/reader transitions
    - mobile default is now list when `article_id` is unset
  - mobile navigation affordances:
    - `Back to nav` action in list header (`ArticlesPane`)
    - `Back to nav` + `Back to list` actions in reader (`ReaderPane`)
  - settings shell alignment:
    - settings/workspace nav breakpoint parity moved to `1200px` in `SettingsWorkspaceShell`
  - long-name handling:
    - monitoring feed name cells now wrap (no forced `noWrap`)
    - feed-health and monitoring rows now use condensed row class hooks for consistency
- Added/updated test coverage:
  - new route-level responsive behavior tests:
    - `frontend/src/features/workspace/routes/WorkspacePage.test.tsx`
  - component interaction tests:
    - `frontend/src/features/workspace/components/ArticlesPane.test.tsx` (mobile back-to-nav)
    - `frontend/src/features/workspace/components/ReaderPane.test.tsx` (back-to-nav)
  - monitoring table wrapping regression:
    - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Verification

- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`

## 2026-02-21 (Workspace + Settings Management UI Touchups v1 Delivered)

### Implemented This Session

- Delivered backend + frontend implementation for workspace/settings management touchups v1:
  - backend:
    - added migration `alembic/versions/20260221_0015_keyword_stream_folder.py`
    - added `keyword_streams.folder_id` persistence and validation
    - stream contracts now support `folder_id` on create/update/out
    - navigation stream payload now includes `folder_id`
    - `GET /api/v1/feeds/health` now supports `all=true`
    - `POST /api/v1/feeds` now supports optional `folder_id`
  - frontend:
    - workspace nav add-folder is now icon-only (`folder-plus`)
    - monitoring/folder expand-collapse controls now use chevrons
    - monitoring streams are grouped by folders in workspace navigation
    - settings routes now use a shared side-menu shell (`/account`, `/account/monitoring`, `/account/feed-health`, `/help`)
    - monitoring management list is now one-row-per-feed definition with icon actions and edit-left form population
    - feed health list is now one-row-per-feed with icon actions and add-feed dialog
    - feed health uses `all=true` query mode by default
- Synced planning/backlog/spec governance:
  - moved implemented spec to `docs/specs/done/workspace-settings-management-ui-touchups-v1.md`
  - updated `docs/backlog.md`, `docs/backlog-history.md`, `AGENTS.md`, and `docs/architecture.md` to reflect completion

### Verification

- Backend:
  - `python -m pytest tests/test_stream_service.py tests/test_navigation_service.py tests/test_feed_health_service.py tests/test_feed_health_api.py`
- Frontend:
  - `pnpm --dir frontend run gen:openapi`
  - `pnpm --dir frontend run test -- src/entities/navigation/model.test.ts src/features/workspace/components/NavigationPane.test.tsx src/features/auth/routes/AccountPage.test.tsx src/features/monitoring/routes/MonitoringFeedsPage.test.tsx src/features/feed-health/routes/FeedHealthPage.test.tsx src/features/help/routes/HelpPage.test.tsx`
  - `pnpm --dir frontend run typecheck`
  - `pnpm --dir frontend run lint`
  - `pnpm --dir frontend run build`

## 2026-02-21 (UI Touchups Planning Spec Captured)

### Implemented This Session

- Added a new implementation-ready UI planning spec:
  - `docs/specs/workspace-settings-management-ui-touchups-v1.md` (now archived at
    `docs/specs/done/workspace-settings-management-ui-touchups-v1.md`)
  - scope includes:
    - icon/chevron navigation touchups
    - monitoring feed folders
    - settings side-menu shell
    - condensed monitoring management rows
    - condensed feed-health rows
    - add-feed flow and all-feeds default loading in feed health
- Updated active backlog tracking:
  - `docs/backlog.md` `Next UI Slice` now points to the new touchups spec
  - `docs/backlog.md` linked specifications now include the new spec
- Updated planning alignment docs:
  - `AGENTS.md` `Next UI Slice (Prioritized)` now points to the new touchups spec
  - `docs/architecture.md` `Next UI Slice (Prioritized)` now points to the new touchups spec

### Verification

- Documentation/planning update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Consistency checks:
  - `Get-ChildItem docs/specs`
  - `rg -n "workspace-settings-management-ui-touchups-v1|Next UI Slice|Linked Specifications" docs/backlog.md AGENTS.md docs/architecture.md docs/session-notes.md docs/specs`

## 2026-02-19 (Observability Planning Spec Captured)

### Implemented This Session

- Added new implementation-ready observability planning spec:
  - `docs/specs/scheduler-ingestion-observability-v1.md`
  - scope is backend runtime observability for API/scheduler/worker and ingestion pipeline telemetry
  - locked decisions captured:
    - OTel-aligned + Prometheus-compatible metrics
    - VMUI-first operational posture for resource efficiency
    - metadata-only logging defaults
    - no collector required in v1
    - trace-ready contract with tracing backend deferred
- Updated active backlog references:
  - `docs/backlog.md` `Next` priority #2 now links the observability spec inline
  - `docs/backlog.md` linked-spec list now includes scheduler/ingestion observability spec
- Kept priority ordering and deferred sequence unchanged.

### Verification

- Documentation/planning update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Consistency checks:
  - `rg -n "scheduler.*observability|scheduler-ingestion-observability-v1|Linked Specifications" docs/backlog.md AGENTS.md docs/architecture.md docs/session-notes.md docs/specs`
  - `Get-ChildItem docs/specs`

## 2026-02-19 (Planning Docs Consolidation Pass)

### Implemented This Session

- Consolidated active planning docs so implemented feed-health work is no longer listed as active `Next` work:
  - updated `docs/backlog.md` core priorities to start with stream ranking, then scheduler observability
  - updated `AGENTS.md` `Next Delivery Sequence` to match
  - updated `docs/architecture.md` `Planned Next Moves` to match
- Consolidated completed-work references:
  - moved completed spec to `docs/specs/done/feed-health-edit-surface-v1.md`
  - updated `docs/backlog-history.md` with completed feed health + edit surface v1 summary
  - updated stale spec/path references in active docs.
- Recorded current next step explicitly in planning docs:
  - next active implementation priority is stream-level ranking and prioritization controls.

### Verification

- Documentation/planning consolidation only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Consistency check commands:
  - `rg -n "feed health \\+ edit surface v1|stream-level ranking and prioritization controls|Planned Next Moves|Next Delivery Sequence" docs/backlog.md AGENTS.md docs/architecture.md docs/backlog-history.md`
  - `Get-ChildItem docs/specs`
  - `Get-ChildItem docs/specs/done`

## 2026-02-19 (Feed Health + Edit Surface v1 Delivered)

### Implemented This Session

- Delivered feed lifecycle + health backend slice:
  - migration added feed lifecycle/fetch metadata fields:
    - `feeds.is_archived`
    - `feeds.archived_at`
    - `feeds.last_fetch_success_at`
    - `feeds.last_fetch_error_at`
  - ingestion bookkeeping now updates success/error timestamps on fetch outcomes
  - scheduler feed candidate selection now excludes archived feeds
  - navigation tree feed nodes now exclude archived feeds
  - new feed health service added for stale/cadence/unread aggregation and filtering
- Added/extended feed APIs:
  - `GET /api/v1/feeds` now supports `include_archived`
  - `GET /api/v1/feeds/health`
  - `PATCH /api/v1/feeds/{feed_id}/settings`
  - `PATCH /api/v1/feeds/{feed_id}/lifecycle`
  - lifecycle behavior includes archive side effect: bulk-mark existing unread feed articles as read
- Delivered frontend feed health management vertical slice:
  - new authenticated route: `/account/feed-health`
  - new account settings entry: `Manage feed health`
  - health filters (`lifecycle`, `stale_only`, `error_only`, `q`)
  - per-feed interval editing and lifecycle actions (pause/resume/archive/unarchive)
  - archive confirmation explicitly mentions unread mark-read behavior
  - success feedback includes archive `marked_read_count`
  - follow-up UI polish completed:
    - clearer filter panel copy/actions (`Apply filters`, `Reset`)
    - additional status context (`Last refreshed`, stale age, interval badge)
    - clearer lifecycle action labels (`Pause updates`, `Resume updates`, `Archive feed`, `Unarchive feed`)
- Added test coverage:
  - `tests/test_feed_health_service.py`
  - `tests/test_feed_health_api.py`
  - extended `tests/test_feed_service.py`
  - extended `tests/test_navigation_service.py`
  - extended `tests/test_ingestion_service.py`
  - `frontend/src/features/feed-health/routes/FeedHealthPage.test.tsx`
  - extended `frontend/src/features/auth/routes/AccountPage.test.tsx`
- Synced planning docs and spec tracking:
  - promoted feed health into `Next` priorities in `docs/backlog.md`
  - added implementation spec `docs/specs/done/feed-health-edit-surface-v1.md` (archived to done after delivery)
  - updated `AGENTS.md` and `docs/architecture.md` priority and API status references.

### Verification

- Backend test suite:
  - `python -m pytest`
- Frontend quality gates:
  - `pnpm --dir frontend run gen:openapi`
  - `pnpm --dir frontend run lint`
  - `pnpm --dir frontend run typecheck`
  - `pnpm --dir frontend run test`
  - `pnpm --dir frontend run build`
- Note:
  - `uv run pytest` was attempted first but failed in this environment due local `.venv` access issues; verification
    used `python -m pytest` successfully.

## 2026-02-19 (Planning Reprioritization: Stream Ranking First, Vector DB Deferred)

### Implemented This Session

- Reprioritized active `Next` platform work in `docs/backlog.md`:
  - kept `stream-level ranking and prioritization controls` as immediate top priority
  - moved `vector-database integration` out of immediate `Next`
  - kept `scheduler and ingestion observability` as the second immediate core priority
  - added explicit deferred backlog item for vector-database integration infrastructure.
- Updated delivery sequencing docs for consistency:
  - `AGENTS.md` `Next Delivery Sequence` now prioritizes stream ranking then scheduler/observability
  - `AGENTS.md` `Deferred` now explicitly lists vector-database integration as later priority
  - `docs/architecture.md` `Planned Next Moves` and deferred delivery sequence now reflect the same order.
- Set `docs/specs/stream-ranking-prioritization-controls-v1.md` status to in-progress kickoff.

### Verification

- Documentation/planning reprioritization only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Consistency check command:
  - `rg -n "stream-level ranking|vector-database integration|scheduler and ingestion observability|Next Delivery Sequence|Core Platform Priorities" docs/backlog.md AGENTS.md docs/architecture.md`

## 2026-02-19 (Process Update: `develop` -> `main` Branching Model)

### Implemented This Session

- Added branch-governance instructions in `AGENTS.md`:
  - `main` is the protected production branch
  - `develop` is the default integration branch for ongoing feature work
  - feature branches should be created from `develop` and merged back into `develop`
  - merge into `main` only after validation/release readiness.

### Verification

- Documentation/process update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.

## 2026-02-19 (Docs Governance Update: Spec Archive Lifecycle)

### Implemented This Session

- Added explicit spec-lifecycle governance in `AGENTS.md`:
  - active/planned specs stay in `docs/specs/`
  - implemented specs move to `docs/specs/done/`
  - planning workflow and knowledge-location sections now include this archive rule.
- Archived implemented specs out of active specs:
  - `docs/specs/done/monitoring-match-visual-explainability-v1.md`
  - `docs/specs/done/workspace-action-iconification-v1.md`
- Updated docs links after archive move:
  - removed completed workspace iconification spec from active linked-spec list in `docs/backlog.md`
  - fixed moved-spec backlog links to `../../backlog.md`
  - updated session-note references for archived spec paths.

### Verification

- Documentation/governance update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Archive + reference validation commands:
  - `Get-ChildItem docs/specs`
  - `Get-ChildItem docs/specs/done`
  - `rg -n "workspace-action-iconification-v1\\.md|monitoring-match-visual-explainability-v1\\.md|docs/specs/done" docs AGENTS.md`

## 2026-02-18 (Planning Update: Dashboard Command Center Program + Spec Gate)

### Implemented This Session

- Added new dashboard planning umbrella spec:
  - `docs/specs/dashboard-command-center-v1.md`
  - locks route/layout direction to `/app/dashboard` while keeping workspace rail + navigation tree visible.
- Added required dependency specs for dashboard build gating:
  - `docs/specs/stream-ranking-prioritization-controls-v1.md`
  - `docs/specs/feed-health-ops-panel-v1.md`
  - `docs/specs/monitoring-signal-scoring-v1.md`
  - `docs/specs/trends-detection-dashboard-v1.md`
- Captured dashboard card/interaction planning decisions:
  - prioritized unread queue via weighted heuristic
  - feed ops health summary panel
  - saved follow-up card
  - high-value monitoring signal card
  - trends card with explicit unavailable state until trend dependency is implemented
  - discovery candidates card with both feed recommendations and monitoring-first candidate articles
  - optional future cards: alerts + follow-up detail
  - hybrid refresh model: summary auto-refresh + per-card manual refresh
- Updated backlog governance for dashboard delivery:
  - added dashboard spec-gate checklist under deferred dashboard item in `docs/backlog.md`
  - added explicit rule that dashboard implementation starts only after dependency specs are drafted and linked.
- Updated planning alignment docs:
  - `docs/architecture.md` dashboard section now reflects `/app/dashboard`, card model, and spec-gate requirement
  - `AGENTS.md` deferred and feature notes now include dashboard command-center direction and dependencies.

### Verification

- Documentation/planning update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Specs/backlog alignment check:
  - `rg -n "dashboard-command-center-v1|spec gate|monitoring-signal-scoring-v1|feed-health-ops-panel-v1|trends-detection-dashboard-v1" docs AGENTS.md`

## 2026-02-18 (Workspace Action Iconification v1 Delivered)

### Implemented This Session

- Implemented icon-first action controls in workspace list/reader surfaces:
  - list control `Mark all in scope as read` is now icon-first with explicit accessibility label
  - reader actions are now icon-first for:
    - `Mark as read` / `Mark as unread`
    - `Save article` / `Remove from saved`
    - `Open original source`
    - `Previous article` / `Next article`
    - `Hide match highlights` / `Show match highlights`
- Preserved existing behavior and keyboard mappings:
  - no changes to action semantics or mutation flows
  - shortcuts remain unchanged (`j/k`, `o`, `m`, `s`)
- Updated component tests for iconified controls:
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`
- Updated planning/source-of-truth docs to mark this UI slice complete:
  - `docs/specs/done/workspace-action-iconification-v1.md` status set to implemented
  - `docs/backlog.md` next UI slice section updated (no active queued slice)
  - `docs/backlog-history.md` archived completed workspace action iconification v1 milestone
  - `docs/architecture.md` and `AGENTS.md` synchronized with completion status.

### Verification

- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx src/features/workspace/components/ReaderPane.test.tsx`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`

## 2026-02-18 (Planning Update: Article LLM Summary On-Demand v1)

### Implemented This Session

- Added new planning spec for on-demand article summaries:
  - `docs/specs/article-llm-summary-on-demand-v1.md`
  - captures planned API additions:
    - `POST /api/v1/articles/{article_id}/summary/generate`
    - `GET /api/v1/articles/{article_id}` summary status/result extension
    - planned plugin contract hook `summarize_article(article, options)`
- Updated deferred backlog planning:
  - linked LLM summary spec in `docs/backlog.md` under `Plugin Backlog Ideas`
  - kept this feature explicitly in Deferred (not promoted to Next)
  - fixed OIDC delivery-order indentation in backlog for consistency.
- Updated architecture and agent planning docs for alignment:
  - `docs/architecture.md` now references planned summary hook and links LLM summary spec in plugin roadmap ideas
  - `AGENTS.md` deferred list now includes on-demand LLM summary as later priority
  - `AGENTS.md` feature notes now capture shared LLM capability plugin direction (summary first).
- Captured fixed planning decisions for this feature:
  - plugin-first architecture
  - async job + status flow
  - full-article content preferred when available
  - latest-only summary persistence
  - reader action + reader summary card UX with disabled-with-hint behavior when capability is unavailable.

### Verification

- Documentation/planning update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.
- Docs consistency verification command:
  - `rg -n "article-llm-summary-on-demand-v1|summarize_article|LLM summarization plugin" docs AGENTS.md`

## 2026-02-18 (Planning Update: Full Article Fetch On-Demand v1)

### Implemented This Session

- Added new planning spec for reader-triggered full article fetch:
  - `docs/specs/done/full-article-fetch-on-demand-v1.md`
  - scopes manual `Fetch full article` action from reader, persisted extracted fulltext storage, and guarded fetch
    pipeline requirements.
- Updated active backlog deferred planning:
  - added linked spec reference in `docs/backlog.md`
  - added deferred backlog item `Full Article Fetch On-Demand` as a later-priority item
  - updated suggested deferred delivery sequence to include this feature as lowest priority.
- Updated architecture deferred planning:
  - added long-term backlog section for full article fetch capability and architecture implications
  - updated deferred delivery sequence ordering accordingly.
- Updated `AGENTS.md` deferred list with this later-priority feature for cross-doc planning consistency.

### Verification

- Documentation/planning update only.
- Source-code context reviewed for current behavior:
  - ingestion currently stores feed-provided excerpt content (`src/sift/services/ingestion_service.py`)
  - reader currently renders article detail content with `Open original` action (`frontend/src/features/workspace/components/ReaderPane.tsx`)
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.

## 2026-02-18 (Planning Alignment: Backlog/Architecture/Agent Notes Consistency Pass)

### Implemented This Session

- Aligned planning documents to keep `docs/backlog.md` as the active source of truth and remove drift:
  - updated `AGENTS.md` next UI slice to match active backlog wording (workspace action iconification v1).
  - updated `docs/architecture.md` UI extension status to reflect completed monitoring visual explainability v1
    (`query_hits`, title/content spans, compact matched-term summaries).
  - updated `docs/architecture.md` monitoring-management deferred wording to remove stale "span highlighting pending"
    language now that baseline is implemented.
- Normalized deferred planning coverage in `docs/backlog.md`:
  - added explicit deferred item for `Discover feeds (Discovery streams)` to match linked spec.
  - added explicit deferred item for OIDC provider integration (Google first, then Azure/Apple) to match
    `AGENTS.md`/`docs/architecture.md`.
  - updated suggested deferred delivery sequence ordering to include discovery, plugin UI/config, and OIDC.
- Updated backlog history heading wording for clarity:
  - `docs/backlog-history.md` now uses `Archive Initiated on 2026-02-17` to avoid stale-date ambiguity.

### Verification

- Documentation/planning alignment update only.
- No backend/frontend runtime behavior changes were implemented in this session.
- No test suite execution was required for this docs-only update.

## 2026-02-18 (Monitoring Match Visual Explainability v1: Query Spans + List/Reader Term Summaries)

### Implemented This Session

- Implemented query-hit extraction for advanced monitoring expressions:
  - `ParsedSearchQuery.matched_hits(...)` now returns matched title/content tokens with offsets and operator context.
  - stream rule evidence now persists `query_hits` entries with `field`, `token`, `start`, `end`, `offset_basis`, and
    snippet text.
- Extended stream matching evidence persistence and validation coverage:
  - query-hit evidence now persists through both ingest-time matching and backfill matching.
  - added backend coverage in:
    - `tests/test_query_language.py`
    - `tests/test_stream_service.py`
    - `tests/test_stream_backfill_api.py`
- Implemented list/reader matched-term compact summaries:
  - added shared evidence summary helper in `frontend/src/features/workspace/lib/matchEvidence.ts`
  - article rows now render `Matched terms: ...` when concrete evidence hits exist.
  - reader metadata now renders `Matched terms: ...` alongside existing explainability rows.
- Implemented title/content visual explainability refinements in reader:
  - reader evidence model now consumes `query_hits` as first-class evidence rows.
  - title-field offsets are now highlighted in reader title text.
  - evidence rows show query-hit lines with content jump-to-highlight actions where applicable.
  - added/updated frontend coverage:
    - `frontend/src/features/workspace/components/ReaderPane.test.tsx`
    - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
- Updated planning/source-of-truth docs after delivery:
  - moved completed UI slice from active backlog to history (`docs/backlog.md`, `docs/backlog-history.md`)
  - synchronized architecture UI-priority section (`docs/architecture.md`)
  - updated implementation status in spec (`docs/specs/done/monitoring-match-visual-explainability-v1.md`)

### Verification

- `python -m pytest tests/test_query_language.py tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx src/features/workspace/components/ArticlesPane.test.tsx`

## 2026-02-17 (Planning Workflow Update: Active Backlog + Backlog History Split)

### Implemented This Session

- Split backlog documentation into active vs historical sources:
  - `docs/backlog.md` now contains only active remaining items (`Next`, `Deferred`).
  - created `docs/backlog-history.md` to archive completed/historical backlog content.
- Moved prior completed backlog sections into `docs/backlog-history.md`:
  - done foundations
  - completed monitoring/UI milestones
  - archived completed-session index previously kept in active backlog
- Updated project instructions in `AGENTS.md`:
  - planning workflow now reads both active backlog and backlog history
  - backlog governance now requires moving completed items to history file
  - storage guidance now explicitly distinguishes active backlog vs history archive

### Verification

- Documentation-only planning/process update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Planning Update: Monitoring Span Explainability + Action Iconification)

### Implemented This Session

- Added detailed planning spec for monitoring match visual explainability:
  - `docs/specs/done/monitoring-match-visual-explainability-v1.md`
  - scopes title/content span-level visibility for query/rule/classifier evidence
  - defines proposed `query_hits` evidence contract extension and phased implementation plan
- Added detailed planning spec for workspace action iconification:
  - `docs/specs/done/workspace-action-iconification-v1.md`
  - scopes icon-first list/reader action controls with tooltips and explicit accessibility labels
- Updated backlog next-iteration actions:
  - added both slices under `Next UI Slice` planned actions in `docs/backlog.md`
  - linked both new specs in backlog linked-spec references
  - clarified deferred monitoring v2 note to reference new next-iteration span explainability scope

### Verification

- Documentation-only planning update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Monitoring Explainability: Rich Classifier Findings)

### Implemented This Session

- Extended classifier plugin decision contract with structured findings:
  - `StreamClassificationDecision.findings` now accepts a list of finding objects.
- Upgraded built-in classifier plugin evidence output:
  - keyword heuristic classifier now emits finding rows with label/snippet/score
  - when available, findings include field offsets for UI highlight mapping
- Extended stream matching evidence persistence:
  - classifier evidence now stores normalized `findings` blocks
  - classifier reason fallback now uses first finding summary when explicit reason is absent
  - classifier snippets are derived from findings for backward-compatible rendering
- Upgraded reader explainability rendering:
  - match evidence summary now includes classifier finding counts and first finding details
  - evidence panel now renders classifier findings as first-class rows
  - findings with `field=content_text` + offsets support jump-to-highlight actions
- Added/updated tests:
  - `tests/test_stream_service.py` (classifier finding evidence assertions)
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx` (classifier findings summary + evidence row rendering)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

## 2026-02-17 (Classifier Run Persistence + Model/Version Tracking Baseline)

### Implemented This Session

- Added classifier run persistence model and migration:
  - migration: `alembic/versions/20260217_0013_stream_classifier_runs.py`
  - model: `stream_classifier_runs` in `src/sift/db/models.py`
- Extended classifier plugin decision contract with tracking metadata:
  - `provider`, `model_name`, `model_version` in `StreamClassificationDecision`
  - built-in keyword heuristic classifier now emits baseline model metadata
- Extended stream matching execution path:
  - stream service now captures classifier run decisions (match status, confidence, threshold, duration, metadata)
  - ingest flow persists classifier runs for classifier-enabled streams
  - stream backfill flow persists classifier runs for classifier-enabled streams
- Added stream diagnostics API endpoint:
  - `GET /api/v1/streams/{stream_id}/classifier-runs`
  - returns recent classifier runs for the user-owned stream
- Added/updated tests:
  - `tests/test_stream_service.py` (classifier run capture + persistence coverage)
  - `tests/test_stream_classifier_runs_api.py` (new endpoint coverage)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_stream_classifier_runs_api.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`

## 2026-02-17 (Planning Update: Silent Feeds for Monitoring-Only Population)

### Implemented This Session

- Added new planning spec: `docs/specs/silent-feeds-v1.md`.
- Scoped `silent` feed mode semantics:
  - silent feeds keep normal ingestion and monitoring stream matching behavior
  - new ingested articles from silent feeds are auto-marked read
  - switching a feed to silent bulk-marks existing unread for that feed as read
  - unsilencing stops future auto-read but does not revert historical read states
- Updated planning docs for backlog/architecture alignment:
  - added linked spec and deferred backlog item (placed as lowest priority) in `docs/backlog.md`
  - added deferred architecture section for silent feed model/API/pipeline implications in `docs/architecture.md`

### Verification

- Documentation-only planning update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Planning Update: Discovery Providers + Free-Tier Rate Limits)

### Implemented This Session

- Extended `Discover feeds v1` planning spec with provider strategy details:
  - default provider chain guidance (`searxng` primary + managed fallback)
  - optional adapter notes for constrained/legacy providers
- Added planned discovery execution flow:
  - query variant compilation
  - provider search execution
  - staged feed endpoint resolution (direct parse, HTML autodiscovery, constrained heuristics)
  - validation, dedupe, and source attribution behavior
- Added explicit free-tier protection planning:
  - per-provider budget/rate-limit controls (`max_requests_per_run`, `max_requests_per_day`, request spacing, and
    query/result caps)
  - partial-result warning behavior when budget exhaustion occurs
- Updated related planning docs for consistency:
  - `docs/specs/plugin-configuration-registry-v1.md`
  - `docs/architecture.md`
  - `docs/backlog.md`

### Verification

- Documentation-only planning update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Planning Alignment: Discover Feeds + Discovery Streams)

### Implemented This Session

- Updated planning/docs direction from saved-driven recommendations to stream-driven discovery:
  - locked user-facing naming: `Discover feeds` + `Discovery streams`
  - locked v1 model as separate discovery domain (not monitoring stream reuse)
- Captured discovery architecture decisions across docs:
  - separate `discovery_streams` from monitoring `keyword_streams`
  - per-stream manual generation workflow
  - recommendation dedupe by normalized URL with source-stream attribution
- Captured recommendation decision semantics for v1:
  - statuses include `pending`, `accepted`, `denied`, `resolved_existing`
  - denied URLs are suppressed until manual reset
  - already subscribed feed URLs are auto-resolved as `resolved_existing`
- Captured product/UX boundary:
  - optional copy-from-monitoring convenience into discovery stream criteria
  - no saved/starred article seed usage in v1
- Updated linked specs and plugin naming examples to use `Discover feeds` / `discover_feeds`.

### Verification

- Documentation-only alignment pass.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update (optional markdown checks may be run separately).

## 2026-02-16 (Workspace UX: Help in Rail + Scope-Aware Mark Read)

### Implemented This Session

- Added Help entry directly in the left workspace rail (`/app`) for fast discoverability.
- Added backend scope-aware read action endpoint:
  - `POST /api/v1/articles/state/mark-scope-read`
  - marks all matching articles as read based on current scope/state/query filters
- Added service method `mark_scope_as_read(...)` in article service to evaluate full scope filters (including advanced query syntax) before bulk state update.
- Updated workspace list action copy and behavior:
  - button now reads `Mark all in scope as read`
  - action prompts user confirmation before execution
  - no longer limited to currently visible rows
- Added/updated tests:
  - `tests/test_article_service.py`
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/hooks/useWorkspaceShortcuts.test.tsx`

### Verification

- `python -m pytest tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx src/features/workspace/hooks/useWorkspaceShortcuts.test.tsx`

## 2026-02-16 (Help Page: Monitoring Setup + Search Syntax Reference)

### Implemented This Session

- Added authenticated help route: `/help`.
- Added new help page UI focused on:
  - configuring monitoring feeds step-by-step
  - search query syntax (`AND`, `OR`, `NOT`, grouping, quotes, wildcard, fuzzy)
  - regex/include/exclude behavior guidance
- Added help entry links:
  - from settings (`/account`)
  - from monitoring feed management (`/account/monitoring`)
- Added frontend tests:
  - `frontend/src/features/help/routes/HelpPage.test.tsx`
  - updated `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - updated `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/help/routes/HelpPage.test.tsx src/features/auth/routes/AccountPage.test.tsx src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

## 2026-02-16 (Workspace UI Touch-Up: Mark All Read + Remove Stale Magic Copy)

### Implemented This Session

- Added bulk article state wiring in frontend API/hooks:
  - `bulkPatchArticleState` client call to `POST /api/v1/articles/state/bulk`
  - `useBulkPatchArticleStateMutation` for workspace usage
- Added `Mark all as read` action in article list pane:
  - action targets unread articles currently loaded in the list
  - disabled when there are no unread items or mutation is in progress
- Removed stale “Magic sorting” banner copy from article list pane because that feature text was not aligned with current UI behavior.
- Updated article list pane tests for the new bulk action behavior.

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx`

### Notes

- Current list fetch is capped to the active list window (default 50), so `Mark all as read` applies to unread articles currently loaded in the pane.

## 2026-02-16 (Monitoring Management v2: Offset-Aware Highlighting + Evidence Panel)

### Implemented This Session

- Extended stream evidence payloads with explicit offset metadata marker:
  - rule hits now include `offset_basis: field_text_v1`
- Extended classifier evidence payloads with snippet-ready structure:
  - classifier reason now also emits `snippets: [{ text: ... }]`
- Upgraded reader highlighting from term-only to offset-aware rendering:
  - uses `field=content_text` + `start/end` offsets to apply precise `<mark>` ranges in reader body
  - preserves term-based fallback when offset mapping cannot be applied
- Added reader evidence panel with per-stream details:
  - keyword/regex hit rows with snippets
  - classifier rows/snippets
  - `Jump to highlight` actions for rows mapped to rendered highlight anchors
- Updated UI styling for evidence panel and highlight affordances.
- Added frontend test coverage for evidence jump behavior and maintained highlight toggle coverage.

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `python -m ruff check src tests`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

### Notes

- Offset mapping is now primary for body highlighting; fallback term highlighting remains in place for resilience.
- Remaining explainability follow-up is exposing richer plugin finding structures from plugin implementations (beyond classifier reason snippets).

## 2026-02-16 (Monitoring Management v2: Reader Inline Match Highlighting)

### Implemented This Session

- Added inline reader-body highlighting for monitoring match evidence terms.
- Highlight extraction now uses structured match evidence values (keyword and regex matched values).
- Added reader action toggle:
  - `Hide highlights` / `Show highlights`
  - toggle is shown when match evidence terms are available for the selected article
- Added highlight styling token/class:
  - `.workspace-reader__highlight`
- Added frontend coverage for highlight rendering and toggle behavior:
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

### Notes

- Highlighting is DOM-based and preserves existing sanitized reader markup.
- This is an iteration-1 implementation focused on evidence values; future refinement can add precise offset-aware highlighting.

## 2026-02-16 (Monitoring Management v2: Structured Match Evidence + Reader Details)

### Implemented This Session

- Added persisted structured evidence payload for stream matches:
  - migration: `alembic/versions/20260216_0012_stream_match_evidence.py`
  - model field: `keyword_stream_matches.match_evidence_json`
- Extended stream matching to produce structured rule/classifier evidence:
  - keyword and regex hit records now include field, offsets, and snippets
  - classifier matches now capture plugin, confidence/threshold, and reason
  - hybrid mode now stores combined rules/classifier evidence payloads
- Extended backend API outputs with evidence:
  - `StreamArticleOut.match_evidence`
  - `ArticleListItemOut.stream_match_evidence`
  - `ArticleDetailOut.stream_match_evidence`
- Extended article service stream mapping to parse and return per-stream evidence payloads.
- Updated reader explainability rendering:
  - preserved `Why matched` textual reason summaries
  - added `Match evidence` summaries with keyword/regex snippet context and classifier details
- Added/updated tests:
  - `tests/test_stream_service.py`
  - `tests/test_stream_backfill_api.py`
  - `tests/test_article_service.py`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

### Notes

- Monitoring explainability now persists machine-readable evidence suitable for future UI highlight rendering.
- Remaining monitoring v2 enhancement area is article-content level inline highlighting (actual span markup), not just textual evidence summaries.

## 2026-02-16 (Monitoring Management v2: Plugin Matcher Config Baseline)

### Implemented This Session

- Added persisted classifier config for monitoring streams:
  - migration: `alembic/versions/20260216_0011_stream_classifier_config.py`
  - model field: `keyword_streams.classifier_config_json`
- Extended stream schemas with `classifier_config` for create/update/out payloads.
- Added backend classifier config validation in stream service:
  - must be a JSON object
  - must be JSON-serializable
  - bounded payload size (max 5000 chars serialized)
- Extended classifier execution context (`StreamClassifierContext`) to include `classifier_config`.
- Updated built-in heuristic classifier plugin to honor optional config flags:
  - `require_all_include_keywords`
  - `min_keyword_ratio`
- Updated monitoring UI to edit classifier config JSON and validate JSON pre-submit.
- Updated tests:
  - `tests/test_stream_service.py` (config persistence and classifier-context usage)
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx` (config payload wiring)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Notes

- This completes plugin matcher config wiring for monitoring v2.
- Remaining v2 scope is deeper explainability rendering (matched spans/snippets).

## 2026-02-16 (Monitoring Management v2: Explainability Baseline)

### Implemented This Session

- Added persisted match-reason evidence for monitoring stream matches:
  - migration: `alembic/versions/20260216_0010_stream_match_reason.py`
  - model field: `keyword_stream_matches.match_reason`
- Extended stream matching flow to produce reason summaries for matches:
  - query/keyword/regex/source/language/classifier reasons
  - ingestion and backfill now persist match reasons per stream/article match row
- Extended article APIs to return stream match reason mappings:
  - `ArticleListItemOut.stream_match_reasons`
  - `ArticleDetailOut.stream_match_reasons`
- Extended stream article payloads with `match_reason` in `StreamArticleOut`.
- Updated workspace explainability rendering:
  - article rows render `Why matched` summaries when reason evidence exists
  - reader pane renders per-stream reason summaries
- Added/updated tests:
  - `tests/test_stream_service.py`
  - `tests/test_stream_backfill_api.py`
  - `tests/test_article_service.py`
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx src/features/workspace/components/ReaderPane.test.tsx src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Notes

- This completes a textual explainability baseline for monitoring matches.
- Remaining v2 explainability scope is keyword/regex span highlighting and plugin snippet rendering.

## 2026-02-16 (Monitoring Management v2: Regex Matcher Baseline)

### Implemented This Session

- Added regex matcher fields for monitoring streams:
  - migration: `alembic/versions/20260216_0009_stream_regex_fields.py`
  - persisted columns: `keyword_streams.include_regex_json`, `keyword_streams.exclude_regex_json`
- Extended stream schemas and stream CRUD payloads with regex rule lists (`include_regex`, `exclude_regex`).
- Extended stream matching engine:
  - include regex rules require at least one regex hit in article title/content
  - exclude regex rules reject article matches when regex patterns hit title/content
  - regex patterns are validated on stream create/update with explicit validation errors for invalid patterns
- Updated monitoring UI editor to support include/exclude regex rules and persist them via stream APIs.
- Updated monitoring stream cards to display configured regex rules.
- Added/updated tests:
  - `tests/test_stream_service.py` (regex matching and regex validation coverage)
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx` (regex payload wiring)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `pnpm --dir frontend run test -- src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`

### Notes

- Monitoring management v2 now has:
  - historical backfill execution baseline
  - regex matcher expansion baseline
- Remaining v2 scope is plugin matcher expansion and richer explainability rendering.

## 2026-02-16 (Monitoring Management v2 Baseline: Backfill Execution)

### Implemented This Session

- Added backend stream backfill endpoint: `POST /api/v1/streams/{stream_id}/backfill`.
- Added stream backfill service flow:
  - scan existing user-owned articles
  - recompute stream match membership using current stream rules/query/classifier mode
  - replace stale `keyword_stream_matches` rows for the stream with recomputed results
  - return execution counts (`scanned_count`, `previous_match_count`, `matched_count`)
- Added API coverage: `tests/test_stream_backfill_api.py`.
- Added service coverage for replacement behavior: `tests/test_stream_service.py`.
- Updated monitoring UI backfill feedback:
  - success message now shows concrete counts (`matched` vs `scanned`)
  - existing explicit unavailable-state handling for legacy/non-upgraded backends is preserved
- Updated frontend typing/API client for backfill response payload shape.

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `pnpm --dir frontend run test -- src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`
- `python -m ruff check src tests`
- `python -m mypy src`

### Notes

- This completes the historical backfill execution baseline for monitoring management v2.
- Remaining v2 scope is regex/plugin matcher expansion and richer explainability rendering.

## 2026-02-16 (Monitoring Search Language v1 Slice Implemented)

### Implemented This Session

- Added backend monitoring/article search language module: `src/sift/search/query_language.py`.
- Added query-language syntax support:
  - boolean operators: `AND`, `OR`, `NOT` (case-insensitive)
  - grouping with parentheses
  - quoted phrases
  - suffix wildcard (`term*`)
  - fuzzy tokens (`term~1`, `term~2`)
- Added stream persistence for query expressions:
  - migration: `alembic/versions/20260216_0008_stream_match_query.py`
  - model/schema support for `keyword_streams.match_query`
- Integrated query parsing/validation into stream create/update and ingest-time stream matching.
- Integrated advanced query handling in article listing search with clear 400-level validation failures for invalid syntax.
- Added monitoring UI support for editing `Search query (v1)` in `/account/monitoring`.
- Added/updated tests:
  - `tests/test_query_language.py`
  - `tests/test_stream_service.py`
  - `tests/test_article_service.py`
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Verification

- `python -m pytest tests/test_query_language.py tests/test_stream_service.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- --run`
- `pnpm --dir frontend run build`

### Notes

- PostgreSQL acceleration for advanced query filtering is intentionally deferred to a follow-up optimization slice.

## 2026-02-16 (Planning: Monitoring Search Language v1 Sketched)

### Planning Update

- Added a new prioritized backlog item for a monitoring search language v1 using boolean operators.
- Captured initial syntax/behavior sketch in `docs/backlog.md`:
  - operators: `AND`, `OR`, `NOT`
  - grouping with parentheses
  - quoted phrase support
  - operator precedence (`NOT` > `AND` > `OR`)
- Captured implementation outline:
  - backend parser/validator + clear syntax errors
  - expression persistence on monitoring definitions
  - ingest-time evaluation for stream matching
  - monitoring UI editor input + validation feedback
- Marked advanced matcher composition (regex/plugin combinations) as deferred v2 scope.

## 2026-02-16 (Monitoring Feed Management v1 Slice Implemented)

### Implemented This Session

- Added stream-backed monitoring management route: `/account/monitoring`.
- Added monitoring management frontend data layer:
  - stream API client module (`GET/POST/PATCH/DELETE /api/v1/streams`)
  - optional backfill trigger entry point (`POST /api/v1/streams/{stream_id}/backfill`) with explicit unavailable-state UX
  - React Query hooks for list/create/update/delete/backfill operations
- Added settings entry point:
  - `Manage monitoring feeds` action on `/account`
- Added monitoring management UX:
  - create/edit/delete/toggle-active monitoring definitions
  - classifier mode/plugin/confidence controls
  - keyword/source/language criteria editing
  - user feedback banners for success/error/info outcomes
- Added explainability affordances in workspace:
  - article list rows show matched monitoring stream labels
  - reader header shows matched monitoring stream labels
- Added and updated tests:
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`
  - `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- --run`
- `pnpm --dir frontend run build`

## 2026-02-16 (Backlog Source-of-Truth Consolidation)

### Implemented This Session

- Added `docs/backlog.md` as the canonical backlog source of truth.
- Consolidated backlog state into explicit status buckets:
  - `Done` (historical completed work)
  - `Next` (current prioritized items)
  - `Deferred` (future backlog)
- Added references in `AGENTS.md` so future sessions read/update `docs/backlog.md` during planning.

### Notes

- Detailed long-term backlog content was migrated from this file to `docs/backlog.md` to avoid drift.

## 2026-02-16 (Project/UI Plan Review + Monitoring Management Prioritized)

### Planning Review (UI)

- Confirmed completed UI improvements in the current plan:
  - reader-first `/app` shell with 3-pane responsive behavior
  - folder/feed navigation IA and folder management flows
  - topbar quick theme toggle + settings entry point
  - unified `/account` settings hub (`themeMode`, `themePreset`, `density`, `navPreset`)
  - preset-aware theming across rail/nav/list/reader (light + dark)
  - settings accessibility hardening (group semantics, keyboard support, focus-visible states)
  - reset-to-defaults action and settings route test coverage
  - monitoring section placement/expand-collapse behavior in navigation

### Priority Update

- Promoted monitoring feed definition management to the next prioritized UI slice.
- Kept the core platform sequence unchanged:
  1. stream-level ranking/prioritization
  2. classifier run persistence/model tracking
  3. vector-database plugin integration
  4. scheduler/ingestion observability

### Next Step (UI Slice Scope)

1. Define route + information architecture for monitoring definition CRUD.
2. Add explainability affordances in list/reader for match reasons.
3. Add optional historical backfill trigger in the management flow.

## 2026-02-16 (Theme Consistency Follow-Up + Planning Alignment)

### Implemented This Session

- Completed final preset consistency follow-up for remaining non-themed surfaces:
  - expanded preset-specific base surface tokens (`bg`, `surface`, `surface-soft`, `surface-muted`, `text`, `muted`, `border`)
  - aligned MUI palette per preset/mode (`background`, `text`, `divider`, and `action` tokens) so controls match pane theme
- Aligned planning docs (`AGENTS.md`, `docs/architecture.md`) to remove stale deferred UI-polish items that are now complete.
- Set the next UI-focused deferred slice explicitly to monitoring feed definition management UX/API.

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- --run`
- `pnpm --dir frontend run build`

### Next Step (UI)

1. Start monitoring feed definition management slice:
   - define route + IA for monitoring definition CRUD
   - add explainability affordances in list/reader for why an article matched
   - wire optional backfill trigger entry point in the management flow

## 2026-02-16 (UI Extensions Completed: Preset Consistency + Contrast + Settings UX)

### Implemented This Session

- Completed the planned UI extension pass across workspace and settings:
  1. Visual consistency per preset
     - expanded preset-aware visual tokens across workspace panes (rail/nav/list/reader)
     - unified topbar/nav/list/reader surface tints using accent-aware tokenized gradients
  2. Contrast/interaction tuning per preset
     - improved preset-sensitive hover/selected interaction states and rail action states
     - moved focus ring to accent-derived token so each preset has coherent focus color behavior
     - tuned interaction/background tokens for both light and dark preset variants
  3. Settings UX accessibility/responsive polish
     - added `Reset to defaults` action for UI preferences
     - strengthened grouped settings semantics and keyboard operation support (arrows + home/end)
     - improved mobile behavior for settings controls (full-width reset and toggle layout)

- Added/expanded settings route tests:
  - `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - validates accessible settings structure, persistence, reset behavior, and keyboard navigation

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

## 2026-02-16 (UI Polish + Settings Accessibility + Route Tests)

### Implemented This Session

- Completed preset-by-preset interaction polish across workspace surfaces:
  - introduced semantic interaction tokens for hover/selected states, list banners, reader callouts/code blocks
  - made rail gradient and rail interaction states preset-aware (Classic/Ocean/Graphite/Sand in light+dark)
  - removed stale navigation-preset toolbar CSS that is no longer used
- Improved settings accessibility and keyboard behavior on `/account`:
  - upgraded settings controls to semantic `fieldset`/`legend` groups
  - added helper text for keyboard operation
  - implemented arrow/home/end keyboard selection handling for toggle groups
  - improved focus-visible and selected-state styling for settings toggle controls
- Added targeted settings route tests for interaction and persistence:
  - `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - validates accessible settings sections/labels
  - validates persisted unified preferences and legacy key synchronization
  - validates keyboard arrow selection behavior for theme mode group

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

## 2026-02-16 (UI Settings Hub Slice Implemented)

### Implemented This Session

- Implemented unified frontend UI preferences model in `frontend/src/app/uiPreferences.ts`:
  - persisted model: `themeMode`, `themePreset`, `density`, `navPreset`
  - migration-friendly read path from legacy keys
  - synchronized writes to unified + legacy keys for backward compatibility
- Updated app providers and theme wiring:
  - `AppProviders` now stores and exposes unified UI preferences state
  - theme factory now supports `(themeMode, themePreset)`
  - document theme attributes now include both mode and preset
- Expanded `/account` into a settings hub:
  - Appearance controls: theme mode + theme preset
  - Reading/Layout controls: density + nav preset
  - Account section retains identity summary
- Removed duplicate inline display controls from workspace navigation:
  - nav preset selection removed from `NavigationPane`
  - navigation visual preset now flows from app settings state
- Added curated preset token variants in CSS for light/dark presentation tuning:
  - Sift Classic, Ocean Slate, Graphite Violet, Warm Sand
- Added/updated frontend tests:
  - `frontend/src/app/uiPreferences.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

## 2026-02-16 (Reprioritization Update)

### Priority Update

- Reprioritized active work to make the UI settings-hub vertical slice priority #1.
- Updated `AGENTS.md`, `docs/architecture.md`, and `docs/session-notes.md` to use the same ordering.
- Kept OIDC deferred and reframed deferred UI work to post-foundation preset/polish expansion.

## 2026-02-16

### Planning Alignment Audit

- Aligned planning language across `AGENTS.md`, `docs/architecture.md`, and `docs/session-notes.md`.
- Confirmed one canonical current core priority sequence:
  1. stream-level ranking/prioritization
  2. classifier run persistence/model tracking
  3. vector-database plugin integration
  4. scheduler/ingestion observability
- Validated runtime baseline stabilization items as complete:
  - scheduler job-id delimiter compatibility (`ingest-<feed_id>`, legacy `ingest:<feed_id>` lookup)
  - dev seed idempotent behavior for feeds/folders/monitoring streams
- Moved OIDC planning consistently into deferred scope.
- Frontend settings/theme sprint planning from this audit is superseded by the reprioritization update above.

### Verification

- Cross-doc planning sections checked via ripgrep for:
  - `Next Delivery Sequence`
  - `Current Priority Plan`
  - `Planned Next Moves`
  - `Deferred Delivery Sequence`
  - `Next UI Sprint`
- Runtime baseline checks:
  - `python -m pytest tests/test_scheduler.py tests/test_dev_seed_service.py`

## 2026-02-15

### Architecture Baseline (Current)

- Backend is API-only FastAPI (`/api/v1/*`) and does not serve frontend pages or static bundles.
- Frontend is a standalone React + TypeScript app in `frontend/`.
- Frontend routes (`/app`, `/login`, `/register`, `/account`) are owned by the SPA runtime.
- Frontend/backend integration is API-only via REST endpoints.

### Implemented This Session

- Removed backend web delivery package and route surface (`src/sift/web/*`).
- Added CORS configuration in backend settings and middleware wiring in `src/sift/main.py`.
- Added API-only regression test: `tests/test_api_only_surface.py`.
- Set frontend build output to `frontend/dist`.
- Added frontend API base URL support through `VITE_API_BASE_URL`.
- Standardized docs (`AGENTS.md`, architecture, getting-started, development, deployment) to the API-only + standalone SPA model.
- Updated Dev Container stack to include frontend service and default port `5173`.
- Updated root `docker-compose.yml` to start full local stack including frontend dev server (`http://localhost:5173`).

### Verification

- Frontend:
  - `pnpm --dir frontend run gen:openapi`
  - `pnpm --dir frontend run lint`
  - `pnpm --dir frontend run typecheck`
  - `pnpm --dir frontend run test`
  - `pnpm --dir frontend run build`
- Backend:
  - `python -m ruff check src tests`
  - `python -m mypy src`
  - `python -m pytest`

### Current Priority Plan

1. Add stream-level ranking and prioritization controls.
2. Add classifier run persistence and model/version tracking.
3. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
4. Add scheduler and ingestion observability (metrics, latency, failures) after core content features.

### Deferred

1. External OIDC provider integration (Google first, then Azure/Apple).
2. UI preset/consistency extension work completed on 2026-02-16; next deferred UI slice is monitoring feed
   definition management.

### Workspace UI Slice: Folder + Reader v1

- Refactored `/app` to a light, compact reader-first shell:
  - fixed app rail
  - hierarchical navigation pane
  - compact article list
  - persistent reader pane
- Removed dashboard cards from the `/app` workspace route.
- Added hierarchical navigation view model mapping in `frontend/src/entities/navigation/model.ts`:
  - system, folder, feed, and stream scope mapping
  - unified scope label resolution for current URL scope
- Added folder management and feed assignment flows using existing APIs:
  - create/rename/delete folder
  - move feed to folder / unfiled
  - query invalidation for navigation, folders, feeds, and articles
- Reworked article list rows for compact dense rendering with unread/saved indicators and metadata.
- Reworked reader pane with core actions (`read`, `save`, `open original`, `prev`, `next`).
- Added responsive behavior updates:
  - desktop: fixed 3-pane layout
  - tablet/mobile: collapsible navigation drawer from rail action
  - mobile: progressive list/reader panel flow with back-to-list action
- Added/updated frontend tests:
  - navigation hierarchy mapping
  - folder DTO/validation shaping
  - compact article row rendering
  - reader action wiring

### Verification (Workspace Slice)

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`
- `python -m pytest tests/test_article_state_api.py tests/test_article_service.py`

### Workspace UI Modernization + Reader Formatting

- Implemented editorial-light workspace polish for `/app`:
  - updated visual tokens and spacing hierarchy for rail/nav/list/reader panes
  - improved hover/active/focus states and compact readability
  - replaced rail glyph labels with MUI icons for clearer affordances
- Implemented safe reader content rendering:
  - added `frontend/src/features/workspace/lib/readerContent.ts`
  - sanitized article markup using DOMPurify with allowlisted semantic tags
  - normalized rendered links with safe `target`/`rel` attributes
  - converted plaintext payloads into paragraph-based HTML fallback
- Updated reader component contract:
  - `ReaderPane` now renders preprocessed sanitized HTML body content
  - kept existing reader action behavior (`read/save/open/prev/next`)
- Added tests for sanitizer and reader behavior:
  - `frontend/src/features/workspace/lib/readerContent.test.ts`
  - expanded `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Workspace Nav/Visual Polish v2

- Implemented reliable folder interaction split in navigation:
  - row click now selects folder scope only
  - chevron click toggles expansion only (single-click behavior)
- Added folder controls:
  - `Expand all`
  - `Collapse all`
  - folder expansion state persisted in localStorage (`NAV_FOLDERS_EXPANDED_KEY`)
- Added feed icons in folder/feed tree:
  - favicon URL derived from feed `site_url` or `url`
  - graceful fallback to deterministic initial avatar if favicon load fails
- Applied softer visual tuning in workspace styles:
  - lower-contrast borders/backgrounds
  - calmer selected/hover states
  - improved nav/feed row softness and spacing
- Added/updated tests:
  - `frontend/src/features/workspace/lib/feedIcons.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Workspace Nav IA + Readability Polish v3

- Navigation IA updates:
  - moved `Monitoring feeds` to a standalone section above `Folders`
  - kept stream routing semantics unchanged (`scope_type="stream"`)
  - added section-level monitoring collapse/expand toggle with persisted browser-local state
- Density and icon polish:
  - reduced feed icon scale (compact-first)
  - reduced nav row/action visual weight and tightened row spacing
  - kept favicon fallback behavior for feed icons
- Reader readability updates:
  - adopted paper-editorial default in light mode (warm paper background + dark neutral text)
  - switched frontend typography defaults to `IBM Plex Sans` (UI) and `Source Serif 4` (reader body)
  - tuned reader line length, line-height, and paragraph rhythm for long-form scanning
- Added/updated tests:
  - `frontend/src/entities/navigation/model.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Workspace UX Polish v4

- Added desktop pane resizing across both split boundaries:
  - navigation ↔ article list
  - article list ↔ reader
  - widths persisted in browser-local storage (`PANE_LAYOUT_KEY`)
- Added keyboard-accessible separators (`role="separator"`) with arrow/home/end controls.
- Updated monitoring header control from subtle icon-only toggle to visible labeled action (`Collapse` / `Expand`).
- Added slim workspace top bar with icon controls for:
  - dark/light mode toggle
  - settings navigation (`/account`)
- Removed density control from navigation/feed pane toolbar (to live on settings page later).
- Updated reader mark-read behavior:
  - when toggling unread -> read, selection now auto-advances to next article after mutation success
  - mark-unread does not auto-advance
- Stability improvement:
  - selected article id now falls back to first visible row when current id no longer exists in filtered results.
- Added/updated tests:
  - `frontend/src/features/workspace/lib/paneLayout.test.ts`
  - `frontend/src/features/workspace/hooks/usePaneResizing.test.tsx`
  - `frontend/src/features/workspace/lib/readActions.test.ts`
  - `frontend/src/entities/article/model.test.ts`
  - updated `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Frontend Planning Backlog (Paused)

- Session paused by user after theme/navigation polish on branch `feat/folder-nav-polish`.
- Resume plan for the next UI pass:
  1. Stabilize visual defaults:
     - keep `balanced` as default nav preset
     - keep `tight`/`airy` as optional variants, move the settings for this to a settings menu
  2. Folder panel final pass:
     - finalize row height, indent depth, and unread-count contrast values
     - verify truncation and menu discoverability at narrower widths
  3. Nav + list visual harmony:
     - align article list hover/selected/read states with softened pistachio light theme
     - keep reader pane styling unchanged
  4. Settings consolidation:
     - move display controls (nav preset/theme/density) into settings surface
     - keep quick theme toggle in top bar
  5. Wrap-up and merge readiness:
     - rerun `lint`, `typecheck`, `test`, `build`
     - open PR from `feat/folder-nav-polish` when approved

### UI Sprint: Settings Hub + Theme Presets (Completed Foundation Slice)

- Goal: complete a sleek, modern UI pass by centralizing preferences and shipping multiple prebuilt visual themes.
- Foundation slice outcome:
  1. Added multi-preset theme system with curated presets.
  2. Expanded `/account` into a settings hub for UI preferences.
  3. Removed duplicate workspace navigation display controls after settings migration.
  4. Added preset-aware theme tokens for coherent rail/nav/list/reader styling.

#### Delivered Vertical Slice

1. Theme model and persistence
   - Extended frontend UI state with `themePreset` and setter.
   - Added unified preference storage with backward-compatible legacy migration/synchronization.
   - Updated theme factory to accept both `themeMode` and `themePreset`.
2. Settings hub structure
   - Expand account/settings route into sectioned settings UI:
     - Appearance (theme mode + preset)
     - Reading/Layout (density and related display controls)
     - Account (existing identity summary)
3. Workspace cleanup
   - Kept topbar settings entry point and quick theme toggle.
   - Removed duplicated inline nav preset controls from workspace navigation.
4. Token-driven polish
   - Implemented semantic color/surface token contract for presets.
   - Updated shell surfaces to consume preset-aware tokens in light/dark.

#### Candidate Presets (Initial)

- Sift Classic (current green-forward baseline)
- Ocean Slate (cool blue/cyan accent)
- Graphite Violet (dark-forward premium)
- Warm Sand (light neutral with warm accent)

#### Verification (Completed)

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

#### Next Priorities (UI Extensions, Completed 2026-02-16)

1. Perform deeper visual consistency pass across workspace panes per preset. (Completed)
2. Validate and tune contrast/interaction states for each preset in both theme modes. (Completed)
3. Expand settings UX with stronger accessibility affordances and responsive layout polish. (Completed)

### Backlog Reference

- Backlog source of truth is maintained in `docs/backlog.md`.
- This file remains the chronological session log only.


