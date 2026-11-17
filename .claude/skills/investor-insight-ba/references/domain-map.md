# Investor Insight — domain map

Read once per session. It orients you; it does not replace the specs. If anything here disagrees with the files, the files win — and tell the user this map is stale.

## What the product is
A web app where a retail investor uploads their own trade-history CSV and answers a 5-question risk questionnaire. Deterministic Python (`backend/app/core`) computes every metric, rules raise behavior flags, and an LLM only *explains* those metrics in Vietnamese, with guardrails that re-check every number and block buy/sell advice. MVP = one flow: CSV → validate → ledger/portfolio → metrics → flags → AI report + article recommendations → dashboard. Target market: Vietnamese equities (HOSE/HNX/UPCoM), data simulated for the MVP.

Two audiences shape every decision: (1) the end user — a retail investor reflecting on their own behavior; (2) the internship deliverable — Phần 3 of the BCTT at DSC Đà Nẵng and a CV project, which need *measured, defensible* numbers (precision/recall, guardrail pass rate, latency, 5-user survey).

## Where things live (authority order when sources disagree)
Default order; confirm with the user when a conflict actually changes the build.

| Question | Authority | File |
|---|---|---|
| What problem, scope, what is out, legal/market context, evaluation plan, report mapping | MVP plan | `contexts/Investor Insight – Kế hoạch xây dựng MVP.pdf` |
| How to build it: modules, models, endpoints, acceptance | specs | `specs/00–13-*.md`, order in `specs/README.md` |
| Numeric thresholds, fee tiers, guardrail tolerances | config | `specs/thresholds.yaml` (copied to `backend/config/`) — the plan itself says thresholds are *proposals to tune after eval* |
| Internship report format, deadlines, what Phần 2 / Phần 3 must contain | school guideline | `contexts/[BCTT] Tài liệu hướng dẫn.pptx` — only for report-related questions |
| What the user wants now | the user's message | overrides all of the above, but flag if it contradicts a fixed invariant |

Plan wins on intent and scope; specs win on implementation detail; `thresholds.yaml` wins on numbers. Spec files carry the dependency order: 01 → 02 → 11 → 03 → 04 → 05 → 06 → 08 → 09 → 07 → 10 → 12 → 13.

## Invariants (a request that breaks one is a finding, not a detail)
1. Every number shown to a user comes from `core`; the LLM never computes or invents a number.
2. No buy/sell/hold recommendation for any stock; no price prediction. The product explains *the user's own past behavior*.
3. Behaviors are signals for self-reflection, never psychological diagnoses; limits of the data are always stated.
4. Below the minimum sample (`min_sample`: 10 sells / 10 buys) the answer is `insufficient_data`, not a conclusion.
5. All thresholds in `thresholds.yaml`; no magic numbers in code. `core` is pure: no DB, HTTP or LLM.
6. Money is VND integer/Decimal, never float in the ledger. UI and LLM output in Vietnamese; code in English.
7. No identifying data (name, email, account number) goes to the model.
8. Data is simulated; the persona generator must not share thresholds with the detector (avoids circular evaluation).
9. Out of scope: auth, real brokerage connection, price prediction, derivatives, margin, dividends/splits.

## Cut order if the schedule slips (plan)
1. Chat Q&A → 2. article recommendations → 3. manual trade-entry form (keep CSV only). **The eval suite is never cut** — it produces the real numbers for the report and CV.

## Key dates (from the plan and school guideline)
MVP end-to-end with measured results by **2026-11-23** (roadmap 17–23/11, one runnable output per day). Report draft to GVHD 08/11 (passed), report approved by **29/11/2026**, defense **07–13/12/2026**.

## Team names appearing in the plan
Jayce wrote the plan (builds); Tuyền writes the report and is the one who can confirm things with DSC and the GVHD. Treat open "Tuyền to verify" items as external dependencies — do not guess their answers.

## Change-impact map
When a request changes X, these usually change too. List the ones that apply in your analysis.

| Change | Touches |
|---|---|
| Formula or threshold of a metric/flag | `thresholds.yaml` + `Thresholds` model; the `core` function and its hand-computed unit test; **bump `formula_version`** (cached reports are keyed by `sha256(trades + formula_version)`); `templates.py` text; frontend "Cách tính" popover; re-run eval and keep the old run under "Trước hiệu chỉnh" (spec 12); persona specs only if the *behavior* definition changes, never by importing thresholds |
| New metric or flag | 04 (definition + key), 05 (flag row, `evidence_keys`, sample gate), `FlagId` enum, 08 (template + guardrail allowed values), 09 (≥2 articles per flag id), 10 (a card), 11 (persona + label), 12 (eval row) |
| CSV column / validation rule | 02, 06 (`trades` table + CHECKs), 07 (`/template.csv`), 10 (upload error table), 11 (generator output) |
| Price data / symbol list | 01 (`fetch_prices`, `sectors.json`), every spec reading `PriceStore`, persona generator |
| LLM output schema or prompt | 08 schema + guardrails, cached `reports` rows, eval AI measurements |
| Fees or tax rule | `thresholds.yaml fees`, 02 `fees.py`, 03 realized P&L, plan "Việc cần xác minh" #3/#4 |
| New user-facing text | Vietnamese, footer disclaimer "không phải khuyến nghị đầu tư", AI label "Nội dung do AI tạo" |

## Glossary (VN ↔ code)
| Term | Meaning |
|---|---|
| disposition effect / hiệu ứng ngược vị thế | selling winners early, holding losers; PGR, PLR, `de = pgr − plr` (Odean 1998); positions whose avg cost lies between the day's low and high are skipped |
| PGR / PLR | proportion of gains / losses realized = realized ÷ (realized + paper) on days with ≥1 sell |
| HHI | Σ w² of symbol weights; concentration (`hhi_warn` 0.25, `top_symbol_warn` 0.40) |
| TWR | time-weighted return of the portfolio, flows removed; compared with VN-Index over the same window (`excess`) |
| vòng quay / turnover | monthly SELL value ÷ mean portfolio value that month |
| mua đuổi / chasing | share of BUYs after the stock rose ≥ 10% in the prior 5 sessions |
| bán theo đám đông / herding | `lift` of sells on VN-Index drop days (≤ −2%, plus next session) vs baseline |
| risk_mismatch / overconfidence | HHI or volatility above the self-declared tier's limit / overtrading AND return below VN-Index |
| tier / level | risk tier (conservative, balanced, growth) from the questionnaire score; experience level (beginner, intermediate, experienced) from question 2 |
| investor_type | rule-based label: "Giao dịch ngắn hạn", "Tập trung", "Nắm giữ dài hạn", "Cân bằng" |
| `insufficient_data` | pseudo-flag shown as "Chưa đủ dữ liệu" when the sample gate fails |
| giá điều chỉnh | adjusted close; used for signals; trades' own prices drive P&L |
| phiên / GDKHQ | trading session / ex-rights date (dividend, split — unsupported in MVP, a stated limitation) |
| lô chẵn / lô lẻ | round lot (multiples of 100) / odd lot (1–99) |
| biên độ | daily price band: HOSE ±7%, HNX ±10%, UPCoM ±15% (plan); violation is a warning, not a block |
| DSC, GVHD, ĐVTT, BCTT | host broker (Đà Nẵng branch), faculty supervisor, internship host unit, internship report |
| `formula_version`, `data_hash` | version tag of formulas; cache key of a report |
