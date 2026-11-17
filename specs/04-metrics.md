# 04 — Behavioral metrics

## Goal
One function that returns the full `Metrics` object from trades + prices.

## Files
`app/core/metrics.py`, `app/schemas.py` (Metrics), `tests/test_metrics.py`

## compute_metrics(trades, prices, profile, cfg) -> Metrics
Uses outputs of 03. All ratios as floats in [0, 1] unless noted.

| key | definition |
|---|---|
| period.start, end, months | first trade date, last price date, month count |
| concentration.hhi | Σ w² of symbol weights on last date |
| concentration.top_symbol, top_symbol_weight | largest weight |
| concentration.top_sector, top_sector_weight | largest sector weight |
| activity.monthly_turnover | list `{month, value}`: SELL value in month / mean V_t in month |
| activity.avg_turnover | mean of monthly_turnover |
| activity.trades_per_month | trade count / months |
| holding.avg_days_win, avg_days_loss | qty-weighted holding_days of Realized with realized > 0 / < 0 |
| disposition.pgr, plr, de, n_sell_days, n_sells | below |
| chasing.ratio, n_buys | share of BUYs where close[t−1]/close[t−1−lookback] − 1 ≥ rise |
| herding.lift, n_sells | (SELLs on drop days / n_sells) ÷ (drop days / sessions) |
| performance.* | twr, benchmark_return, excess, vol_annual, benchmark_vol, realized_pnl, unrealized_pnl, fees_total, tax_total (from 03) |

Drop day: VNINDEX daily return ≤ `herding.index_drop`; if `include_next_session`, the next session also counts.

## Disposition (Odean 1998)
For each day d with ≥ 1 SELL, for each symbol held at the start of d:
- sold on d: realized gain if sell_price > avg_cost, realized loss if <
- not sold: paper gain if `low_d > avg_cost`, paper loss if `high_d < avg_cost`, otherwise skip

Count positions, not shares. `pgr = RG/(RG+PG)`, `plr = RL/(RL+PL)` (0 if denominator 0), `de = pgr − plr`.

## Output
`Metrics = {formula_version, period, profile{tier, level}, metrics{...}}`. Flags are added in 05. Round floats to 4 decimals at serialization only.

## Acceptance
- Weights 0.5/0.3/0.2 → hhi 0.38.
- Sell day with A sold at gain, B paper gain, C paper loss → pgr 0.5, plr 0.0, de 0.5.
- Position with low ≤ avg_cost ≤ high and not sold → skipped.
- 10 BUYs, 3 after a ≥10% 5-session rise → chasing.ratio 0.3.
