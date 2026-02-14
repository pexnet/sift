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

Plugins implement `ArticlePlugin` and are loaded by dotted path:

- Hook now: `on_article_ingested`
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
  - includes fetch metadata (`etag`, `last_modified`, `last_fetched_at`, `last_fetch_error`)
- `subscriptions`: user to feed mapping
- `raw_entries`: immutable source payloads (unique feed/source key for ingest dedupe)
- `articles`: normalized canonical content (unique feed/source key for ingest dedupe)
- `article_states`: per-user read/star/archive state

## Implemented Service Slices

1. Ingestion service:
   - endpoint: `POST /api/v1/feeds/{feed_id}/ingest`
   - flow: fetch -> parse -> dedupe -> persist raw/article -> plugin hook
2. Keyword filter preview:
   - endpoint: `POST /api/v1/articles/filter-preview`
   - include/exclude keyword matching over article title+content
3. Scheduler-driven background ingestion:
   - scheduler polls active feeds and enqueues due jobs
   - worker executes ingest jobs via RQ
   - queue dedupe by stable job id (`ingest:<feed_id>`)

## Planned Next Moves

1. Add auth and ownership constraints.
2. Persist filter/rule definitions per user.
3. Add cross-feed canonical deduplication (`canonical_article_id` + fuzzy hash).
4. Add first production plugin (translation or summary) with plugin run history.
5. Add scheduler and ingest observability (metrics + structured logs).

