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
- Frontend owns routes (`/app`, `/login`, `/register`, `/account`, `/account/monitoring`, `/account/feed-health`,
  `/help`) and is deployed independently from FastAPI.
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
   - on-demand full article fetch action with retry (`Fetch full article` / `Refetch full article`)
   - content source labeling (`Source: full article` / `Source: feed excerpt`)
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

Frontend plugin integration is intentionally narrow and typed. The host app owns routing, API orchestration, auth
checks, and error boundaries; plugins mount only at explicit extension points.

### Shared registration contract

Every extension point registers items with a common base shape plus point-specific fields:

- `id: string` (globally unique and stable; recommended namespace `plugin_name.feature_name`)
- `title: string` (human-readable label used in UI and diagnostics)
- `mount: React.ComponentType<Props>` (render entry component for this extension point)
- `capabilities: { ... }` (boolean feature flags declared by plugin and validated by host)

Host-side guardrails:

1. Unknown capability flags are ignored and logged at debug level.
2. Duplicate `id` registrations are rejected deterministically (first registration wins, later registrations disabled).
3. Invalid registrations (missing required keys) are skipped and surfaced in diagnostics.
4. All plugin mounts are wrapped in per-item error boundaries (`Plugin unavailable` fallback).

### Extension points

1. `nav_badge_provider`: augment navigation labels/counts for system/folder/feed/stream nodes.
2. `article_row_action`: add row-level actions in article lists (`leading`/`trailing`/`overflow` placement).
3. `reader_panel_tab`: add reader-side panels/tabs for article-specific plugin content.
4. `dashboard_card`: define dashboard summary cards with host-managed availability/fallback states.
5. `command_palette_action`: register contextual commands for keyboard-first workflows.

Runtime rules for all extension points:

1. Plugins operate only within authenticated, user-scoped data returned by existing APIs.
2. Read-only access is default; mutating actions must be explicitly declared and host-mediated.
3. Failures disable only the affected plugin item and never break the surrounding workspace surface.
4. Detailed payload/field contracts live in implementation specs under `docs/specs/` and `docs/specs/done/`.

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

Optional local observability overlay:

1. `victoriametrics`: metrics storage/query (`http://localhost:8428`)
2. `victorialogs`: logs storage/query (`http://localhost:9428`)
3. `vmagent`: scrape + remote-write agent (`http://localhost:8429`)
4. `vector`: Docker log shipper for Sift runtime logs (`http://localhost:8686`)
5. Bootstrap and config files:
   - `ops/observability/docker-compose.observability.yml`
   - `ops/observability/vmagent/prometheus.yml`
   - `ops/observability/vector/vector.yaml`

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
- `src/sift/plugins`: plugin protocol, registry loader/validation, runtime manager, built-ins
- `src/sift/tasks`: worker and scheduler entrypoints
- `frontend`: Vite + React + TypeScript source code and frontend tests

## Plugin Contract

Plugins are now activated through centralized registry configuration (`config/plugins.yaml`) and may implement one or
more hooks:

- `on_article_ingested(article)` for ingest-time enrichment/transformation.
- `classify_stream(article, stream)` for stream relevance decisions with confidence.
- Planned hooks:
  - `search_feeds(request)` for provider-chain-backed blog/feed search (shared infrastructure)
  - `discover_feeds(seed_query, options)` for discovery-stream feed candidate lookup
  - `summarize_article(article, options)` for on-demand reader summary generation
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
  - includes fetch metadata (`etag`, `last_modified`, `last_fetched_at`, `last_fetch_success_at`, `last_fetch_error`,
    `last_fetch_error_at`)
  - includes lifecycle metadata (`is_active`, `is_archived`, `archived_at`)
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

Implemented slices are tracked at capability level here; detailed completion chronology is maintained in
`docs/current-state.md`, `docs/backlog-history.md`, and `docs/session-notes/archive/`.

1. Core ingestion and content pipeline:
   - OPML import, feed ingest, normalization, and dedupe foundations.
   - background scheduler/worker ingestion with stable job-id dedupe.
2. Auth and ownership model:
   - local auth/session foundation with user-scoped feed/article access.
3. Rules, streams, and monitoring:
   - persisted rules and keyword streams,
   - query language (`AND`/`OR`/`NOT`, phrases, wildcard, fuzzy),
   - backfill execution, regex support, match explainability, and classifier config payloads.
4. Classification and dedup intelligence:
   - classifier plugin execution modes and run persistence/diagnostics,
   - cross-feed canonical dedup metadata and duplicate linking.
5. Feed/folder operations:
   - folder CRUD and feed assignment,
   - feed lifecycle/health APIs and archive behavior.
6. Plugin platform:
   - centralized registry/runtime cutover,
   - capability-gated dispatch, timeout/fault isolation, diagnostics, and plugin telemetry metrics.
7. Frontend integration baselines:
   - workspace plugin areas and route host (`/app/plugins/$areaId`),
   - dashboard shell/card host baseline (`/app/dashboard`),
   - full article fetch-on-demand reader workflow.
8. Observability and operator surfaces:
   - request correlation + structured events,
   - API/scheduler/worker metrics surfaces and runbook-backed operations.

## Frontend Delivery Standard

**Current**

1. Frontend is implemented as a greenfield React + TypeScript app in `frontend/` using Vite.
2. Folder layout is feature-first (`features/auth`, `features/workspace`) with shared typed API/domain layers.
3. TanStack Router + TanStack Query power route state and server-state caching/mutations.
4. OpenAPI-derived types are generated to `frontend/src/shared/types/generated.ts` and consumed through typed API contracts.
5. Vite build output is `frontend/dist` and is deployed by a separate static host/runtime.
6. Runtime CDN imports and legacy `React.createElement` frontend modules have been removed.

## Delivery Pipeline

Current delivery automation is GitHub Actions + GHCR based:

1. `ci-fast` runs on PRs targeting `develop` and acts as the integration gate.
2. `release-readiness` runs on PRs targeting `main` and enforces:
   - full backend/frontend quality checks
   - release label contract (`release:major|minor|patch`)
   - security gate (dependency review + Trivy HIGH/CRITICAL)
3. `release-main` runs on push to `main` and:
   - computes the next SemVer tag from merged PR labels
   - creates GitHub Release notes
   - publishes multi-arch backend/frontend images to GHCR
4. `codeql` runs on `develop`/`main` PR and push events plus weekly schedule.

### Quality Baseline

| Category | Current frontend standard |
| --- | --- |
| Must-match behaviors | Keyboard shortcuts (`j/k`, `o`, `m`, `s`, `/`), scope/navigation flows powered by `/api/v1/navigation`, article list/reader behavior from `/api/v1/articles`, and article state mutations via `PATCH /api/v1/articles/{article_id}/state` and `POST /api/v1/articles/state/bulk`; keep density/theme persistence behavior parity. |
| Required quality gates | `pnpm run lint`, `pnpm run typecheck`, `pnpm run test`, and backend route tests must pass before merge. |
| Allowed improvements | Layout refinements, improved loading/error handling UX, and accessibility hardening are encouraged as long as they preserve fixed API contracts. |
| Deferred / non-goals | Advanced stream ranking/prioritization controls are explicitly out of scope for this cutover slice. |

## Planning Sources

- Active roadmap and prioritization source of truth: `docs/backlog.md`.
- Current implementation snapshot for session startup: `docs/current-state.md`.
- Completed/historical planning items: `docs/backlog-history.md`.

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
- Base surface and MUI palette tokens are preset-aware, so controls and panes stay visually consistent per preset.
- Current curated presets:
  - Sift Classic
  - Ocean Slate
  - Graphite Violet
  - Warm Sand

### Settings Accessibility Baseline

- Settings controls use semantic grouped forms (`fieldset` + `legend`) for screen-reader clarity.
- Keyboard navigation in settings toggle groups supports arrow keys and home/end movement.
- Focus-visible and selected-state styles are explicit and token-driven to maintain contrast per preset.
- Settings surface includes a first-class `Reset to defaults` action for UI preference recovery.
- Settings controls are responsive-first on mobile (full-width toggle groups and reset action sizing).

### UI Extension Status

1. Preset consistency, contrast/interaction tuning, and settings accessibility/responsiveness polish are implemented.
2. Monitoring management/explainability baselines are implemented; remaining sequencing is tracked in `docs/backlog.md`.

