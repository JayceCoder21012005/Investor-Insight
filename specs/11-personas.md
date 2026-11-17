# 11 — Synthetic personas

## Goal
Generate labeled trade histories with known behaviors, for demo and evaluation.

## Files
`scripts/persona_specs.yaml`, `scripts/generate_personas.py`, `data/personas/{id}_s{seed}.csv`, `data/personas/labels.json`, `data/personas/answers.json`

## Rules
- The generator reads only `persona_specs.yaml` and price files. It must not import `thresholds.yaml` or `app.core.flags`.
- Behavior parameters are drawn from ranges so some cases fall near or below detection thresholds.
- `persona_specs.yaml` is loaded into a pydantic `PersonaSpec` model (ranges as `tuple[float, float]` with `lo <= hi` validator).
- `uv run python scripts/generate_personas.py --seeds 3` → 11 personas × 3 seeds = 33 CSVs. Deterministic per seed.

## Common mechanics
- Start capital U(300M, 800M); quantities in lots of 100; never spend more cash than available.
- Trade price = adjusted close × U(0.995, 1.005), clipped to [low, high], rounded to 10 VND.
- Leave `fee`/`tax` blank; fees are applied by spec 02 on load.
- Period: whole price window.
- Periodic buys (P08) keep a budget per stock; what a round lot cannot use carries over to the next month, so expensive stocks are still bought.

## Personas
| id | tier answers | behavior | labels |
|---|---|---|---|
| P01 | balanced | 15–25 trades/month, hold 2–10 sessions | overtrading |
| P02 | growth | one stock kept at 45–55% of value, rest spread over 4–5 | concentration |
| P03 | balanced | sell winners at +5–12%, hold losers until −25% or end | disposition |
| P04 | balanced | 50–70% of buys after a 5-session rise of 8–15% | chasing |
| P05 | conservative | 3–4 of SSI, VND, DGC, HPG; low trading | risk_mismatch |
| P06 | growth | P01 + P03 | overtrading, disposition |
| P07 | growth | P02 + P04 | concentration, chasing |
| P08 | conservative | monthly equal buys of VCB, ACB, VNM, FPT, PNJ; no sells | — |
| P09 | balanced | 8–10 stocks, quarterly rebalance to equal weight | — |
| P10 | balanced | 6 trades total | insufficient_data |
| P11 | balanced | ~60% of sells on VNINDEX ≤ −2% days or next session | herding |

`answers.json`: questionnaire answers per persona that score into its tier. `labels.json`: `{"P03_s1": ["disposition"], ...}`.

## Acceptance
- Every CSV passes spec 02 validation with zero errors.
- Same seed → identical output.
