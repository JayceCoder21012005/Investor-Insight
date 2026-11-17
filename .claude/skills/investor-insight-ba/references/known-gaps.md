# Known gaps — snapshot as of 2026-11-17

A dated list of discrepancies and open items found while reading `specs/` against the MVP plan. **Re-verify each against the current files before you repeat it** — some will have been fixed, and a stale claim damages trust in the whole analysis. When one is fixed, delete the row. When you find a new one while doing a BA pass, add it here with the date.

## Plan ↔ specs discrepancies
| # | Topic | Plan says | Spec says | Why it matters |
|---|---|---|---|---|
| 1 | Price-band check | CSV price must lie within the session band: HOSE ±7%, HNX ±10%, UPCoM ±15%; breach = warning only (plan §Kiểm tra dữ liệu đầu vào, table row 8 "Lô và biên độ") | `02-csv-validation` warns if price is outside `[day_low×0.95, day_high×1.05]`; no exchange attribute exists in `sectors.json`/`PriceStore` | The spec's check is a different rule, and exchange per symbol is not stored. Decide: adopt the exchange bands (needs a symbol→exchange map in 01) or keep the simplified rule and record the deviation |
| 2 | Number of simulated profiles | 10 profiles (5 single trait, 2 double, 2 control, 1 low-data) | `11-personas` defines 11 (adds P11 herding) × 3 seeds = 33 files | Report text and eval tables must quote the same number; plan has a herding metric, so P11 is plausible — confirm and align the plan wording |
| 3 | Article recommendation method | Step 7 of the flow: semantic search over 20–30 articles | `09-recommendations`: tag + level score; embeddings only as an optional upgrade | Report wording ("tìm kiếm ngữ nghĩa") would over-claim vs what is built |
| 4 | Holding-time indicator | Plan lists "Thời gian nắm giữ" with warning sign "lệnh lỗ giữ lâu hơn lệnh lời rõ rệt", linked to loss aversion | `04` computes `holding.avg_days_win/loss`, `05` has no flag for it (used only as evidence of `disposition`); `thresholds.yaml` has no holding threshold | The plan implies a warning that no spec implements; either drop it from the plan table or add a flag (touches 05, 08, 09, 10, 11, 12) |
| 5 | Fee schedule by account type | Plan #4: advisory-managed accounts 0.1%; broker-managed tiered by daily value | `02`/`thresholds.yaml` implement only the broker tiers; CSV has no account-type field | Fine for simulated data, but a real DSC export may need an account-type switch; also tier boundary wording ("dưới 100 triệu" vs "100–300 triệu") vs spec "upper bound exclusive" should be checked at exactly 100M/300M/500M |

## Inside specs
| # | Where | Issue |
|---|---|---|
| 6 | `08-ai-report` Output schema | The prose puts `evidence_keys` and `flag_id` on `ReportContent`, while the JSON shape and the rules put them on each `Insight`; also "summary ≤ 60 words" in the shape vs `max_length=600` characters in the field. Clarify before the schema is implemented because the guardrail reads these fields |
| 7 | `06-database-neon` | Contains what looks like a **live Neon connection string with the password inline**. Should be rotated and replaced with a placeholder; never quote it in outputs |

## Found while building (2026-11-17) — resolved in code (items 12, 13, 18 also in specs)
| # | Where | Gap | How the build resolved it |
|---|---|---|---|
| 8 | `10-frontend` vs `07-api` | Dashboard needs the rebased portfolio/VN-Index series and weights by symbol/sector, but `Metrics` carries neither | Added `GET /api/profiles/{id}/portfolio` |
| 9 | `10-frontend` vs `07-api` | Cards must show "value vs threshold" but the frontend may hold no business logic, and thresholds live only in the backend | Added `GET /api/thresholds` |
| 10 | `11-personas` labels vs `05-flags` sample gate | Any history with fewer than `min_sample` sells/buys gets `insufficient_data`, yet only P10 is labeled with it | Labels extended for personas that by design never sell enough (P02, P04, P05, P07, P08); P09 left unlabeled on purpose |
| 11 | `05-flags` spike rule | "month > 2 × mean of previous 3" fires on tiny baselines (1% → 3% turnover) | Added `turnover.spike_min_value` (0.5), `formula_version` 0.2; eval precision for overtrading 35% → 55% (33% → 71% on the first data set) |
| 12 | `04-metrics` HHI / `05` risk tiers | Last-day HHI; conservative `hhi_max` 0.20 = five equal stocks; absolute `vol_max` 0.18 below the index's own volatility | Measured first: time-averaged HHI was *worse* (P04/P10 start with few stocks), so HHI stays last-day. Most false alarms came from persona bugs (P08 lot rounding skipped expensive stocks; P07 chasing diluted the main stock). Formula 0.3: conservative `hhi_max` 0.25; `vol_ratio_max` × `benchmark_vol` (VN-Index, same sessions) replaces `vol_max` (1.3/1.6/2.0); `spike_min_value` = `monthly_warn` (1.0) |
| 13 | `05-flags` overconfidence | Defined on outcome (excess < 0), which no persona declares | `run_eval` derives its label: labeled `overtrading` AND excess < 0 (spec 12 updated) |
| 18 | `01-prices` vnstock | vnstock is no longer on PyPI (404) | `--source VNDIRECT` (public dchart endpoint, adjusted); real prices in the repo since 2026-11-17. Chaser persona now waits up to 40 sessions for a hot stock (real gaps reach 35) |
| 14 | `08-ai-report` guardrail | Number check rejected month/year of the analysis period ("tháng 11 năm 2025") and abs. values ("thấp hơn 5,2%" for −0.052); 1% tolerance accepts 2025 as 2026 | Period date parts matched exactly; absolute value accepted |
| 15 | `02-csv` row numbers | Spec says "1-based row number" without saying whether the header counts | Data rows are numbered from 1, header excluded; the UI says so |
| 16 | `09-recommendations` | Multi-tag articles dominate the 2×overlap score, so a user with 3 flags can get 3 articles about the same one | Each article carries one flag tag; ties break by id |
| 17 | `06-database-neon` / `.env` | `.env` line 1 (`DATABASE_URL`) is not parsed by python-dotenv; values should be unquoted, one per line | Reported to the user; `.env.example` documents the format |

## Open items waiting on a person (do not guess)
- GVHD agreement to place the product in section 3.1 and use simulated data — blocks report writing, not the build (plan #5).
- What DSC ChatAI / WeTrade / Chatbot actually do, and whether DSC already analyzes behavior on trade data (plan #1, #2).
- How DSC computes realized P&L; MVP uses weighted average cost until compared on DSC Trading (plan #3).
- Real DSC order-history export, to fix the CSV column names (plan, "Việc còn lại cho Tuyền").
- Behavior around ex-rights dates: real CSVs will deviate from adjusted prices — a recorded limitation, not a bug (plan #10).
