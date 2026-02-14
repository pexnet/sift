# Development Guide

## Recommended Workflow: Dev Container

Sift standardizes development on a Dev Container stack.

Prerequisites:
- Docker Desktop
- VS Code with Dev Containers extension

Steps:
1. Open repository in VS Code.
2. Run **Dev Containers: Reopen in Container**.
3. Wait for dependency sync (`uv sync --extra dev`).
4. Services from `.devcontainer/docker-compose.yml` start automatically.

Primary URLs:
- App via Traefik: `http://sift.localhost`
- App direct: `http://localhost:8000`
- Traefik dashboard: `http://localhost:8081`

## Daily Commands

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Tests: `uv run pytest`
- Type check: `uv run mypy src`
- Create migration: `uv run alembic revision --autogenerate -m "your message"`
- Run worker: `uv run python -m sift.tasks.worker`
- Run scheduler: `uv run python -m sift.tasks.scheduler`

## Development Seed Notes

When enabled in local/devcontainer config, the seed flow:
- creates a default local user,
- imports OPML feeds/folders,
- maps Inoreader monitoring feeds to keyword streams,
- and runs idempotently on startup.

Use `dev-data/local-seed.opml` for personal local data (gitignored). The fallback committed sample is
`dev-data/public-sample.opml`.

## Local VS Code Personalization

Use gitignored local files for machine-specific settings:
- `.vscode/extensions.local.json`
- `.vscode/settings.local.json`

Starter templates:
- `.vscode/extensions.local.example.json`
- `.vscode/settings.local.example.json`

Install extension set from your local file:
- `powershell -ExecutionPolicy Bypass -File scripts/setup-local-vscode.ps1`

## Reader Workspace Shortcuts

- `j` / `k`: move selection down/up
- `o`: open selected article in reader pane
- `m`: toggle read/unread on selected article
- `s`: toggle saved/starred on selected article
- `/`: focus article search

## Developer Notes

- Plugin implementations should follow `ArticlePlugin` in `src/sift/plugins/base.py`.
- Plugin paths are loaded from `SIFT_PLUGIN_PATHS`.
- Queue/scheduler controls:
  - `SIFT_INGEST_QUEUE_NAME`
  - `SIFT_SCHEDULER_POLL_INTERVAL_SECONDS`
  - `SIFT_SCHEDULER_BATCH_SIZE`
- Prefer migration-first schema evolution through Alembic.
