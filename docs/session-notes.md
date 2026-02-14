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
- Verified quality gates:
  - `python -m ruff check .` passed
  - `python -m pytest` passed (11 tests)
  - `python -m mypy src` passed
  - `python -m alembic upgrade head` passed against a temporary SQLite DB

## Current Priority Plan

1. Add user/auth foundation and enforce feed/subscription ownership.
2. Persist filter/rule definitions (`include/exclude`, source, language) and apply them at ingest time.
3. Add canonical dedup layer across feeds (URL normalization + hash/fuzzy scoring).
4. Add first real plugin (translation or LLM summary) with persisted plugin run logs.
5. Add scheduler observability metrics (queue depth, success/failure, ingest latency).

## Working Notes

- In dev, run migrations before app start:
  - `python -m alembic upgrade head`
- During transition, avoid mixing `create_all` with migrations in shared environments.
- Keep this file concise: what changed, what was verified, and the next 3-5 concrete steps.

