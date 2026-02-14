#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "[error] uv is required but not installed."
  echo "Install instructions: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "[info] Created .env from .env.example"
else
  echo "[info] .env already exists; leaving it unchanged"
fi

echo "[info] Syncing project dependencies with uv (including dev extras)"
uv sync --extra dev

echo "[info] Applying database migrations"
uv run alembic upgrade head

echo "[info] Running validation checks"
uv run ruff check .
uv run pytest

cat <<'MSG'

[done] Codex environment is ready.

Useful commands:
  uv run uvicorn sift.main:app --reload
  uv run python -m sift.tasks.worker
  uv run python -m sift.tasks.scheduler
MSG
