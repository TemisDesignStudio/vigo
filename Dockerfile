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

EXPOSE 8000
VOLUME ["/data"]

CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
