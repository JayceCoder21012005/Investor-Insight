# Backend image: dependencies from uv.lock, price data and articles shipped inside (spec 13).
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY config ./config
COPY content ./content
COPY data ./data
COPY migrations ./migrations
COPY alembic.ini ./

ENV PORT=8000
EXPOSE 8000
# Run `uv run alembic upgrade head` once against DATABASE_URL_DIRECT before the first start (see README).
CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
