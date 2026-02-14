FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY docs ./docs
COPY AGENTS.md ./

RUN uv sync --dev

CMD ["uv", "run", "uvicorn", "sift.main:app", "--host", "0.0.0.0", "--port", "8000"]

