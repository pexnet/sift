# Sift Architecture

## Architectural Style

MVP uses a modular monolith with explicit boundaries:

1. Ingestion (fetch + parse + normalize)
2. Deduplication + filtering
3. Plugin pipeline
4. API/UI delivery

This keeps deployment simple while preserving clean seams for future service extraction.

## Runtime Components

1. `app`: FastAPI API + server-rendered UI (Jinja2 + HTMX)
2. `worker`: RQ worker for ingest jobs (`src/sift/tasks/worker.py`)
3. `scheduler`: periodic feed polling and job enqueue loop (`src/sift/tasks/scheduler.py`)
4. `db`: PostgreSQL (SQLite default for local bootstrap)
5. `redis`: queue broker

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
- `src/sift/web`: HTML routes, templates, static files

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
- `article_states`: per-user read/star/archive state
- `users`: account identity
- `auth_identities`: provider-aware identities (`local` now, OIDC providers later)
- `user_sessions`: server-side session records for cookie auth
- `api_tokens`: token records for future machine-to-machine access

## Planned Model Extensions

- feed folders (not implemented yet):
  - `feed_folders`: per-user folder objects
  - `feed_folder_items` or `feeds.folder_id`: feed organization mapping
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
   - queue dedupe by stable job id (`ingest:<feed_id>`)
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

## Planned Next Moves

1. Add cross-feed canonical deduplication (`canonical_article_id` + fuzzy hash).
2. Add feed folders (per-user folder objects and feed mappings).
3. Add scheduler and ingest observability (metrics + structured logs).
4. Add stream ranking/prioritization and rule evaluation metrics.
5. Add classifier run persistence and model/version tracking for traceability.
6. Add optional vector database plugin layer for semantic retrieval/matching workflows.

## Deferred

1. Add first OIDC provider integration (Google) on top of `auth_identities`, then Azure/Apple.

