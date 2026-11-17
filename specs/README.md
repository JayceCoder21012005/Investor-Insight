# Investor Insight — Specs

Web app that analyzes a retail investor's own trade history. Deterministic Python computes every metric; an LLM only explains those metrics in Vietnamese. No buy/sell advice, no price forecasts.

Read `00-conventions.md` first, then only the spec for the task you are doing.

| # | Spec | Builds | Depends on |
|---|---|---|---|
| 00 | conventions | rules, stack, layout, env | — |
| 01 | prices | `scripts/fetch_prices.py`, `core/prices.py` | 00 |
| 02 | csv-validation | `core/validate.py`, `core/fees.py` | 01 |
| 03 | ledger-portfolio | `core/ledger.py`, `core/portfolio.py` | 01, 02 |
| 04 | metrics | `core/metrics.py` | 03 |
| 05 | flags-risk | `core/flags.py`, `core/risk.py` | 04 |
| 06 | database-neon | `db.py`, `models.py`, Alembic | 00 |
| 07 | api | `api/*.py`, `main.py` | 02–06, 08, 09 |
| 08 | ai-report | `ai/*` except recommend | 05 |
| 09 | recommendations | `ai/recommend.py`, `content/articles/` | 05 |
| 10 | frontend | `frontend/` | 07 |
| 11 | personas | `scripts/generate_personas.py` | 01, 02 |
| 12 | eval | `scripts/run_eval.py` | 05, 08, 11 |
| 13 | deploy | hosting, README, demo | all |

Shared config: `thresholds.yaml` → copy to `backend/config/thresholds.yaml`.

Build order: 01 → 02 → 11 → 03 → 04 → 05 → 06 → 08 → 09 → 07 → 10 → 12 → 13.
