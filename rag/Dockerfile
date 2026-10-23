FROM python:3.11.15-slim-bookworm AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

RUN useradd --create-home --uid 10001 app
COPY --chown=app:app app ./app
USER app
EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health/live', timeout=3)"]

FROM base AS development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

FROM base AS release
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
