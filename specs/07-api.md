# 07 — API

## Goal
FastAPI endpoints that wire core, DB, and AI together.

## Files
`app/main.py`, `app/api/{profiles,trades,reports,demo}.py`, `tests/test_api.py`

## Endpoints (prefix `/api`)
| method | path | body | returns |
|---|---|---|---|
| POST | /profiles | `{answers: int[5]}` | `{id, tier, level}` |
| POST | /profiles/{id}/trades | multipart `file` (CSV) | ValidationResult; on success replaces trades |
| GET | /profiles/{id}/trades | — | TradeRow[] |
| GET | /profiles/{id}/metrics | — | Metrics with flags and investor_type |
| POST | /profiles/{id}/reports | — | Report (cached by data_hash) |
| GET | /profiles/{id}/reports/latest | — | Report or 404 |
| GET | /profiles/{id}/articles | — | Article[3] |
| GET | /demo | — | `{persona_id, title, tier, description}[]` |
| POST | /demo/{persona_id}/load | — | `{id}` — new profile with persona answers + trades |
| GET | /template.csv | — | sample CSV |
| GET | /health | — | `{ok, db}` |

## Behavior
- Upload: `validate` → if errors return 422 with ValidationResult; else `apply_fees`, replace trades, return 200.
- Metrics: load trades → 03/04/05 → return. No trades → 409 "Chưa có dữ liệu giao dịch".
- Reports: compute metrics, hash, return cached report if hash matches, else call `build_report` (08) and save.
- PriceStore and thresholds load once at startup.
- CORS: allow `NEXT_PUBLIC` frontend origin from env.
- Errors: `{detail: str}` in Vietnamese.

## Acceptance
- Load P03 demo → metrics contain a disposition flag.
- Upload with an oversell row → 422, trades unchanged.
- Two report POSTs without data change → second returns same report id.
