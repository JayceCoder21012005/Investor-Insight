"""Run the real-user CSVs through the core pipeline (no LLM), in two variants:

- raw: trade prices as written;
- adjusted: a fill more than 5% outside the session range is moved to the (adjusted) close, with the
  quantity scaled so that price x quantity is unchanged. VNDIRECT bars are adjusted for stock dividends
  and bonus shares while broker fills are nominal, so old fills otherwise look like large losses.

Sells of a symbol never bought in the file (history cut off) are dropped and listed, since the API would
reject the whole file. Users have no questionnaire answers, so the default balanced answers are assumed.

    cd backend && uv run python scripts/real_users/eval_core.py <prices_dir_parent> <out.json>
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.config import load_thresholds
from app.core.fees import apply_fees
from app.core.flags import annotate
from app.core.metrics import compute_metrics
from app.core.prices import PriceStore
from app.core.risk import score
from app.core.validate import _row_payload, validate
from app.schemas import Side, TradeRow

ANSWERS = [2, 2, 3, 3, 2]
FILES = ["Nhật Nam.csv", "Noname.csv", "Thăng Long.csv", "Đào Lệ Tuyền.csv", "Đình Trọng.csv"]
PERSONAS = Path(__file__).resolve().parents[2] / "data" / "personas"


def parse_all(raw: bytes) -> list[TradeRow]:
    rows = []
    for n, rec in enumerate(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))), 1):
        if any((v or "").strip() for v in rec.values()):
            rows.append(TradeRow.model_validate(_row_payload(n, rec)))
    return rows


def drop_orphan_sells(rows: list[TradeRow]) -> tuple[list[TradeRow], list[int]]:
    held: dict[str, int] = {}
    keep, dropped = [], []
    for r in sorted(rows, key=lambda t: (t.trade_date, t.row_no)):
        if r.side == Side.BUY:
            held[r.symbol] = held.get(r.symbol, 0) + r.quantity
            keep.append(r)
        elif r.quantity <= held.get(r.symbol, 0):
            held[r.symbol] -= r.quantity
            keep.append(r)
        else:
            dropped.append(r.row_no)
    return keep, dropped


def rescale(rows: list[TradeRow], store: PriceStore) -> tuple[list[TradeRow], int]:
    out, n = [], 0
    for r in rows:
        bar = store.bar(r.symbol, r.trade_date)
        if bar.low * 0.95 <= r.price <= bar.high * 1.05:
            out.append(r)
            continue
        factor = bar.close / r.price
        out.append(r.model_copy(update={"price": round(bar.close), "quantity": max(1, round(r.quantity / factor))}))
        n += 1
    return out, n


def main() -> None:
    data, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    store = PriceStore(data / "prices", data / "sectors.json")
    cfg = load_thresholds(Path(__file__).resolve().parents[2] / "config" / "thresholds.yaml")
    res = {}
    for i, name in enumerate(FILES, 1):
        raw = (PERSONAS / name).read_bytes()
        v = validate(raw, store)
        entry: dict = {"errors": [e.message for e in v.errors], "warnings": [w.message for w in v.warnings]}
        rows = v.rows
        if v.errors:
            rows, entry["dropped_orphan_sells"] = drop_orphan_sells(parse_all(raw))
        for variant in ("raw", "adjusted"):
            rr, n = (rows, 0) if variant == "raw" else rescale(rows, store)
            m = annotate(compute_metrics(apply_fees(rr, cfg), store, score(ANSWERS, cfg), cfg), cfg)
            entry[variant] = {"rescaled_rows": n, "metrics": json.loads(m.model_dump_json())}
        res[f"U{i}"] = entry
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
