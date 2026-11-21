"""Real prices for the real-user evaluation: the 20 project symbols plus the ones those users traded,
up to a later end date. Written to a separate directory so data/prices (demo + eval baseline) is untouched.

    cd backend && uv run python scripts/real_users/fetch_prices_ext.py <out_dir> [--end 2026-11-20]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fetch_prices as fp

EXTRA = {"BID": "Ngân hàng", "TPB": "Ngân hàng", "DXG": "Bất động sản", "DIG": "Bất động sản", "VIW": "Xây dựng"}


def main() -> None:  # pragma: no cover - needs network
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--start", default="2025-11-01")
    ap.add_argument("--end", default="2026-11-20")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "prices").mkdir(parents=True, exist_ok=True)
    for sym in [fp.INDEX, *fp.SYMBOLS, *EXTRA]:
        df = fp.normalize_frame(sym, fp.fetch_vndirect(sym, args.start, args.end))
        df.to_parquet(out / "prices" / f"{sym}.parquet", index=False)
        print(sym, len(df), df["date"].iloc[-1])
    (out / "sectors.json").write_text(json.dumps({**fp.SECTORS, **EXTRA}, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    (out / "SOURCE.json").write_text(json.dumps({"source": "VNDIRECT", "start": args.start, "end": args.end,
                                                 "simulated": False}), encoding="utf-8")


if __name__ == "__main__":
    main()
