# 01 — Price data

## Goal
Static daily price files committed to the repo, plus a lookup module.

## Files
`scripts/fetch_prices.py`, `app/core/prices.py`, `data/prices/*.parquet`, `data/sectors.json`, `tests/test_prices.py`

## fetch_prices.py
- `uv run python scripts/fetch_prices.py --source KBS --start 2025-11-01 --end 2026-10-31`
- Validate every row as `PriceBar(date, open, high, low, close: VND, volume: int ≥ 0)` with a model validator `low ≤ open, close ≤ high` before writing.
- Library: vnstock, daily OHLCV. Fallback `--source VCI` if KBS fails; print which source was used.
- `--source VNDIRECT`: VNDirect's public chart endpoint (`dchart-api.vndirect.com.vn/dchart/history`, adjusted, thousand VND), used because vnstock is no longer on PyPI. Only tickers and dates are sent.
- Symbols: VNINDEX + FPT, VCB, CTG, TCB, MBB, ACB, VPB, HDB, HPG, MWG, VNM, MSN, VIC, VHM, GAS, SSI, VND, PNJ, REE, DGC.
- Stock prices come in thousand VND and are already adjusted → multiply open/high/low/close by 1000. Do not multiply VNINDEX.
- Write `data/prices/{SYMBOL}.parquet` with columns `date, open, high, low, close, volume`.
- Write `data/sectors.json`: `{symbol: sector}` using: Ngân hàng (VCB, CTG, TCB, MBB, ACB, VPB, HDB), Công nghệ (FPT), Thép (HPG), Bán lẻ (MWG, PNJ), Tiêu dùng (VNM, MSN), Bất động sản (VIC, VHM), Năng lượng (GAS), Chứng khoán (SSI, VND), Tiện ích (REE), Hóa chất (DGC).
- Assertions before writing: every symbol has exactly VNINDEX's dates, no nulls, ~240–250 sessions.

## core/prices.py
```python
class PriceStore:
    def __init__(self, dir: Path): ...           # load all parquet once
    symbols: set[str]
    trading_days: list[date]                      # from VNINDEX
    def is_trading_day(self, d: date) -> bool
    def bar(self, symbol: str, d: date) -> Bar    # open/high/low/close
    def close_series(self, symbol: str) -> pd.Series
    def prev_session(self, d: date, n: int = 1) -> date
    def next_session(self, d: date) -> date | None
    sector(symbol) -> str
```

## Acceptance
- Unknown symbol or non-trading date raises a typed error.
- `prev_session(d, 5)` skips weekends/holidays using VNINDEX dates.
