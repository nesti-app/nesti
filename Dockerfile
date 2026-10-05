FROM python:3.13-slim AS builder

# gcc/libpq-dev are only needed to build native extensions. This stage is
# discarded, so the toolchain never reaches the published image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --no-install-project


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# fonts-dejavu-core is a runtime requirement, not a build one: label rendering
# loads /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf by absolute path
# (app/labels/service.py). Without it the loader falls back to a bitmap font
# instead of failing loudly, so the image would look fine and print badly.
RUN apt-get update && \
    apt-get install -y --no-install-recommends fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

# Nothing else is needed at runtime: pillow-heif bundles its own
# libheif/libde265 through auditwheel, and asyncpg does not use libpq.
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app
COPY migrations ./migrations
COPY static ./static
COPY templates ./templates
COPY alembic.ini ./alembic.ini

RUN useradd --create-home --uid 10001 nesti && \
    mkdir -p /app/data /data && \
    chown -R nesti:nesti /app /app/data /data

USER nesti

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]