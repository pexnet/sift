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
2. `worker`: RQ worker for async and plugin tasks
3. `scheduler`: periodic feed polling and maintenance jobs
4. `db`: PostgreSQL (SQLite default for local bootstrap)
5. `redis`: queue broker

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
- `subscriptions`: user to feed mapping
- `raw_entries`: immutable source payloads
- `articles`: normalized canonical content
- `article_states`: per-user read/star/archive state

## Planned Next Moves

1. Add Alembic migrations.
2. Implement feed fetch + parser pipeline.
3. Add deduplication service (`canonical_article_id`, fuzzy hash).
4. Add rule engine and keyword filtering.
5. Add first plugin (translation or summary).

