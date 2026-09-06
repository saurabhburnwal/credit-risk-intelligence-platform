# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install system dependencies (OpenMP for LightGBM, SQLite, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official Astral image for fast, reproducible dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Configure uv and Python environment
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

# Copy dependency specifications first to take advantage of Docker layer caching
COPY pyproject.toml uv.lock ./

# Install locked dependencies deterministically (no compilation drift)
RUN uv sync --frozen --no-install-project

# Copy application code, sql scripts, model metadata and UI assets
COPY src/ ./src/
COPY sql/ ./sql/
COPY models/ ./models/
COPY notebooks/ ./notebooks/
COPY documents/ ./documents/

# Expose default Flask service port
EXPOSE 5000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Production WSGI server command using gunicorn via uv
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "src.ui.app:app"]
