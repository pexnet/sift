# Getting Started

## Prerequisites

- Python environment managed with `uv`
- Docker (recommended for full local stack)

Install `uv`:
- <https://docs.astral.sh/uv/getting-started/installation/>

## Quick Local Setup

1. Copy environment config:
   - `copy .env.example .env` (Windows)
   - `cp .env.example .env` (macOS/Linux)
2. Install dependencies:
   - `uv sync --extra dev`
3. Apply migrations:
   - `uv run alembic upgrade head`
4. Start the app:
   - `uv run uvicorn sift.main:app --reload`
5. Open:
   - `http://127.0.0.1:8000`

## One-command Automation

For clean automation environments (including Codex):

- `./scripts/setup-codex-env.sh`

## First Run with Containers

- `docker compose up --build`
- Open `http://localhost:8000/login`

If development seed is enabled, default credentials are:
- email: `dev@sift.local`
- password: `devpassword123!`
