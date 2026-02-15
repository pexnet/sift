# Session Notes

## 2026-02-15

### Architecture Baseline (Current)

- Backend is API-only FastAPI (`/api/v1/*`) and does not serve frontend pages or static bundles.
- Frontend is a standalone React + TypeScript app in `frontend/`.
- Frontend routes (`/app`, `/login`, `/register`, `/account`) are owned by the SPA runtime.
- Frontend/backend integration is API-only via REST endpoints.

### Implemented This Session

- Removed backend web delivery package and route surface (`src/sift/web/*`).
- Added CORS configuration in backend settings and middleware wiring in `src/sift/main.py`.
- Added API-only regression test: `tests/test_api_only_surface.py`.
- Set frontend build output to `frontend/dist`.
- Added frontend API base URL support through `VITE_API_BASE_URL`.
- Standardized docs (`AGENTS.md`, architecture, getting-started, development, deployment) to the API-only + standalone SPA model.
- Updated Dev Container stack to include frontend service and default port `5173`.
- Updated root `docker-compose.yml` to start full local stack including frontend dev server (`http://localhost:5173`).

### Verification

- Frontend:
  - `pnpm --dir frontend run gen:openapi`
  - `pnpm --dir frontend run lint`
  - `pnpm --dir frontend run typecheck`
  - `pnpm --dir frontend run test`
  - `pnpm --dir frontend run build`
- Backend:
  - `python -m ruff check src tests`
  - `python -m mypy src`
  - `python -m pytest`

### Current Priority Plan

1. Stabilize local runtime baseline:
   - fix scheduler job-id delimiter compatibility with current RQ
   - keep dev seed idempotent without noisy duplicate-stream DB errors
2. Add stream-level ranking and prioritization controls.
3. Add classifier run persistence and model/version tracking.
4. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
5. Add scheduler and ingestion observability (metrics, latency, failures) after core content features.

### Deferred

1. External OIDC provider integration (Google first, then Azure/Apple).
