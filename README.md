# Sift

Sift is a self-hosted RSS aggregation portal designed for a solid Python backend, easy extensibility, and a simple web UI.

## Stack (MVP Foundation)

- Backend: FastAPI, SQLAlchemy, Pydantic Settings
- UI: Jinja2 templates + HTMX
- Queue/Scheduling: Redis + RQ + scheduler stub
- Storage: PostgreSQL in Docker (SQLite default for local bootstrap)
- Tooling: uv, Ruff, Pytest, Mypy

## Quick Start

1. Install `uv`: <https://docs.astral.sh/uv/getting-started/installation/>
2. Create env file:
   - `copy .env.example .env`
3. Create virtual environment and sync dependencies:
   - `uv sync --extra dev`
4. Run migrations:
   - `uv run alembic upgrade head`
5. Run API and web app:
   - `uv run uvicorn sift.main:app --reload`
6. Open:
   - `http://127.0.0.1:8000`

## Recommended Development Workflow (Dev Container)

This project now standardizes development on a Dev Container with full supporting services.

Prerequisites:

- Docker Desktop
- VS Code with the `Dev Containers` extension

How to start:

1. Open this repository in VS Code.
2. Run `Dev Containers: Reopen in Container`.
3. Wait for the workspace build and `postCreateCommand` (`uv sync --extra dev`) to finish.
4. Dev services are started automatically from `.devcontainer/docker-compose.yml`:
   - `dev` (workspace)
   - `app` (FastAPI + auto-migrations + reload)
   - `worker`
   - `scheduler`
   - `db` (PostgreSQL 17)
   - `redis` (Redis 8)
   - `traefik` (edge router)

Primary URLs:

- App via Traefik: `http://sift.localhost`
- App direct: `http://localhost:8000`
- Traefik dashboard: `http://localhost:8081`

Default development seed behavior (enabled in Docker/devcontainer app service):

- Creates default local user:
  - email: `dev@sift.local`
  - password: `devpassword123!`
- Loads seed OPML from `dev-data/local-seed.opml` (gitignored local file).
- Falls back to committed sanitized sample `dev-data/public-sample.opml` if local file is missing.
- Imports normal OPML entries as feeds (+ folders).
- Imports Inoreader `Monitoring feeds` entries as keyword streams.
- Seeding is idempotent (safe to run on each app start).

To use your personal OPML locally:

1. Copy your OPML to `dev-data/local-seed.opml`.
2. Start the stack.
3. Your personal file stays out of git.

## Local VS Code Overrides (Not in Git)

Use personal local files for machine-specific VS Code setup:

- `.vscode/extensions.local.json`
- `.vscode/settings.local.json`

These files are intentionally gitignored. Starter templates are committed:

- `.vscode/extensions.local.example.json`
- `.vscode/settings.local.example.json`

To apply extension installs from your local file:

- `powershell -ExecutionPolicy Bypass -File scripts/setup-local-vscode.ps1`

## Dev Commands

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Tests: `uv run pytest`
- Type check: `uv run mypy src`
- New migration: `uv run alembic revision --autogenerate -m "your message"`
- Run worker: `uv run python -m sift.tasks.worker`
- Run scheduler: `uv run python -m sift.tasks.scheduler`

## Reader Workspace UI

- Main authenticated UI: `GET /app`
- Layout:
  - left navigation tree (system folders, folders/feeds, monitoring streams)
  - center article list (search, scope state, sort, density)
  - right reader panel (article content and actions)
- Preferences persisted locally:
  - theme: light/dark
  - list density: compact/comfortable (compact default)

Keyboard shortcuts:

- `j` / `k`: move selection down/up
- `o`: open selected article in reader pane
- `m`: toggle read/unread on selected article
- `s`: toggle saved/starred on selected article
- `/`: focus article search

## Docker (App + Worker + Scheduler + Postgres + Redis)

- `docker compose up --build`
- Dev container stack (without VS Code): `docker compose -f .devcontainer/docker-compose.yml up --build`

## Plugin Direction

Plugins should implement the `ArticlePlugin` protocol in `src/sift/plugins/base.py`.
Configured plugin paths are loaded from `SIFT_PLUGIN_PATHS` in `.env`.

## API Notes (Current)

- Register: `POST /api/v1/auth/register`
- Login: `POST /api/v1/auth/login`
- Logout: `POST /api/v1/auth/logout`
- Current user: `GET /api/v1/auth/me`
- List rules: `GET /api/v1/rules`
- Create rule: `POST /api/v1/rules`
- Update rule: `PATCH /api/v1/rules/{rule_id}`
- Delete rule: `DELETE /api/v1/rules/{rule_id}`
- List streams: `GET /api/v1/streams`
- Create stream: `POST /api/v1/streams`
- Update stream: `PATCH /api/v1/streams/{stream_id}`
- Delete stream: `DELETE /api/v1/streams/{stream_id}`
- Stream articles: `GET /api/v1/streams/{stream_id}/articles`
- List feeds: `GET /api/v1/feeds`
- Create feed: `POST /api/v1/feeds`
- Ingest one feed now: `POST /api/v1/feeds/{feed_id}/ingest`
- Assign/unassign feed folder: `PATCH /api/v1/feeds/{feed_id}/folder`
- List folders: `GET /api/v1/folders`
- Create folder: `POST /api/v1/folders`
- Update folder: `PATCH /api/v1/folders/{folder_id}`
- Delete folder: `DELETE /api/v1/folders/{folder_id}`
- Keyword filter preview: `POST /api/v1/articles/filter-preview`
- List scoped articles: `GET /api/v1/articles`
- Get article detail: `GET /api/v1/articles/{article_id}`
- Patch article state: `PATCH /api/v1/articles/{article_id}/state`
- Bulk patch article state: `POST /api/v1/articles/state/bulk`
- Get navigation tree: `GET /api/v1/navigation`
- Import OPML: `POST /api/v1/imports/opml` (multipart file upload)

## Authentication and Identity Providers

- Local accounts use Argon2 password hashing and secure session cookies.
- Identity model is provider-aware via `auth_identities` table.
- Current provider: `local`.
- Planned providers (same user model): Google, Azure AD/Microsoft, Apple, and other OIDC-compliant providers.

## Stream Classifier Foundation

- Streams support classifier configuration:
  - `classifier_mode`: `rules_only` | `classifier_only` | `hybrid`
  - `classifier_plugin`: plugin name
  - `classifier_min_confidence`: confidence threshold
- Built-in example classifier plugin:
  - `keyword_heuristic_classifier`

## Canonical Dedup Foundation

- Ingestion computes:
  - normalized canonical URL (tracking params removed, stable query ordering)
  - content fingerprint (hash of normalized title/content)
- Cross-feed duplicates are linked via `articles.duplicate_of_id` with `dedup_confidence`.
- Ingest response includes `canonical_duplicate_count`.

## Feed Folders Foundation

- Folders are user-scoped and support ordering via `sort_order`.
- Feeds can be assigned or unassigned from folders through `PATCH /api/v1/feeds/{feed_id}/folder`.
- Deleting a folder unassigns its feeds.

## Dev Seed Settings

- `SIFT_DEV_SEED_ENABLED`
- `SIFT_DEV_SEED_DEFAULT_USER_EMAIL`
- `SIFT_DEV_SEED_DEFAULT_USER_PASSWORD`
- `SIFT_DEV_SEED_DEFAULT_USER_DISPLAY_NAME`
- `SIFT_DEV_SEED_OPML_PATH`
- `SIFT_DEV_SEED_MONITORING_FOLDER_NAME`

## Run Locally Now

Recommended:

1. `docker compose up --build`
2. Open `http://localhost:8000/login`
3. Login with:
   - email: `dev@sift.local`
   - password: `devpassword123!`

Dev Container:

1. Reopen in container.
2. Wait for services to start (`app`, `worker`, `scheduler`, `db`, `redis`, `traefik`).
3. Open `http://sift.localhost/login` and login with the same dev user.

## Background Processing

- Scheduler polls active feeds and enqueues due ingest jobs in Redis/RQ.
- Worker consumes queue jobs and runs feed ingestion.
- Queue and scheduler behavior are configurable through:
  - `SIFT_INGEST_QUEUE_NAME`
  - `SIFT_SCHEDULER_POLL_INTERVAL_SECONDS`
  - `SIFT_SCHEDULER_BATCH_SIZE`

## Long-Term Project Memory

- Session-specific notes: `docs/session-notes.md`
- Architectural decisions: `docs/architecture.md`
- Codex run instructions and conventions: `AGENTS.md`

