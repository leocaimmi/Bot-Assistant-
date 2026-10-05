# syntax=docker/dockerfile:1

# ---- Build stage: install locked dependencies with uv ------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer stays cached until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# ---- Runtime stage: slim image without build tools ---------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DATA_DIR=/data \
    DATABASE_URL=sqlite+aiosqlite:////data/asistente.db

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/entrypoint

RUN mkdir -p "$DATA_DIR" && chown app:app "$DATA_DIR"

# The entrypoint starts as root only to fix the volume ownership, then drops to "app".
ENTRYPOINT ["entrypoint"]
CMD ["python", "-m", "asistente"]
