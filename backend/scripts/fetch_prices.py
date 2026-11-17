"""Download daily OHLCV for VNINDEX + 20 stocks and write parquet files.

    uv run python scripts/fetch_prices.py --source KBS --start 2025-11-01 --end 2026-10-31

vnstock is imported lazily because it may not be installable everywhere. When it is not,
`--synthetic` writes a deterministic *simulated* price set (clearly marked in data/SOURCE.json)
so the rest of the pipeline can be developed and tested. Never present synthetic prices as real.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.schemas import PriceBar

INDEX = "VNINDEX"
SYMBOLS = [
    "FPT", "VCB", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "HPG", "MWG",
    "VNM", "MSN", "VIC", "VHM", "GAS", "SSI", "VND", "PNJ", "REE", "DGC",
]
SECTORS = {
    **{s: "Ngân hàng" for s in ["VCB", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB"]},
    "FPT": "Công nghệ", "HPG": "Thép", "MWG": "Bán lẻ", "PNJ": "Bán lẻ",
    "VNM": "Tiêu dùng", "MSN": "Tiêu dùng", "VIC": "Bất động sản", "VHM": "Bất động sản",
    "GAS": "Năng lượng", "SSI": "Chứng khoán", "VND": "Chứng khoán",
    "REE": "Tiện ích", "DGC": "Hóa chất",
}
COLUMNS = ["date", "open", "high", "low", "close", "volume"]


class PriceDataError(Exception):
    pass


def normalize_frame(symbol: str, raw: pd.DataFrame) -> pd.DataFrame:
    """vnstock frame -> validated frame. Stock prices (thousand VND) become VND; VNINDEX unchanged."""
    df = raw.copy()
    if "time" in df.columns:
        df = df.rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    scale = 1 if symbol == INDEX else 1000
    for col in ("open", "high", "low", "close"):
        df[col] = (df[col].astype(float) * scale).round(0 if scale == 1000 else 2)
    df["volume"] = df["volume"].fillna(0).astype(int)
    df = df[COLUMNS].sort_values("date").reset_index(drop=True)
    for row in df.to_dict("records"):
        try:
            PriceBar.model_validate(row)
        except ValidationError as e:
            raise PriceDataError(f"{symbol} {row['date']}: {e.errors()[0]['msg']}") from e
    return df


def check_consistency(frames: dict[str, pd.DataFrame], min_sessions: int = 240,
                      max_sessions: int = 250) -> None:
    ref = list(frames[INDEX]["date"])
    if not (min_sessions <= len(ref) <= max_sessions):
        raise PriceDataError(f"{INDEX} has {len(ref)} sessions, expected {min_sessions}-{max_sessions}")
    for sym, df in frames.items():
        if df[COLUMNS].isnull().any().any():
            raise PriceDataError(f"{sym} has null values")
        if list(df["date"]) != ref:
            raise PriceDataError(f"{sym} dates differ from {INDEX}")


# ---------------------------------------------------------------- sources
def fetch_vnstock(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    try:
        from vnstock import Vnstock  # type: ignore
    except ImportError as e:  # pragma: no cover - environment dependent
        raise SystemExit("vnstock is not installed. `uv add vnstock`, or use --synthetic for dev data.") from e
    stock = Vnstock().stock(symbol=symbol, source=source)  # pragma: no cover
    return stock.quote.history(start=start, end=end, interval="1D")  # pragma: no cover


DCHART_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
VN_TZ = "Asia/Ho_Chi_Minh"


def parse_dchart(symbol: str, payload: dict) -> pd.DataFrame:
    """VNDirect dchart JSON (t/o/h/l/c/v arrays, adjusted, stocks in thousand VND) -> vnstock-style frame."""
    if payload.get("s") != "ok" or not payload.get("t"):
        raise PriceDataError(f"{symbol}: no data from VNDirect ({payload.get('s') or payload})")
    when = pd.to_datetime(payload["t"], unit="s", utc=True).tz_convert(VN_TZ).tz_localize(None).normalize()
    return pd.DataFrame({"time": when, "open": payload["o"], "high": payload["h"], "low": payload["l"],
                         "close": payload["c"], "volume": payload["v"]})


def fetch_vndirect(symbol: str, start: str, end: str) -> pd.DataFrame:  # pragma: no cover - needs network
    """Daily bars from VNDirect's public chart endpoint. Only the ticker and the dates are sent."""
    import httpx

    lo = int(pd.Timestamp(start, tz=VN_TZ).timestamp())
    hi = int((pd.Timestamp(end, tz=VN_TZ) + pd.Timedelta(days=1)).timestamp()) - 1
    r = httpx.get(DCHART_URL, params={"resolution": "D", "symbol": symbol, "from": lo, "to": hi},
                  headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return parse_dchart(symbol, r.json())


VN_HOLIDAYS = {
    date(2026, 1, 1), date(2026, 4, 27), date(2026, 4, 30), date(2026, 5, 1),
    date(2026, 9, 1), date(2026, 9, 2),
    *[date(2026, 2, d) for d in range(16, 21)],  # Tet
}


def trading_calendar(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in VN_HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    return days


def synthetic_frames(start: date, end: date, seed: int = 3) -> dict[str, pd.DataFrame]:
    """Deterministic correlated random walks, in vnstock units (stocks in thousand VND)."""
    rng = np.random.default_rng(seed)
    days = trading_calendar(start, end)
    n = len(days)
    # Student-t(4) innovations: fat tails like real markets (variance of t4 is 2).
    mkt = 0.0003 + 0.013 * rng.standard_t(4, n) / np.sqrt(2)
    base = {"FPT": 100, "VCB": 60, "CTG": 35, "TCB": 35, "MBB": 25, "ACB": 25, "VPB": 20,
            "HDB": 25, "HPG": 27, "MWG": 70, "VNM": 60, "MSN": 70, "VIC": 120, "VHM": 80,
            "GAS": 70, "SSI": 30, "VND": 20, "PNJ": 90, "REE": 65, "DGC": 70}

    def build(start_px: float, rets: np.ndarray, tick: float, vol_scale: int, noise: float) -> pd.DataFrame:
        close = start_px * np.cumprod(1 + rets)
        open_ = np.concatenate([[start_px], close[:-1]]) * (1 + rng.normal(0, noise / 3, n))
        close = np.round(close / tick) * tick
        open_ = np.round(open_ / tick) * tick
        hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, noise, n)))
        lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, noise, n)))
        hi, lo = np.round(hi / tick) * tick, np.round(lo / tick) * tick
        hi, lo = np.maximum(hi, np.maximum(open_, close)), np.minimum(lo, np.minimum(open_, close))
        return pd.DataFrame({"time": pd.to_datetime(days), "open": open_, "high": hi, "low": lo,
                             "close": close, "volume": rng.integers(vol_scale, vol_scale * 10, n)})

    frames = {INDEX: build(1700.0, mkt, 0.01, 500_000_000, 0.004)}
    for sym in SYMBOLS:
        beta = rng.uniform(0.7, 1.3)
        rets = beta * mkt + 0.016 * rng.standard_t(4, n) / np.sqrt(2)
        frames[sym] = build(float(base[sym]), rets, 0.01, 1_000_000, 0.006)
    return frames


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="KBS")
    ap.add_argument("--start", default="2025-11-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--out", default=str(ROOT / "data"))
    ap.add_argument("--synthetic", action="store_true", help="simulated prices for offline dev")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "prices").mkdir(parents=True, exist_ok=True)
    if args.synthetic:
        raw = synthetic_frames(date.fromisoformat(args.start), date.fromisoformat(args.end))
        used = "SYNTHETIC"
        print("WARNING: writing SIMULATED prices (not real market data)")
    elif args.source.upper() == "VNDIRECT":  # pragma: no cover - needs network
        used = "VNDIRECT"
        raw = {sym: fetch_vndirect(sym, args.start, args.end) for sym in [INDEX, *SYMBOLS]}
        print("source used: VNDIRECT (dchart, adjusted daily bars)")
    else:  # pragma: no cover - needs network
        used, raw = args.source, {}
        for sym in [INDEX, *SYMBOLS]:
            try:
                raw[sym] = fetch_vnstock(sym, args.start, args.end, args.source)
            except Exception as e:
                if args.source != "KBS":
                    raise
                print(f"{sym}: KBS failed ({e}); falling back to VCI")
                used = "VCI"
                raw[sym] = fetch_vnstock(sym, args.start, args.end, "VCI")
        print(f"source used: {used}")

    frames = {sym: normalize_frame(sym, df) for sym, df in raw.items()}
    check_consistency(frames, min_sessions=240 if not args.synthetic else 200)
    for sym, df in frames.items():
        df.to_parquet(out / "prices" / f"{sym}.parquet", index=False)
    (out / "sectors.json").write_text(json.dumps(SECTORS, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "SOURCE.json").write_text(
        json.dumps({"source": used, "start": args.start, "end": args.end,
                    "simulated": bool(args.synthetic)}, indent=2), encoding="utf-8")
    print(f"wrote {len(frames)} symbols x {len(frames[INDEX])} sessions to {out}")


if __name__ == "__main__":
    main()
