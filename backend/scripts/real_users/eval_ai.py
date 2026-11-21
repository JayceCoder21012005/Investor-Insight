"""AI reports for the real users (adjusted variant from eval_core.py), 3 runs each. Only metrics are sent
to the model: no names, no files. Needs GEMINI_API_KEY (or LLM_API_KEY) in backend/.env.

    cd backend && uv run python scripts/real_users/eval_ai.py <prices_dir_parent> <core.json> <out.json>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.ai.llm import build_llm
from app.ai.report import build_report
from app.config import Settings, load_thresholds
from app.core.prices import PriceStore
from app.schemas import Metrics

RUNS = 3


def main() -> None:  # pragma: no cover - calls the LLM
    data, src, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    store = PriceStore(data / "prices", data / "sectors.json")
    cfg = load_thresholds(Path(__file__).resolve().parents[2] / "config" / "thresholds.yaml")
    llm = build_llm(Settings())
    if llm is None:
        raise SystemExit("no LLM key configured")
    res = {}
    for user, entry in json.loads(src.read_text(encoding="utf-8")).items():
        m = Metrics.model_validate(entry["adjusted"]["metrics"])
        runs = []
        for _ in range(RUNS):
            r = build_report(m, llm, cfg, frozenset(store.symbols))
            runs.append({"model": r.model, "attempts": r.attempts, "passed": r.passed, "latency_ms": r.latency_ms,
                         "first": [v.code for v in r.first_attempt_violations],
                         "final": [v.code for v in r.violations],
                         "content": json.loads(r.content.model_dump_json())})
            print(user, r.model, r.attempts, r.passed, runs[-1]["first"], r.latency_ms, flush=True)
            time.sleep(2)
        res[user] = runs
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
