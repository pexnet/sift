# Deployment Guide

## Runtime Topology

Standard runtime services:
- `app` (FastAPI API-only service)
- `worker` (RQ worker)
- `scheduler` (ingest scheduler loop)
- `db` (PostgreSQL)
- `redis` (queue backend)

Frontend is deployed as a separate static SPA build from `frontend/dist`.

See architecture details in [`docs/architecture.md`](architecture.md).

## Docker Compose (Local Full Stack)

Start local full stack:

- `docker compose up --build`

This runs API, frontend dev server, queue workers, and data services for local development.

## GHCR Release Deployment

Release artifacts are published to GHCR on each `main` release:

- `ghcr.io/pexnet/sift-backend:vX.Y.Z` and `:latest`
- `ghcr.io/pexnet/sift-frontend:vX.Y.Z` and `:latest`

Deploy using:

```bash
export SIFT_VERSION=vX.Y.Z
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

`docker-compose.release.yml` runs:

- `app` (runs Alembic migration then starts API)
- `worker`
- `scheduler`
- `frontend` (Nginx static host + `/api` reverse proxy to `app`)
- `db`
- `redis`

## Dev Container Compose

Run the devcontainer service topology (without opening VS Code):

- `docker compose -f .devcontainer/docker-compose.yml up --build`

This profile includes the frontend Vite service on `http://localhost:5173` for local full-stack development.

## Frontend Deployment

From `frontend/`:
- `pnpm install --frozen-lockfile`
- `pnpm run gen:openapi`
- `pnpm run build`

Deploy `frontend/dist` to your static host (Nginx, CDN, object storage + CDN, etc.) with SPA history fallback to
`index.html`.

Recommended integration pattern:
- serve frontend and backend on the same site origin, and proxy `/api/*` to the FastAPI service.
- if deployed cross-origin, keep CORS and credential settings aligned.
- set `VITE_API_BASE_URL` at frontend build time when API is not available on the same origin.

## Operational Notes

- Run database migrations before or during app startup.
- Keep scheduler and worker running to support recurring ingestion.
- Configure CORS for deployed frontend origins:
  - `SIFT_CORS_ALLOW_ORIGINS`
  - `SIFT_CORS_ALLOW_CREDENTIALS`
  - `SIFT_CORS_ALLOW_METHODS`
  - `SIFT_CORS_ALLOW_HEADERS`
- Configure queue/scheduler behavior with:
  - `SIFT_INGEST_QUEUE_NAME`
  - `SIFT_SCHEDULER_POLL_INTERVAL_SECONDS`
  - `SIFT_SCHEDULER_BATCH_SIZE`
