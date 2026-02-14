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
- Implemented stream classifier plugin foundation:
  - Added stream classifier fields + migration `20260214_0005_stream_classifier_fields`
  - Extended stream models/schemas/services with `rules_only`/`classifier_only`/`hybrid` modes
  - Added classifier plugin contract + plugin manager dispatch by plugin name
  - Added built-in `keyword_heuristic_classifier` plugin as reference
  - Integrated classifier-aware stream matching into `ingestion_service`
  - Added stream classifier mode tests
- Implemented Dev Container-first development stack:
  - Added `.devcontainer/devcontainer.json` with full run-services configuration
  - Added `.devcontainer/docker-compose.yml` with `dev`, `app`, `worker`, `scheduler`, `db`, `redis`, `traefik`
  - Added `.devcontainer/Dockerfile` to provide Python 3.13 + `uv` in workspace container
  - Standardized local routing via Traefik (`http://sift.localhost`)
  - Updated README + AGENTS + architecture docs with the new default dev workflow
- Added local-only VS Code personalization support:
  - Added gitignored local override files: `.vscode/extensions.local.json`, `.vscode/settings.local.json`
  - Added committed templates: `.vscode/extensions.local.example.json`, `.vscode/settings.local.example.json`
  - Added helper installer script: `scripts/setup-local-vscode.ps1`
  - Updated README + AGENTS with local setup instructions
- Implemented cross-feed canonical dedup foundation:
  - Added article dedup metadata fields + migration `20260214_0006_article_canonical_dedup`
  - Added canonical URL normalization + content fingerprinting service (`src/sift/services/dedup_service.py`)
  - Integrated canonical duplicate lookup into ingestion flow with confidence scoring
  - Added `canonical_duplicate_count` in ingest result payload
  - Added dedup unit tests in `tests/test_ingestion_service.py`
- Implemented feed folders:
  - Added folder schema + migration `20260214_0007_feed_folders` (`feed_folders` + `feeds.folder_id`)
  - Added folder service (`src/sift/services/folder_service.py`) with user-scoped CRUD
  - Added folders API (`GET/POST/PATCH/DELETE /api/v1/folders`)
  - Added feed folder assignment endpoint (`PATCH /api/v1/feeds/{feed_id}/folder`)
  - Added folder service tests (`tests/test_folder_service.py`)
- Implemented development seed bootstrap:
  - Added config-driven dev seeding options in `src/sift/config.py`
  - Added startup seed flow in `src/sift/main.py`
  - Added seed service (`src/sift/services/dev_seed_service.py`) to:
    - create default local dev user
    - import OPML feed folders/feeds
    - map Inoreader `Monitoring feeds` entries to keyword streams
  - Added default seed OPML file: `dev-data/inoreader-default.opml`
  - Added seed parsing and idempotency tests (`tests/test_dev_seed_service.py`)
  - Enabled dev seed defaults in Docker and devcontainer app setup
- Hardened dev seed data privacy:
  - Switched default local seed path to `dev-data/local-seed.opml` (gitignored)
  - Added committed sanitized sample `dev-data/public-sample.opml`
  - Added `dev-data/README.md` with local/public seed-file guidance
  - Added gitignore entries for personal OPML filenames
- Verified quality gates:
  - `python -m ruff check .` passed
  - `python -m pytest` passed (dev seed tests added)
  - `python -m mypy src` passed
  - `python -m alembic upgrade head` passed against a temporary SQLite DB (through latest migration)
  - `docker compose -f .devcontainer/docker-compose.yml config` passed

## Current Priority Plan

1. Add stream-level ranking and prioritization controls.
2. Add classifier run persistence and model/version tracking.
3. Explore vector database integration as plugin capability for semantic matching/classification.
4. Add scheduler observability metrics (queue depth, success/failure, ingest latency) after core features.

## Deferred Items

1. External OIDC provider integration (Google first, then Azure/Apple) using `auth_identities`.

## Working Notes

- In dev, run migrations before app start:
  - `python -m alembic upgrade head`
- Preferred day-to-day dev flow is now Dev Container + `.devcontainer/docker-compose.yml`.
- During transition, avoid mixing `create_all` with migrations in shared environments.
- Keep this file concise: what changed, what was verified, and the next 3-5 concrete steps.

