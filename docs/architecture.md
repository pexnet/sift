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

## Developer Topology (Dev Container Standard)

For day-to-day development, use the Dev Container stack in `.devcontainer/`:

1. `dev`: workspace container for editing/testing (`uv`, lint, tests, migrations)
2. `app`: FastAPI runtime with reload and migration-on-start
3. `worker`: RQ worker process
4. `scheduler`: periodic enqueue loop
5. `db`: PostgreSQL 17
6. `redis`: Redis 8
7. `traefik`: local edge router to simplify service access (`http://sift.localhost`)

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
9. Cross-feed canonical dedup foundation:
   - normalize article URLs (tracking-parameter stripping + stable query ordering)
   - compute content fingerprint hash over normalized title/content text
   - assign `duplicate_of_id` and confidence when canonical duplicate candidates are found
10. Feed folders:
   - per-user folder table (`feed_folders`) with stable ordering metadata
   - feed-to-folder mapping through nullable `feeds.folder_id`
   - authenticated folder CRUD API and feed folder assignment endpoint

## Planned Next Moves

1. Add stream ranking/prioritization and rule evaluation metrics.
2. Add classifier run persistence and model/version tracking for traceability.
3. Add optional vector database plugin layer for semantic retrieval/matching workflows.
4. Add scheduler and ingest observability (metrics + structured logs) after core content features.

## Deferred

1. Add first OIDC provider integration (Google) on top of `auth_identities`, then Azure/Apple.

