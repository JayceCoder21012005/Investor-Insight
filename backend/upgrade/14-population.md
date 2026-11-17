# 14 — Synthetic population (for clustering)

## Goal
Generate a large, **unlabeled**, behaviorally diverse population of synthetic investors so spec 15 can cluster them. Unlike spec 11 (11 fixed archetypes with labels), every investor here draws **continuous** behavior parameters, so the population has no built-in groups.

## Files
- `backend/scripts/generate_population.py` (new)
- `backend/scripts/population_spec.yaml` (new)
- Output: `backend/data/population/` → `INV0001.csv … INV0400.csv` + `params.json`
- Add `data/population/` to `.gitignore` **and** `backend/.dockerignore` (regenerable, must not enter the image)

## Command
`uv run python scripts/generate_population.py --n 400 --seed 42`

## Rules
- Reuse `Sim`, lot rounding, price noise and cash tracking from `generate_personas.py` by **importing** them. Do not copy code.
- Must not import `app.config` or read `thresholds.yaml` (same independence rule as spec 11).
- Deterministic: same `--n` and `--seed` → identical files.
- CSV format identical to persona files (fees/tax blank, applied on load).

## Parameters per investor (drawn once; ranges live in `population_spec.yaml`)
| Param | Distribution | Drives |
|---|---|---|
| `trades_per_month` | log-uniform [1, 30] | activity |
| `pool_size` | int uniform [1, 12] | concentration |
| `size_pct` | uniform [0.05, 0.40] of equity per buy | concentration, risk |
| `base_exit` | uniform [0.02, 0.15] daily sell prob per position | holding period |
| `disposition` | uniform [0, 0.9] | sell prob × (1+d) when in gain, × (1−d) when in loss |
| `chase` | uniform [0, 1] | prob a buy picks from the top-rising symbols of the last 5 sessions |
| `herd` | uniform [0, 1] | prob of selling a position on a day VN-Index fell sharply (own trigger drawn in [−3%, −1.5%]) |
| `capital` | from `common.capital` | — |

Loop per trading day: (1) sell decisions per held position, (2) herd sells, (3) buys at a rate matching `trades_per_month`, choosing chase vs. random pick, respecting cash and lot size.

## Output `params.json`
`{ "INV0001": { "trades_per_month": …, "pool_size": …, "disposition": …, "chase": …, "herd": …, … }, … }` — ground truth for **after-the-fact interpretation only**, never used as a clustering input.

## Tests (`tests/test_population.py`)
- Same seed → byte-identical CSVs; different seed → different.
- Every generated CSV passes `validate` with zero errors.
- Higher `disposition` → higher computed `de` (Spearman ρ > 0 on n=100).
- Higher `trades_per_month` → higher computed `avg_turnover` (ρ > 0.5).

## Done when
400 files generated in < 60 s, all valid, tests green, nothing under `data/population/` is tracked by git.
