# Sift Architecture

## Architectural Style

MVP uses a modular monolith backend with explicit boundaries:

1. Ingestion (fetch + parse + normalize)
2. Deduplication + filtering
3. Plugin pipeline
4. API delivery and frontend integration contracts

This keeps deployment simple while preserving clean seams for future service extraction.

## Runtime Components

**Current**

1. `app`: FastAPI API-only runtime (`/api/v1/*`).
2. `worker`: RQ worker for ingest jobs (`src/sift/tasks/worker.py`).
3. `scheduler`: periodic feed polling and job enqueue loop (`src/sift/tasks/scheduler.py`).
4. `db`: PostgreSQL (SQLite default for local bootstrap).
5. `redis`: queue broker.
6. `frontend`: standalone SPA runtime (Vite dev server in local dev, static host/CDN in deployment).

## Frontend Architecture

**Current**

- Frontend is a standalone React + TypeScript SPA in `frontend/` (Vite + MUI + TanStack Router/Query).
- Frontend owns routes (`/app`, `/login`, `/register`, `/account`) and is deployed independently from FastAPI.
- Backend no longer serves UI pages/static frontend bundles from `src/sift`.
- Integration with backend is API-only via `/api/v1/*`.

Reader UX target is a modern, responsive React workspace built with MUI components:

1. Left navigation pane:
   - system scopes (All, Fresh, Saved, Archived, Recently read)
   - monitoring feeds section (stream scopes) above regular folders
   - user folders with feed children and unread counts
   - compact feed icons and density-aware row sizing
2. Center list pane:
   - scoped article listing with search/state/sort controls
   - desktop resizable split with persisted pane widths
   - slim top utility bar for workspace-level controls (theme/settings)
   - responsive density and layout behavior across breakpoints
   - row-level read/save actions
3. Right reader pane:
   - article detail view and open-original action
   - mark-read auto-advance to next article when transitioning unread -> read
   - sanitized rich HTML rendering pipeline for article body content (DOMPurify-based allowlist)
   - paper-editorial default reading surface in light mode (warm background + serif body typography)

Routing and data model:

1. Route state is URL-driven (`scope_type`, `scope_id`, `state`, `sort`, `q`, pagination).
2. TanStack Router defines typed route/search-param boundaries for `/app`.
3. TanStack Query manages API server-state caching, mutations, and invalidation.
4. UI-only preferences are persisted as a unified local model:
   - `themeMode` (`light`/`dark`)
   - `themePreset` (curated preset id)
   - `density` (`compact`/`comfortable`)
   - `navPreset` (`tight`/`balanced`/`airy`)
5. Keyboard shortcuts remain a first-class UX feature (`j/k`, `o`, `m`, `s`, `/`).
6. Reader rendering rule: frontend never trusts feed markup directly; article body is sanitized and link-normalized
   before rendering.

## Frontend Plugin Surface (Minimal Extension Registry)

React + MUI cutover should expose a narrow, typed plugin registry for UI customization without coupling plugin code to
internal state layout. The host app owns routing, data-fetch orchestration, auth checks, and error boundaries.

### Shared registration contract

Every frontend extension point registers items using a common base shape plus point-specific fields:

- `id: string` (globally unique and stable; recommended namespace `plugin_name.feature_name`)
- `title: string` (human-readable label used in UI and diagnostics)
- `mount: React.ComponentType<Props>` (render entry component for this extension point)
- `capabilities: { ... }` (boolean feature flags declared by plugin and validated by host)

Host-side validation requirements:

1. Unknown capability flags are ignored and logged at debug level.
2. Duplicate `id` registrations are rejected deterministically (first registration wins, later registrations disabled).
3. Invalid registrations (missing required keys) are skipped and surfaced in diagnostics.

Failure isolation baseline for all extension points:

1. Each mounted plugin runs inside a per-item error boundary.
2. Runtime exceptions disable only the failing plugin item; the rest of the page remains interactive.
3. The host renders a compact fallback placeholder (`Plugin unavailable`) and logs structured telemetry with `plugin_id`,
   extension point, and error metadata.

### 1) `nav_badge_provider`

Purpose: augment navigation labels/counts (for example, custom unread counters or status chips) for built-in nav nodes.

Registration shape:

- Base fields (`id`, `title`, `mount`, `capabilities`)
- `targetScopes: Array<"system" | "folder" | "feed" | "stream">`
- `capabilities` flags:
  - `supportsCountOverride` (replace default count)
  - `supportsLabelSuffix` (append extra label text)

Data dependencies:

- Primary: `GET /api/v1/navigation`
- Optional plugin-owned fetches (if needed) must be read-only and scoped to currently visible nav entities.

Permission/auth constraints:

- Runs only for authenticated sessions.
- Plugin receives only user-scoped nav entities already returned by the API; no cross-user identifiers are exposed.

Failure isolation behavior:

- On plugin failure, host falls back to core nav label/count rendering for affected nodes.

### 2) `article_row_action`

Purpose: add row-level actions in the article list (for example, send to external workflow, quick annotate, triage).

Registration shape:

- Base fields (`id`, `title`, `mount`, `capabilities`)
- `placement: "leading" | "trailing" | "overflow"`
- `capabilities` flags:
  - `requiresSelection` (action expects multi-select context)
  - `mutatesArticleState` (action may update read/saved/archived state)

Data dependencies:

- `GET /api/v1/articles`
- `PATCH /api/v1/articles/{article_id}/state` (if `mutatesArticleState=true`)
- `POST /api/v1/articles/state/bulk` (if `requiresSelection=true`)

Permission/auth constraints:

- Runs only for authenticated sessions.
- Action visibility is gated by user access to the row article in current scope/filter context.

Failure isolation behavior:

- On plugin failure, host removes the failing action control for that row and keeps built-in row actions available.

### 3) `reader_panel_tab`

Purpose: add tabs in the right reader pane (for example, metadata, enrichment output, related links).

Registration shape:

- Base fields (`id`, `title`, `mount`, `capabilities`)
- `tabOrder?: number` (optional stable sort hint; default after built-ins)
- `capabilities` flags:
  - `requiresArticleContent`
  - `supportsBackgroundRefresh`

Data dependencies:

- `GET /api/v1/articles/{article_id}`
- Optional: plugin may request additional read-only APIs related to selected article.

Permission/auth constraints:

- Runs only for authenticated sessions.
- Plugin only receives currently selected article payload already authorized by backend.

Failure isolation behavior:

- On plugin failure, host replaces that tab panel with inline error fallback while keeping other tabs functional.

### 4) `dashboard_card`

Purpose: define dashboard v2 card registry entries for top-level summary widgets.

Registration shape:

- Base fields (`id`, `title`, `mount`, `capabilities`)
- `cardSize: "sm" | "md" | "lg"`
- `defaultLayout: { column: number; row: number; w: number; h: number }`
- `capabilities` flags:
  - `supportsManualRefresh`
  - `supportsTimeRange`

Data dependencies:

- Core dashboard context expected from host: `GET /api/v1/navigation` and scoped `GET /api/v1/articles` summaries.
- Card-specific fetches must remain read-only unless explicitly mediated by host mutations.

Permission/auth constraints:

- Runs only for authenticated sessions.
- Cards must honor same per-user data boundaries as dashboard host; no global aggregate endpoints are exposed directly.

Failure isolation behavior:

- On plugin failure, host renders a standard failed-card shell with title + retry affordance and excludes only that card
  from layout calculations until recovery.

### 5) `command_palette_action`

Purpose: register extra commands in command palette for power-user flows and integrations.

Registration shape:

- Base fields (`id`, `title`, `mount`, `capabilities`)
- `keywords: string[]` (search aliases)
- `capabilities` flags:
  - `requiresArticleContext`
  - `opensExternalUrl`

Data dependencies:

- Baseline palette context uses current route/scope (no required API call).
- If contextual, may consume `GET /api/v1/articles/{article_id}` for active selection.

Permission/auth constraints:

- Runs only for authenticated sessions when command operates on protected resources.
- Commands that open external URLs must use allowlisted host validation to avoid untrusted redirect abuse.

Failure isolation behavior:

- On plugin failure during execution, host surfaces non-blocking toast error and keeps palette open/usable for other
  commands.

## Developer Topology (Dev Container Standard)

For day-to-day development, use the Dev Container stack in `.devcontainer/`:

1. `dev`: workspace container for editing/testing (`uv`, lint, tests, migrations)
2. `app`: FastAPI runtime with reload and migration-on-start
3. `worker`: RQ worker process
4. `scheduler`: periodic enqueue loop
5. `db`: PostgreSQL 17
6. `redis`: Redis 8
7. `traefik`: local edge router to simplify service access (`http://sift.localhost`)
8. `frontend`: Vite dev server for SPA runtime (`http://localhost:5173`)

## Development Seed Bootstrap

- Optional development-only bootstrap runs at API startup when `SIFT_DEV_SEED_ENABLED=true`.
- Bootstraps a local default account and imports OPML-based sample data.
- Inoreader `Monitoring feeds` OPML folder is mapped to keyword streams instead of RSS subscriptions.

## Database Lifecycle

- Migrations are managed with Alembic.
- Initial migration: `alembic/versions/20260214_0001_initial_schema.py`.
- Default runtime setting is now migration-first (`SIFT_AUTO_CREATE_TABLES=false`).
- Local bootstrap flow:
  1. `python -m alembic upgrade head`
  2. start app/service processes

## Package Layout

- `src/sift/api`: API routers and request/response boundaries
- `src/sift/services`: application services and use-case orchestration
- `src/sift/domain`: domain schemas and shared contracts
- `src/sift/db`: SQLAlchemy models and session management
- `src/sift/plugins`: plugin protocol, loader, built-ins
- `src/sift/tasks`: worker and scheduler entrypoints
- `frontend`: Vite + React + TypeScript source code and frontend tests

## Plugin Contract

Plugins are loaded by dotted path and may implement one or more hooks:

- `on_article_ingested(article)` for ingest-time enrichment/transformation.
- `classify_stream(article, stream)` for stream relevance decisions with confidence.
- Planned hooks:
  - scoring
  - post-filter action
  - outbound integration

Design goals:

1. deterministic plugin execution order
2. per-plugin fault isolation
3. observable plugin runs (timing, success/failure)

## Data Model (Initial)

- `feeds`: source catalog
  - includes owner reference (`owner_id`)
  - includes fetch metadata (`etag`, `last_modified`, `last_fetched_at`, `last_fetch_error`)
- `subscriptions`: user to feed mapping
- `raw_entries`: immutable source payloads (unique feed/source key for ingest dedupe)
- `articles`: normalized canonical content (unique feed/source key for ingest dedupe)
  - includes canonical dedup metadata (`canonical_url_normalized`, `content_fingerprint`, `duplicate_of_id`, `dedup_confidence`)
- `article_states`: per-user read/star/archive state
- `users`: account identity
- `auth_identities`: provider-aware identities (`local` now, OIDC providers later)
- `user_sessions`: server-side session records for cookie auth
- `api_tokens`: token records for future machine-to-machine access

## Planned Model Extensions

- vector storage (optional, plugin-driven):
  - keep embeddings/index references outside core ingest contract
  - expose through plugin interfaces for semantic matching/classification

## Implemented Service Slices

1. OPML import:
   - endpoint: `POST /api/v1/imports/opml`
   - flow: parse OPML -> normalize URLs -> per-user dedupe -> import report
2. Ingestion service:
   - endpoint: `POST /api/v1/feeds/{feed_id}/ingest`
   - flow: fetch -> parse -> dedupe -> persist raw/article -> plugin hook
3. Keyword filter preview:
   - endpoint: `POST /api/v1/articles/filter-preview`
   - include/exclude keyword matching over article title+content
4. Scheduler-driven background ingestion:
   - scheduler polls active feeds and enqueues due jobs
   - worker executes ingest jobs via RQ
   - queue dedupe by stable RQ-compatible job id (`ingest-<feed_id>`) with legacy `ingest:<feed_id>` lookup
5. Authentication and account foundation:
   - local account registration/login/logout/me endpoints
   - provider-ready identity schema to support Google/Azure/Apple later
   - feed/article endpoints now require authenticated user context
6. Persisted ingest rules:
   - endpoints: `GET/POST/PATCH/DELETE /api/v1/rules`
   - per-user rules with priority and criteria (include/exclude keywords, source, language)
   - rules applied during ingestion before article persistence
7. Keyword streams:
   - endpoints: `GET/POST/PATCH/DELETE /api/v1/streams`, `GET /api/v1/streams/{stream_id}/articles`
   - per-user saved stream expressions (include/exclude keywords, source, language)
   - stream memberships recorded for matching ingested articles
8. Stream classifier foundation:
   - stream config supports `classifier_mode` (`rules_only`, `classifier_only`, `hybrid`)
   - stream config supports `classifier_plugin` + `classifier_min_confidence`
   - plugin manager can dispatch classifier plugins by name
   - built-in heuristic classifier plugin included as reference implementation
9. Cross-feed canonical dedup foundation:
   - normalize article URLs (tracking-parameter stripping + stable query ordering)
   - compute content fingerprint hash over normalized title/content text
   - assign `duplicate_of_id` and confidence when canonical duplicate candidates are found
10. Feed folders:
   - per-user folder table (`feed_folders`) with stable ordering metadata
   - feed-to-folder mapping through nullable `feeds.folder_id`
   - authenticated folder CRUD API and feed folder assignment endpoint

## Frontend Delivery Standard

**Current**

1. Frontend is implemented as a greenfield React + TypeScript app in `frontend/` using Vite.
2. Folder layout is feature-first (`features/auth`, `features/workspace`) with shared typed API/domain layers.
3. TanStack Router + TanStack Query power route state and server-state caching/mutations.
4. OpenAPI-derived types are generated to `frontend/src/shared/types/generated.ts` and consumed through typed API contracts.
5. Vite build output is `frontend/dist` and is deployed by a separate static host/runtime.
6. Runtime CDN imports and legacy `React.createElement` frontend modules have been removed.

### Quality Baseline

| Category | Current frontend standard |
| --- | --- |
| Must-match behaviors | Keyboard shortcuts (`j/k`, `o`, `m`, `s`, `/`), scope/navigation flows powered by `/api/v1/navigation`, article list/reader behavior from `/api/v1/articles`, and article state mutations via `PATCH /api/v1/articles/{article_id}/state` and `POST /api/v1/articles/state/bulk`; keep density/theme persistence behavior parity. |
| Required quality gates | `pnpm run lint`, `pnpm run typecheck`, `pnpm run test`, and backend route tests must pass before merge. |
| Allowed improvements | Layout refinements, improved loading/error handling UX, and accessibility hardening are encouraged as long as they preserve fixed API contracts. |
| Deferred / non-goals | Advanced stream ranking/prioritization controls are explicitly out of scope for this cutover slice. |

## Planned Next Moves (Current Core Priority Plan)

1. Add stream-level ranking and prioritization controls.
2. Add classifier run persistence and model/version tracking.
3. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
4. Add scheduler and ingestion observability (metrics, latency, failures) after core content features.

## Deferred

1. Add first OIDC provider integration (Google) on top of `auth_identities`, then Azure/Apple.
2. Expand UI beyond settings-hub foundation with additional curated theme presets and final visual consistency polish.

## Frontend Settings and Theme Architecture (Current)

### Implemented

- Settings are centralized on `/account` with three sections:
  - Appearance
  - Reading/Layout
  - Account
- Workspace keeps only a quick theme toggle in the top bar and a settings entry point.
- Unified browser-local preferences are persisted under one model:
  - `themeMode`
  - `themePreset`
  - `density`
  - `navPreset`
- Legacy single-key preferences are still synchronized for backward compatibility.

### Theme System

- Theme creation uses `(themeMode, themePreset)` inputs.
- Semantic CSS tokens are preset-aware across both light and dark modes.
- Interaction tokens are preset-aware across workspace surfaces (rail/nav/list/reader hover + selected states).
- Current curated presets:
  - Sift Classic
  - Ocean Slate
  - Graphite Violet
  - Warm Sand

### Settings Accessibility Baseline

- Settings controls use semantic grouped forms (`fieldset` + `legend`) for screen-reader clarity.
- Keyboard navigation in settings toggle groups supports arrow keys and home/end movement.
- Focus-visible and selected-state styles are explicit and token-driven to maintain contrast per preset.

### Next UI Extensions (Deferred)

1. Additional preset tuning and theme-token refinement across rail/nav/list/reader surfaces.
2. Final visual consistency pass for hover/selected/contrast behavior per preset.
3. Extended accessibility/responsiveness pass for settings controls.

## Long-Term Product Backlog (Captured, Explicitly Deferred)

These items are intentionally documented for future implementation and are **not** part of the current priority stack.

### 1) Feed Health + Feed Lifecycle Management

Planned capability:

- A dedicated feed status/edit surface for operators/users to inspect feed health.
- Health/quality indicators per feed:
  - last successful fetch/ingest timestamp
  - recent failures + latest error context
  - ingest cadence metrics (for example, rolling articles/day)
- Lifecycle controls directly on this page:
  - pause/resume feed ingestion
  - archive/unarchive feed from active navigation

Architecture implications:

- Extend feed domain/API contracts with lifecycle state (`active`/`paused`/`archived`) and health aggregates.
- Add lightweight ingestion telemetry aggregation to power cadence and reliability indicators.

### 2) Monitoring Feed Definition Management (Keyword/Regex/Plugin)

Planned capability:

- A management UI/API for monitoring feed definitions and rule evolution.
- Matching primitives:
  - keyword matcher
  - regex matcher
  - plugin-provided matcher hooks for advanced discovery logic
- Optional historical backfill run when creating/updating monitoring definitions so existing article corpus can be rescored.
- Explainability in monitoring article lists/reader:
  - highlight matched keyword/regex spans
  - show plugin-provided match reasons/snippets

Architecture implications:

- Introduce a matcher abstraction for monitoring definitions with versioned configuration payloads.
- Add backend support for asynchronous historical match jobs against stored article corpus.
- Persist match evidence payloads to enable frontend explainability rendering.

### 3) Dashboard as Command Center

Planned capability:

- A top-level dashboard route optimized for daily triage.
- User-configurable prioritization across sources (feeds, monitoring feeds, and future scoped sources).
- Candidate cards:
  - latest unread by priority
  - high-signal monitoring matches
  - stale/error feed watchlist
  - saved/follow-up queue

Architecture implications:

- Extend existing `dashboard_card` plugin slot with source-priority context.
- Provide summary-focused dashboard query endpoints/view-models without replacing detailed workspace APIs.

### 4) Duplicate Candidate Review (Iteration 1)

Planned capability:

- Settings-accessible duplicate candidate view as initial UX for canonical dedup transparency.
- First version is read-centric:
  - grouped duplicate candidates
  - confidence and origin metadata
  - navigation to canonical + variant articles

Architecture implications:

- Add read API for duplicate groups leveraging existing canonical dedup fields.
- Preserve merge/resolve workflows for a later iteration.

### 5) Plugin Roadmap Ideas

Planned plugins:

- LLM summarization plugin (initial provider target: Ollama Cloud).
- Vector similarity plugin for article/topic relatedness and future semantic monitoring workflows.

Architecture implications:

- Ensure plugin execution contracts can persist model/provider/version metadata and outputs.
- Keep vector/embedding storage optional and plugin-boundary isolated from core ingest requirements.


### 6) Trends Detection Across Selected Feed Folders

Planned capability:

- Add a deferred trends subsystem that identifies rising topics in user-selected feed folders.
- Primary consumption surface: dashboard cards and daily briefing widgets.
- Trend outputs should include:
  - topic/keyphrase label
  - momentum signal (short-window lift vs baseline)
  - evidence bundle (article count, source diversity, and article links)

Architecture implications:

- Add a trend-analysis pipeline (batch or periodic) over scoped article sets.
- Persist trend snapshots so dashboard reads are fast and historically comparable.
- Provide read APIs/view models for dashboard and future analytics surfaces.

### Deferred Delivery Sequence (Post Current Core Priorities)

1. Feed health/edit + lifecycle controls.
2. Monitoring management v2 (keyword/regex/plugin + historical backfill + explainability).
3. Dashboard v1 command center.
4. Duplicate candidate review screen.
5. Trends detection for selected feed folders (dashboard-oriented).
6. Plugin implementations (LLM summary, vector similarity).
