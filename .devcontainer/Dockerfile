FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm
RUN python -m pip install --no-cache-dir uv
