# ============================================
# Stage 1: Build — instala dependencias con uv
# ============================================
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app/backend

# Cachea dependencias por separado del código (clave para builds rápidos)
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Ahora copia el código y sincroniza el proyecto en sí
COPY apps/backend/app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# Stage 2: Runtime — imagen final, sin uv ni build tools
# ============================================
FROM python:3.14-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/backend/data \
    && chown appuser:appuser /app/backend/data

COPY --chown=appuser:appuser --from=builder /app/backend/.venv ./.venv
COPY --chown=appuser:appuser --from=builder /app/backend/app ./app

ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000
VOLUME ["/app/backend/data"]

HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
