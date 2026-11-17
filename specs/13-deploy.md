# 13 — Deploy and packaging

## Goal
Public demo, documented repo, CV-ready.

## Steps
1. Neon `main` branch: `uv run alembic upgrade head` with `DATABASE_URL_DIRECT`.
2. Backend: Docker image built with uv (`COPY pyproject.toml uv.lock`, `uv sync --frozen --no-dev`, then `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`), deployed to any container host. Env: `DATABASE_URL` (pooled), `LLM_API_KEY`, `LLM_MODEL`, `CORS_ORIGIN`. Price parquet and articles ship inside the image.
3. Frontend: deploy Next.js with `NEXT_PUBLIC_API_BASE` pointing to the backend.
4. Smoke test: `/api/health`, load P03 demo, generate report.

## README.md
- Problem in 3 lines; screenshot; live link.
- Architecture diagram: CSV → validate → ledger/portfolio → metrics → flags → LLM + guardrails → dashboard.
- How to run locally (Neon `dev` branch, `.env.example`).
- Eval table copied from `eval/results.md`, with date and model.
- Limitations: simulated data, adjusted prices, no dividends/splits, not investment advice.

## Demo assets
- 2–3 minute video: demo profile → behavior tab → AI report → guardrail badge.
- Screenshots of each dashboard tab for the internship report.

## Acceptance
- Fresh clone + `.env` + documented commands reproduces the demo locally.
