# 03 — Ledger and portfolio

## Goal
Positions, realized P&L, holding periods, daily portfolio value and returns.

## Files
`app/core/ledger.py`, `app/core/portfolio.py`, `tests/test_ledger.py`, `tests/test_portfolio.py`

## ledger.py
State per symbol: `qty`, `avg_cost`, `lots` (FIFO deque of `(date, qty)`).

```python
BUY:  avg_cost = (qty*avg_cost + q*price + fee) / (qty + q)
      qty += q; lots.append((date, q))
SELL: realized = q*(price - avg_cost) - fee - tax
      ret = price/avg_cost - 1
      holding_days = qty-weighted calendar days of lots consumed FIFO
      qty -= q            # avg_cost unchanged; reset to 0 when qty == 0
```

Outputs:
- `Realized(symbol, date, qty, sell_price, avg_cost, realized, ret, holding_days)` per SELL
- `snapshots: dict[date, dict[symbol, Position(qty, avg_cost)]]` at start and end of each trading day from first trade to last price date

Average cost drives P&L; FIFO lots only drive holding period.

## portfolio.py
For each trading day t from first trade date:
- `V_t = Σ qty × close_t` (end-of-day positions)
- `flow_t = Σ BUY value − Σ SELL value` on t (gross, before fees)
- `r_t = (V_t − flow_t) / V_{t−1} − 1` if `V_{t−1} > 0`, else skip
- `twr = Π(1 + r_t) − 1`
- `vol_annual = std(r_t, ddof=1) × sqrt(250)`
- `benchmark_vol` = the same formula on VN-Index daily returns over the portfolio's sessions (first to last day); 0 with fewer than 2 returns. Used by `risk_mismatch` (spec 05, formula 0.3).
- `benchmark_return = VNINDEX_close[last] / VNINDEX_close[first] − 1` (same window)
- `excess = twr − benchmark_return`
- `unrealized_pnl = Σ qty × (close_last − avg_cost)`
- `weights_last`: by symbol and by sector

## Acceptance
- BUY 100 @10,000 fee 3,000; BUY 100 @12,000 fee 3,600 → avg_cost 11,033.
- Then SELL 100 @13,000 fee 3,900 tax 1,300 → realized 191,500, avg_cost still 11,033.
- Lots (Jan 1, 100), (Feb 1, 100); SELL 150 on Mar 1 → holding_days = (59×100 + 28×50)/150.
- Two days, no flows, V 100→110 → r = 0.10.
