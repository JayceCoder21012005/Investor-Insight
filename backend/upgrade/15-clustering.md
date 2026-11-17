# 15 — Behavior clustering (KMeans, offline analysis)

## Goal
Exploratory segmentation of the spec 14 population by behavior, then compare clusters with the rule-based `investor_type`. **Offline analysis only**: no API, no frontend, no DB, nothing added to the Docker image.

## Files
- `backend/scripts/run_clustering.py` (new)
- `backend/app/analysis/features.py` (new; pure functions, unit-tested)
- Output: `eval/clustering.json`, `eval/clustering.md`, `eval/figures/{elbow_silhouette,pca_clusters,centroids}.png`

## Dependencies
`uv add --dev scikit-learn matplotlib` (dev group only, so the production image is unchanged).

## Command
`uv run python scripts/run_clustering.py [--population data/population] [--k auto|3..6]`

## 1. Features (one row per investor, from `analyze` output, i.e. `Metrics`)
| Feature | Source | Transform |
|---|---|---|
| `turnover` | `activity.avg_turnover` | `log1p` |
| `trades_pm` | `activity.trades_per_month` | `log1p` |
| `hhi` | `concentration.hhi` | none |
| `hold_days` | `holding.avg_days` | `log1p` |
| `de` | `disposition.de` | none |
| `chasing` | `chasing.ratio` | none |
| `herding` | `herding.lift` | `log1p` |
| `vol_ratio` | `performance.vol_annual / performance.benchmark_vol` | none |

**Excluded on purpose:** `excess`, `twr`, P&L (outcomes, not behavior); `top_symbol_weight` (duplicates `hhi`); risk answers/tier (self-reported, used only for comparison).

## 2. Cleaning (in `features.py`)
1. **Eligibility:** drop investors with `disposition.n_sells < cfg.min_sample.sells`, `chasing.n_buys < cfg.min_sample.buys`, or `holding.avg_days is None`. Never fill missing behavior with 0. Report how many were dropped.
2. Apply transforms from the table.
3. Winsorize every feature at the 1st/99th percentile.
4. `StandardScaler`.
5. Correlation check: if any pair has |r| > 0.8, drop the one listed later in the table and log it.

## 3. Model
- `KMeans(n_init=20, random_state=0)` for k = 2…7; record inertia and silhouette.
- `--k auto` = highest silhouette among k ∈ [3, 6].
- Stability: refit chosen k with `random_state` 0–4; mean pairwise ARI must be reported (target > 0.8).

## 4. Interpretation
- Centroids back-transformed to original units + cluster sizes.
- Vietnamese name per cluster written from centroids (e.g. "Giao dịch dày, giữ ngắn"); names live in a small dict in the script, set after inspecting results.
- Crosstab cluster × rule-based `investor_type`; ARI between them.
- Mean of each generator param (`params.json`) per cluster: checks whether clusters recover the hidden behaviors.
- PCA 2-D scatter colored by cluster.

## 5. `clustering.md` (Vietnamese, ready for the report)
Data note (synthetic, n, dropped) → chosen k + why → centroid table → crosstab vs investor_type → param recovery table → figures → limitations:
- synthetic data, so this demonstrates the method, not real investor segments;
- KMeans assumes roughly spherical clusters;
- results depend on the feature choice.

## Tests (`tests/test_features.py`)
- Eligibility drops the right rows; no NaN reaches the scaler.
- Winsorize clips to percentiles; transforms are applied once.
- Same population + seed → identical labels and `clustering.json`.

## Done when
Script runs end-to-end in < 2 min, writes all outputs, tests green, `git diff` touches nothing under `app/api`, `app/core`, `frontend/`, or `Dockerfile`.
