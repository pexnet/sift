# Session Notes

## 2026-02-14

- Created initial project scaffold with FastAPI + Jinja2 + HTMX.
- Added SQLAlchemy async setup and baseline models.
- Added plugin protocol and dynamic plugin loader.
- Added worker/scheduler stubs for queue-based processing.
- Standardized tooling around uv + Ruff + Pytest + Mypy.
- Ruff line width set to 120.
- Added Alembic setup (`alembic.ini`, `alembic/`) with initial migration `20260214_0001`.
- Added ingestion metadata to `feeds` (`etag`, `last_modified`, `last_fetched_at`, `last_fetch_error`).
- Added per-feed source-id dedupe keys on `raw_entries` and `articles`.
- Added ingestion service and API endpoint: `POST /api/v1/feeds/{feed_id}/ingest`.
- Added keyword filter service and API endpoint: `POST /api/v1/articles/filter-preview`.
- Set `SIFT_AUTO_CREATE_TABLES=false` by default to favor migration-driven schema changes.
- Added tests for ingestion helpers and keyword filtering.
- Implemented recurring ingestion scheduling:
  - RQ queue helpers in `src/sift/tasks/queueing.py`
  - Feed ingest job wrapper in `src/sift/tasks/jobs.py`
  - Scheduler due-feed enqueue loop in `src/sift/tasks/scheduler.py`
  - Worker startup for ingest queue in `src/sift/tasks/worker.py`
- Added scheduler due-feed tests (`tests/test_scheduler.py`).
- Implemented provider-ready authentication and account foundation:
  - Added models: `users`, `auth_identities`, `user_sessions`, `api_tokens`
  - Added feed ownership column: `feeds.owner_id`
  - Added Alembic migration: `20260214_0002_auth_accounts`
  - Added auth service with Argon2 hashing + cookie session lifecycle
  - Added API auth routes: register/login/logout/me
  - Added web routes/templates: login/register/account/logout
  - Protected feed/article APIs behind authenticated sessions
  - Added auth service tests
- Current limitation:
  - `feeds.url` remains globally unique; cross-account shared-feed model is not yet implemented.
- Implemented OPML import:
  - Added OPML parser/import service in `src/sift/services/opml_service.py`
  - Added authenticated upload endpoint: `POST /api/v1/imports/opml`
  - Added detailed import report (created/skipped/invalid/duplicate)
  - Added OPML parser/import tests
- Implemented persisted ingest-time rule engine:
  - Added `ingest_rules` model + migration `20260214_0003_ingest_rules`
  - Added authenticated rules API (`GET/POST/PATCH/DELETE /api/v1/rules`)
  - Added rule service (`src/sift/services/rule_service.py`) with priority + criteria matching
  - Integrated rule evaluation into `ingestion_service` (drops matched items before article insert)
  - Added `filtered_count` to ingestion result payload
  - Added rule service tests
- Implemented keyword streams as monitoring feeds:
  - Added `keyword_streams` and `keyword_stream_matches` models + migration `20260214_0004_keyword_streams`
  - Added streams API (`GET/POST/PATCH/DELETE /api/v1/streams`, `GET /api/v1/streams/{stream_id}/articles`)
  - Added stream service (`src/sift/services/stream_service.py`) with criteria matching
  - Integrated stream matching into `ingestion_service` for newly ingested articles
  - Added `stream_match_count` to ingestion result payload
  - Added stream service tests
- Verified quality gates:
  - `python -m ruff check .` passed
  - `python -m pytest` passed (stream tests added)
  - `python -m mypy src` passed
  - `python -m alembic upgrade head` passed against a temporary SQLite DB

## Current Priority Plan

1. Add classifier plugin foundation for advanced stream classification (LLM/ML/rule plugins).
2. Add canonical dedup layer across feeds (URL normalization + hash/fuzzy scoring).
3. Add scheduler observability metrics (queue depth, success/failure, ingest latency).
4. Add stream-level ranking and prioritization controls.
5. Add classifier run persistence and model/version tracking.

## Deferred Items

1. External OIDC provider integration (Google first, then Azure/Apple) using `auth_identities`.

## Working Notes

- In dev, run migrations before app start:
  - `python -m alembic upgrade head`
- During transition, avoid mixing `create_all` with migrations in shared environments.
- Keep this file concise: what changed, what was verified, and the next 3-5 concrete steps.

