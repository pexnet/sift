# Getting Started

## Prerequisites

- Python environment managed with `uv`
- Node.js 22+ with `pnpm`
- Docker (recommended for full local stack)

Install `uv`:
- <https://docs.astral.sh/uv/getting-started/installation/>

## Quick Local Setup (API + Frontend)

1. Copy environment config:
   - `copy .env.example .env` (Windows)
   - `cp .env.example .env` (macOS/Linux)
2. Install backend dependencies:
   - `uv sync --extra dev`
3. Apply migrations:
   - `uv run alembic upgrade head`
4. Start backend API:
   - `uv run uvicorn sift.main:app --reload`
5. In another terminal, start frontend:
   - `cd frontend`
   - `pnpm install`
   - `pnpm run gen:openapi`
   - `pnpm run dev`
6. Open:
   - Frontend: `http://127.0.0.1:5173`
   - Backend docs: `http://127.0.0.1:8000/docs`

Optional frontend config:
- Set `VITE_API_BASE_URL` when the API is hosted on a different origin than the frontend.

## Production Frontend Build

From `frontend/`:
- `pnpm run build`

Artifacts are written to `frontend/dist` and should be deployed by your frontend/static host.

## One-command Automation

For clean automation environments (including Codex):

- `./scripts/setup-codex-env.sh`

## First Run with Containers

- `docker compose up --build`
- This starts API, frontend dev server, worker, scheduler, db, and redis.
- Open:
  - Frontend: `http://localhost:5173`
  - API docs: `http://localhost:8000/docs`

## First Run with Dev Container Stack

- Reopen in Dev Container (`.devcontainer/devcontainer.json`).
- The stack starts API, frontend dev server, worker, scheduler, db, and redis.
- Open:
  - Frontend: `http://localhost:5173`
  - API docs: `http://localhost:8000/docs`

If development seed is enabled, default credentials are:
- email: `dev@sift.dev`
- password: `devpassword123!`
