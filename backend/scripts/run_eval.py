"""Measure the system: flag detection against labeled personas, AI faithfulness, speed.

    uv run python scripts/run_eval.py --runs 3 [--skip-llm] [--save-baseline]

Runs the core and AI directly (no HTTP, no DB). Writes eval/results.json and eval/results.md; the
markdown is rendered from the JSON so the two always agree.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ai.llm import LLMClient, build_llm
from app.ai.report import build_report
from app.config import Settings, Thresholds, load_thresholds
from app.core.fees import apply_fees
from app.core.flags import annotate
from app.core.metrics import compute_metrics
from app.core.prices import INDEX_SYMBOL, PriceStore
from app.core.risk import score
from app.core.validate import validate
from app.schemas import FlagId, Metrics

FLAGS = [f.value for f in FlagId]
MANUAL_START, MANUAL_END = "<!-- manual:start -->", "<!-- manual:end -->"
MANUAL_DEFAULT = (
    "| Tiêu chí | Điểm trung bình (thang 1-5) |\n|---|---|\n| Dễ hiểu | chưa thu thập |\n"
    "| Liên quan | chưa thu thập |\n| Hữu ích | chưa thu thập |\n\n"
    "Câu hỏi mở: chưa thu thập. Mẫu 5 người chỉ mang tính tham khảo."
)


# ------------------------------------------------------------------ small statistics
def percentile(values: list[float], p: float) -> float:
    return float(np.percentile(values, p))


def precision_recall(tp: int, fp: int, fn: int) -> dict:
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


# ------------------------------------------------------------------ shared computation
def _load(personas_dir: Path, name: str):
    return (personas_dir / name).read_text(encoding="utf-8")


def compute_all(personas_dir: Path, store: PriceStore, cfg: Thresholds) -> dict[str, Metrics]:
    answers = json.loads(_load(personas_dir, "answers.json"))
    out: dict[str, Metrics] = {}
    for path in sorted(personas_dir.glob("P*_s*.csv")):
        persona = path.stem.split("_")[0]
        result = validate(path.read_bytes(), store)
        if result.errors:
            raise SystemExit(f"{path.name} has validation errors: {result.errors[:2]}")
        trades = apply_fees(result.rows, cfg)
        out[path.stem] = annotate(compute_metrics(trades, store, score(answers[persona], cfg), cfg), cfg)
    return out


# ------------------------------------------------------------------ 1. detection
DERIVED_LABELS = {"overconfidence": "overtrading AND performance.excess < 0"}


def effective_labels(declared: list[str], m: Metrics) -> list[str]:
    """Persona labels plus the derived ones. overconfidence is defined on the outcome (spec 05), which no
    persona declares, so a file is expected to show it when it is labeled overtrading and lagged the market."""
    out = list(declared)
    if "overtrading" in declared and m.metrics.performance.excess < 0:
        out.append("overconfidence")
    return out


def evaluate_detection(personas_dir: Path, store: PriceStore, cfg: Thresholds) -> dict:
    metrics = compute_all(personas_dir, store, cfg)
    declared: dict[str, list[str]] = json.loads(_load(personas_dir, "labels.json"))
    labels = {name: effective_labels(declared[name], m) for name, m in metrics.items()}
    predictions = {name: sorted({f.id.value for f in m.flags}) for name, m in metrics.items()}

    per_flag = {}
    for flag in FLAGS:
        tp = sum(flag in predictions[n] and flag in labels[n] for n in metrics)
        fp = sum(flag in predictions[n] and flag not in labels[n] for n in metrics)
        fn = sum(flag not in predictions[n] and flag in labels[n] for n in metrics)
        per_flag[flag] = precision_recall(tp, fp, fn)

    confusion: dict[str, dict[str, dict]] = {}
    for name in metrics:
        persona = name.split("_")[0]
        row = confusion.setdefault(persona, {f: {"fired": 0, "seeds": 0} for f in FLAGS})
        for f in FLAGS:
            row[f]["seeds"] += 1
            row[f]["fired"] += f in predictions[name]
    expected = {name.split("_")[0]: declared[name] for name in metrics}
    return {"n_files": len(metrics), "per_flag": per_flag, "confusion": confusion,
            "expected": expected, "predictions": predictions, "labels": labels,
            "derived_labels": DERIVED_LABELS}


# ------------------------------------------------------------------ 2. AI
MAX_VIOLATION_EXAMPLES = 40


def _is_api_error(violations) -> bool:
    return any(v.code == "llm_error" for v in violations)


def evaluate_ai(items: dict[str, Metrics], llm: LLMClient, cfg: Thresholds, symbols: frozenset[str],
                runs: int, pause: float = 0.0) -> dict:
    """Faithfulness of the AI text. API failures (quota, 503, DNS) say nothing about the model's output, so
    they are counted separately and left out of every rate's denominator."""
    results, names = [], []
    for name, m in items.items():
        for _ in range(runs):
            results.append(build_report(m, llm, cfg, symbols))
            names.append(name)
            if pause:
                time.sleep(pause)

    answered = [r for r in results if not _is_api_error(r.violations)]
    first_answered = [r for r in results if not _is_api_error(r.first_attempt_violations)]
    codes: dict[str, int] = {}
    examples: list[dict] = []  # kept so a reader can tell a fabricated number from a guardrail false alarm
    for name, r in zip(names, results, strict=True):
        for v in r.first_attempt_violations:
            if v.code != "llm_error":
                codes[v.code] = codes.get(v.code, 0) + 1
                if len(examples) < MAX_VIOLATION_EXAMPLES:
                    examples.append({"file": name, "code": v.code, "scope": v.scope, "detail": v.detail})
    latencies = [r.latency_ms for r in answered]
    return {
        "model": llm.model, "reports": len(results), "runs_per_file": runs,
        "answered": len(answered), "api_errors": len(results) - len(answered),
        "first_attempt_pass_rate": (sum(not r.first_attempt_violations for r in first_answered) / len(first_answered)
                                    if first_answered else None),
        "final_pass_rate": sum(r.passed for r in answered) / len(answered) if answered else None,
        "violations": {"number_not_found": codes.get("number_not_found", 0), "advice": codes.get("advice", 0)},
        "violation_codes": codes,
        "violation_examples": examples,
        "latency_ms": {"p50": percentile(latencies, 50), "max": max(latencies)} if latencies else
                      {"p50": None, "max": None},
    }


# ------------------------------------------------------------------ 3. speed
def synthetic_csv(store: PriceStore, n: int = 5000, seed: int = 11) -> bytes:
    """A valid n-row history over the whole price window, for timing only."""
    rng = np.random.default_rng(seed)
    symbols = sorted(store.symbols - {INDEX_SYMBOL})
    days = store.trading_days
    held = dict.fromkeys(symbols, 0)
    lines = ["trade_date,symbol,side,quantity,price,fee,tax"]
    for i in range(n):
        d = days[int(i * len(days) / n)]
        sym = str(rng.choice(symbols))
        if held[sym] == 0 or rng.random() < 0.55:
            qty, side = 100 * int(rng.integers(1, 6)), "BUY"
            held[sym] += qty
        else:
            qty, side = 100 * int(rng.integers(1, held[sym] // 100 + 1)), "SELL"
            held[sym] -= qty
        price = max(10, int(round(store.bar(sym, d).close / 10) * 10))
        lines.append(f"{d},{sym},{side},{qty},{price},,")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _pipeline_ms(data: bytes, store: PriceStore, cfg: Thresholds, answers: list[int]) -> float:
    start = time.perf_counter()
    result = validate(data, store)
    trades = apply_fees(result.rows, cfg)
    annotate(compute_metrics(trades, store, score(answers, cfg), cfg), cfg)
    return (time.perf_counter() - start) * 1000


def evaluate_speed(personas_dir: Path, store: PriceStore, cfg: Thresholds) -> dict:
    answers = json.loads(_load(personas_dir, "answers.json"))
    times = [_pipeline_ms(p.read_bytes(), store, cfg, answers[p.stem.split("_")[0]])
             for p in sorted(personas_dir.glob("P*_s*.csv"))]
    big = _pipeline_ms(synthetic_csv(store), store, cfg, [2, 2, 3, 3, 2])
    return {"files": len(times), "p50_ms": percentile(times, 50), "max_ms": max(times),
            "synthetic_5000_rows_ms": big}


# ------------------------------------------------------------------ markdown
def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.0%}"


def _detection_md(det: dict) -> list[str]:
    lines = ["| Khuynh hướng | TP | FP | FN | Precision | Recall |", "|---|---|---|---|---|---|"]
    for flag, c in det["per_flag"].items():
        lines.append(f"| {flag} | {c['tp']} | {c['fp']} | {c['fn']} | {_pct(c['precision'])} | {_pct(c['recall'])} |")
    return lines


def render_markdown(r: dict, baseline: dict | None, manual: str) -> str:
    det, ai, speed = r["detection"], r["ai"], r["speed"]
    out = [
        "# Kết quả đánh giá Investor Insight", "",
        f"- Ngày chạy: {r['run_date']} · formula_version: {r['formula_version']} · "
        f"mô hình LLM: {r['llm_model'] or 'không dùng'} · commit: {r['git_commit']} · số lần chạy mỗi hồ sơ: {r['runs']}",
        f"- Nguồn giá: {r['price_source']}",
        "- Lưu ý: dữ liệu giao dịch là mô phỏng. Việc tự cài rồi tự phát hiện chỉ chứng minh mã chạy đúng đặc tả, "
        "không chứng minh hiệu quả trên nhà đầu tư thật.", "",
        "## 1. Phát hiện khuynh hướng", "", f"Số tệp đánh giá: {det['n_files']}.", "", *_detection_md(det), "",
        *[f"Nhãn `{k}` là nhãn phái sinh, không do persona khai báo: `{v}`." for k, v in det.get("derived_labels", {}).items()],
        "",
        "### Ma trận hồ sơ × khuynh hướng", "",
        "Mỗi ô là số seed có bật cờ trên tổng số seed. Dấu ◆ đánh dấu cờ được kỳ vọng theo nhãn.", "",
        "| Hồ sơ | " + " | ".join(FLAGS) + " |", "|---|" + "---|" * len(FLAGS),
    ]
    for persona, row in det["confusion"].items():
        cells = [f"{row[f]['fired']}/{row[f]['seeds']}{' ◆' if f in det['expected'][persona] else ''}" for f in FLAGS]
        out.append(f"| {persona} | " + " | ".join(cells) + " |")
    out += ["", "## 2. AI bám số liệu", ""]
    if ai is None:
        out.append("Bỏ qua (chạy với --skip-llm), chưa có số đo.")
    else:
        v = ai["violations"]
        lat = ai["latency_ms"]
        latency = "—" if lat["p50"] is None else f"{lat['p50'] / 1000:.1f} s / {lat['max'] / 1000:.1f} s"
        others = {k: n for k, n in ai["violation_codes"].items() if k not in v}
        out += [
            "| Chỉ số | Giá trị |", "|---|---|",
            f"| Phạm vi | {ai['scope']} |",
            f"| Số báo cáo | {ai['reports']} |",
            f"| Mô hình trả lời được (không tính lỗi API) | {ai['answered']} |",
            f"| Không đánh giá được do lỗi API (hết hạn mức, 503, mạng) | {ai['api_errors']} |",
            f"| Qua guardrail ở lần sinh đầu tiên | {_pct(ai['first_attempt_pass_rate'])} |",
            f"| Qua guardrail cuối cùng (không dùng mẫu thay thế) | {_pct(ai['final_pass_rate'])} |",
            f"| Số vi phạm number_not_found (lần đầu) | {v['number_not_found']} |",
            f"| Số vi phạm advice (lần đầu) | {v['advice']} |",
            f"| Vi phạm khác ở lần đầu (schema, coverage, evidence_key) | {', '.join(f'{k}: {n}' for k, n in others.items()) or 'không'} |",
            f"| Thời gian sinh báo cáo p50 / lớn nhất | {latency} |",
        ]
        if ai["api_errors"]:
            out += ["", f"> {ai['api_errors']}/{ai['reports']} báo cáo gặp lỗi API nên không được đưa vào các tỷ lệ trên; "
                    "đây là số đo chưa đầy đủ, cần chạy lại khi API ổn định."]
    out += ["", "## 3. Hiệu năng", "", "| Phép đo | Giá trị |", "|---|---|",
            f"| Kiểm tra CSV + tính chỉ số, p50 ({speed['files']} tệp) | {speed['p50_ms']:.0f} ms |",
            f"| Kiểm tra CSV + tính chỉ số, lớn nhất | {speed['max_ms']:.0f} ms |",
            f"| Tệp tổng hợp 5.000 dòng | {speed['synthetic_5000_rows_ms']:.0f} ms |", "",
            "## 4. Khảo sát người dùng (nhập tay)", "", MANUAL_START, manual, MANUAL_END]
    if baseline is not None:
        out += ["", "## Trước hiệu chỉnh", "",
                f"Lần chạy lưu ngày {baseline['run_date']} (formula_version {baseline['formula_version']}).", "",
                *_detection_md(baseline["detection"])]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ orchestration
def _git_commit() -> str:
    try:
        res = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, check=False,
                             text=True, timeout=5)
        return res.stdout.strip() or "n/a" if res.returncode == 0 else "n/a"
    except (OSError, subprocess.SubprocessError):
        return "n/a"


def _price_source(prices_dir: Path) -> str:
    path = Path(prices_dir).parent / "SOURCE.json"
    if not path.exists():
        return "không rõ"
    meta = json.loads(path.read_text(encoding="utf-8"))
    tag = "MÔ PHỎNG (không phải giá thị trường thật)" if meta.get("simulated") else meta.get("source", "?")
    return f"{tag}, {meta.get('start')} đến {meta.get('end')}"


def _ai_section(personas_dir: Path, store: PriceStore, cfg: Thresholds, llm: LLMClient | None, runs: int,
                pause: float, ai_seed: int | None) -> dict | None:
    if llm is None:
        return None
    items = compute_all(personas_dir, store, cfg)
    scope = f"toàn bộ {len(items)} tệp"
    if ai_seed is not None:
        items = {n: m for n, m in items.items() if n.endswith(f"_s{ai_seed}")}
        scope = f"seed {ai_seed} ({len(items)}/{len(compute_all(personas_dir, store, cfg))} tệp)"
    res = evaluate_ai(items, llm, cfg, frozenset(store.symbols), runs, pause)
    return {**res, "scope": scope}


def run_eval(personas_dir: Path, prices_dir: Path, out_dir: Path, thresholds_path: Path,
             llm: LLMClient | None, runs: int, save_baseline: bool = False, pause: float = 0.0,
             ai_seed: int | None = None) -> dict:
    cfg, store = load_thresholds(thresholds_path), PriceStore(prices_dir)
    personas_dir, out_dir = Path(personas_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "formula_version": cfg.formula_version,
        "llm_model": llm.model if llm else None,
        "run_date": date.today().isoformat(),
        "git_commit": _git_commit(),
        "price_source": _price_source(prices_dir),
        "runs": runs,
        "detection": evaluate_detection(personas_dir, store, cfg),
        "ai": _ai_section(personas_dir, store, cfg, llm, runs, pause, ai_seed),
        "speed": evaluate_speed(personas_dir, store, cfg),
        "thresholds": cfg.model_dump(mode="json"),
    }
    results = json.loads(json.dumps(results, default=str))  # JSON-native, so md and json cannot disagree

    baseline_path, md_path = out_dir / "baseline.json", out_dir / "results.md"
    baseline = None if save_baseline or not baseline_path.exists() else json.loads(
        baseline_path.read_text(encoding="utf-8"))
    manual = MANUAL_DEFAULT
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        if MANUAL_START in text and MANUAL_END in text:
            manual = text.split(MANUAL_START, 1)[1].split(MANUAL_END, 1)[0].strip("\n")

    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if save_baseline:
        baseline_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(results, baseline, manual), encoding="utf-8")
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--pause", type=float, default=0.0, help="seconds to wait between reports (API rate limits)")
    ap.add_argument("--ai-seed", type=int, default=None, help="evaluate the AI on files of this seed only (saves API quota)")
    ap.add_argument("--save-baseline", action="store_true", help="also store this run as 'Trước hiệu chỉnh'")
    ap.add_argument("--personas", default=str(ROOT / "data" / "personas"))
    ap.add_argument("--prices", default=str(ROOT / "data" / "prices"))
    ap.add_argument("--out", default=str(ROOT.parent / "eval"))
    args = ap.parse_args()

    llm = None
    if not args.skip_llm:
        llm = build_llm(Settings())
        if llm is None:
            raise SystemExit("No LLM key set (GEMINI_API_KEY or LLM_API_KEY). Set one, or run with --skip-llm.")

    started = time.perf_counter()
    run_eval(Path(args.personas), Path(args.prices), Path(args.out), ROOT / "config" / "thresholds.yaml", llm,
             args.runs, args.save_baseline, args.pause, args.ai_seed)
    print(f"wrote {args.out}/results.json and results.md in {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
