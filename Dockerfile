FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN node --test tests/config.test.mjs && npm run build && node --test tests/export.test.mjs

FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/backend

COPY backend/pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY backend/ ./
RUN PYTHONPATH=. uv run --with pytest --with httpx pytest tests
COPY --from=frontend-build /app/frontend/out /app/frontend/out

EXPOSE 8000
VOLUME ["/data"]

CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
