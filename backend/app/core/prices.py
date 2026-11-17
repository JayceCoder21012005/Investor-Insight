"""Static daily price lookup. Pure: reads parquet once, no network."""
from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from datetime import date
from pathlib import Path

import pandas as pd

from app.schemas import Bar

INDEX_SYMBOL = "VNINDEX"


class PriceError(Exception):
    """Base class for price lookup errors."""


class UnknownSymbolError(PriceError):
    pass


class NotTradingDayError(PriceError):
    pass


class PriceStore:
    def __init__(self, dir: Path, sectors_path: Path | None = None):
        dir = Path(dir)
        self._frames: dict[str, pd.DataFrame] = {}
        for f in sorted(dir.glob("*.parquet")):
            df = pd.read_parquet(f)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            self._frames[f.stem.upper()] = df.set_index("date").sort_index()
        if INDEX_SYMBOL not in self._frames:
            raise PriceError(f"{INDEX_SYMBOL}.parquet not found in {dir}")
        self.symbols: set[str] = set(self._frames)
        self.trading_days: list[date] = list(self._frames[INDEX_SYMBOL].index)
        self._day_set = set(self.trading_days)
        sp = sectors_path if sectors_path is not None else dir.parent / "sectors.json"
        self._sectors: dict[str, str] = (
            json.loads(Path(sp).read_text(encoding="utf-8")) if Path(sp).exists() else {}
        )

    def _frame(self, symbol: str) -> pd.DataFrame:
        try:
            return self._frames[symbol]
        except KeyError:
            raise UnknownSymbolError(symbol) from None

    def is_trading_day(self, d: date) -> bool:
        return d in self._day_set

    def bar(self, symbol: str, d: date) -> Bar:
        frame = self._frame(symbol)
        if d not in self._day_set or d not in frame.index:
            raise NotTradingDayError(str(d))
        row = frame.loc[d]
        return Bar(open=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
                   close=float(row["close"]))

    def close_series(self, symbol: str) -> pd.Series:
        return self._frame(symbol)["close"]

    def prev_session(self, d: date, n: int = 1) -> date:
        """The trading session n sessions before d (d itself may be any date)."""
        idx = bisect_left(self.trading_days, d) - n
        if idx < 0:
            raise NotTradingDayError(f"no session {n} before {d}")
        return self.trading_days[idx]

    def next_session(self, d: date) -> date | None:
        idx = bisect_right(self.trading_days, d)
        return self.trading_days[idx] if idx < len(self.trading_days) else None

    def sector(self, symbol: str) -> str:
        if symbol not in self._sectors:
            raise UnknownSymbolError(symbol)
        return self._sectors[symbol]
