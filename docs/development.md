# Development Guide

## Runtime Boundary

- Backend (`src/sift`): FastAPI API-only service on `/api/v1/*`.
- Frontend (`frontend/`): standalone React + TypeScript SPA (Vite).
- Integration contract: frontend communicates with backend through REST APIs only.

## Branching and PR Policy

- `develop` is the default integration branch.
- `main` is release-only.
- Feature flow: `feature/*` -> PR to `develop`.
- Release flow: PR `develop` -> `main` with merge commit.
- Hotfix flow: `hotfix/*` from `main` -> PR to `main` (`release:patch`) -> back-merge to `develop`.

Release labels for PRs into `main`:

- exactly one of `release:major`, `release:minor`, `release:patch`

## Recommended Workflow: Dev Container

Sift standardizes full-stack development on the Dev Container stack.

Prerequisites:
- Docker Desktop
- VS Code with Dev Containers extension

Steps:
1. Open repository in VS Code.
2. Run **Dev Containers: Reopen in Container**.
3. Wait for dependency sync (`uv sync --extra dev` and frontend install/type generation).
4. The compose stack starts backend + frontend services automatically.
5. If frontend service is stopped, run from the `dev` container:
   - `cd frontend && pnpm run dev --host 0.0.0.0 --port 5173`

Primary URLs:
- Frontend SPA: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Traefik dashboard: `http://localhost:8081`

## Docker Compose (Outside Dev Container)

- Run `docker compose up --build` from the repository root.
- This starts the same core services plus the frontend dev server on `http://localhost:5173`.

## Daily Backend Commands

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Tests: `uv run pytest`
- Type check: `uv run mypy src`
- Create migration: `uv run alembic revision --autogenerate -m "your message"`
- Run worker: `uv run python -m sift.tasks.worker`
- Run scheduler: `uv run python -m sift.tasks.scheduler`

## Daily Frontend Commands

Run from `frontend/`:

- Install deps: `pnpm install`
- Generate API types: `pnpm run gen:openapi`
- Start dev server: `pnpm run dev`
- Lint: `pnpm run lint`
- Type check: `pnpm run typecheck`
- Unit tests: `pnpm run test`
- E2E tests: `pnpm run e2e`
- Format check: `pnpm run format:check`
- Production build: `pnpm run build` (output: `frontend/dist`)

## CORS and API Proxy

- Vite proxies `/api` to `http://127.0.0.1:8000` in local development.
- Override Vite proxy target with `VITE_DEV_API_PROXY_TARGET` (used by Dev Container frontend service).
- Frontend API client supports `VITE_API_BASE_URL` for explicit API origin configuration.
- Backend CORS defaults allow `http://localhost:5173` and `http://127.0.0.1:5173`.
- Override with:
  - `SIFT_CORS_ALLOW_ORIGINS`
  - `SIFT_CORS_ALLOW_CREDENTIALS`
  - `SIFT_CORS_ALLOW_METHODS`
  - `SIFT_CORS_ALLOW_HEADERS`

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
