"""Shared fixtures. Core tests never touch the DB."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

# 9 sessions: Mon 5 Jan .. Fri 16 Jan 2026 with Wed 14 Jan missing (a "holiday").
SESSIONS = [
    date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 8), date(2026, 1, 9),
    date(2026, 1, 12), date(2026, 1, 13), date(2026, 1, 15), date(2026, 1, 16),
]


def make_bars(closes: list[float], spread: float = 0.0) -> pd.DataFrame:
    """OHLCV frame on SESSIONS. open == close; high/low = close ± spread."""
    assert len(closes) == len(SESSIONS)
    return pd.DataFrame(
        {
            "date": SESSIONS,
            "open": closes,
            "high": [c + spread for c in closes],
            "low": [c - spread for c in closes],
            "close": closes,
            "volume": [1000] * len(SESSIONS),
        }
    )


@pytest.fixture
def price_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prices"
    d.mkdir()
    make_bars([1000, 1010, 1020, 990, 1000, 1005, 1015, 1025, 1030]).to_parquet(d / "VNINDEX.parquet")
    make_bars([10000, 10100, 10200, 9900, 10000, 10050, 10150, 10250, 10300], spread=100).to_parquet(
        d / "AAA.parquet"
    )
    make_bars([20000] * 9, spread=0).to_parquet(d / "BBB.parquet")
    (tmp_path / "sectors.json").write_text(json.dumps({"AAA": "Ngân hàng", "BBB": "Thép"}), encoding="utf-8")
    return d


def build_store(tmp_path, closes_by_symbol, sectors=None, spread=0.0):
    """PriceStore over SESSIONS with the given close series (open == close, optional high/low spread)."""
    from app.core.prices import PriceStore

    d = tmp_path / "prices"
    d.mkdir(exist_ok=True)
    for sym, closes in closes_by_symbol.items():
        make_bars(closes, spread=spread).to_parquet(d / f"{sym}.parquet")
    (tmp_path / "sectors.json").write_text(json.dumps(sectors or {}), encoding="utf-8")
    return PriceStore(d)


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory):
    """Full 21-symbol SIMULATED price set (same code path as `fetch_prices.py --synthetic`)."""
    from scripts.fetch_prices import SECTORS, normalize_frame, synthetic_frames

    root = tmp_path_factory.mktemp("synthetic")
    (root / "prices").mkdir()
    for sym, raw in synthetic_frames(date(2025, 11, 1), date(2026, 10, 31)).items():
        normalize_frame(sym, raw).to_parquet(root / "prices" / f"{sym}.parquet", index=False)
    (root / "sectors.json").write_text(json.dumps(SECTORS, ensure_ascii=False), encoding="utf-8")
    return root / "prices"


@pytest.fixture(scope="session")
def synthetic_store(synthetic_dir):
    from app.core.prices import PriceStore

    return PriceStore(synthetic_dir)


# Tests must never reach real services through backend/.env (real DB, real LLM key). Empty environment
# variables take precedence over dotenv values, so blank them for the whole session.
for _name in ("GEMINI_API_KEY", "LLM_API_KEY", "LLM_PROVIDER", "LLM_MODEL", "DATABASE_URL",
              "DATABASE_URL_DIRECT", "TEST_DATABASE_URL"):
    os.environ[_name] = ""
