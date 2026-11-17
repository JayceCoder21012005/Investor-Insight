import json
from pathlib import Path

import pytest

from app.ai.llm import FakeLLM
from app.ai.templates import template_content
from app.config import load_thresholds
from app.schemas import FlagId, Metrics
from scripts.generate_personas import generate_all, load_specs
from scripts.run_eval import (
    evaluate_ai,
    evaluate_detection,
    evaluate_speed,
    percentile,
    precision_recall,
    run_eval,
    synthetic_csv,
)

ROOT = Path(__file__).resolve().parent.parent
CFG = load_thresholds(ROOT / "config" / "thresholds.yaml")
FLAGS = [f.value for f in FlagId]


@pytest.fixture(scope="module")
def personas_dir(tmp_path_factory, synthetic_store):
    d = tmp_path_factory.mktemp("eval_personas")
    generate_all(synthetic_store, load_specs(ROOT / "scripts" / "persona_specs.yaml"), seeds=2, out_dir=d)
    return d


# ---------------------------------------------------------------- statistics
def test_precision_recall_from_counts():
    pr = precision_recall(tp=3, fp=1, fn=2)
    assert pr == {"tp": 3, "fp": 1, "fn": 2, "precision": 0.75, "recall": 0.6}


def test_precision_or_recall_is_none_when_undefined():
    assert precision_recall(0, 0, 0)["precision"] is None and precision_recall(0, 0, 0)["recall"] is None
    assert precision_recall(0, 2, 0)["recall"] is None and precision_recall(0, 2, 0)["precision"] == 0.0


def test_percentile_median_and_max():
    assert percentile([5, 1, 3], 50) == 3 and percentile([5, 1, 3], 100) == 5
    assert percentile([1, 2, 3, 4], 50) == 2.5


# ---------------------------------------------------------------- detection
def test_detection_counts_against_known_labels(personas_dir, synthetic_store):
    res = evaluate_detection(personas_dir, synthetic_store, CFG)
    assert set(res["per_flag"]) == set(FLAGS) and res["n_files"] == 22
    assert set(res["confusion"]) == {f"P{i:02d}" for i in range(1, 12)}
    for flag, c in res["per_flag"].items():
        assert c["tp"] + c["fn"] == sum(flag in v for v in res["labels"].values()), flag


def test_overconfidence_label_is_derived_from_the_overtrading_label_and_the_outcome(personas_dir, synthetic_store):
    """overconfidence = overtrading AND excess < 0 (spec 05), so its label is the overtrading label on files
    that ended below the market; the persona files themselves never declare it."""
    from scripts.run_eval import compute_all

    res = evaluate_detection(personas_dir, synthetic_store, CFG)
    declared = json.loads((personas_dir / "labels.json").read_text(encoding="utf-8"))
    metrics = compute_all(personas_dir, synthetic_store, CFG)
    for name, m in metrics.items():
        expected = "overtrading" in declared[name] and m.metrics.performance.excess < 0
        assert ("overconfidence" in res["labels"][name]) == expected, name
        assert set(declared[name]) <= set(res["labels"][name])
    assert res["derived_labels"] == {"overconfidence": "overtrading AND performance.excess < 0"}


def test_detection_confusion_is_fired_over_seeds(personas_dir, synthetic_store):
    res = evaluate_detection(personas_dir, synthetic_store, CFG)
    cell = res["confusion"]["P10"]["insufficient_data"]
    assert cell == {"fired": 2, "seeds": 2}


def test_predictions_are_listed_per_file(personas_dir, synthetic_store):
    res = evaluate_detection(personas_dir, synthetic_store, CFG)
    assert "P03_s1" in res["predictions"] and isinstance(res["predictions"]["P03_s1"], list)


# ---------------------------------------------------------------- AI
def echo(m: Metrics):
    return template_content(m).model_dump(mode="json")


def metric_items(personas_dir, synthetic_store):
    from scripts.run_eval import compute_all

    return compute_all(personas_dir, synthetic_store, CFG)


def test_ai_all_good_has_full_pass_rates(personas_dir, synthetic_store):
    items = metric_items(personas_dir, synthetic_store)
    sample = dict(list(items.items())[:3])

    class GoodLLM(FakeLLM):
        def generate_json(self, system, user, schema):
            payload = json.loads(user[user.index("{"):])
            payload["formula_version"] = "x"
            return echo(Metrics.model_validate(payload))

    res = evaluate_ai(sample, GoodLLM([{}]), CFG, frozenset(synthetic_store.symbols), runs=2)
    assert res["reports"] == 6 and res["first_attempt_pass_rate"] == 1.0 and res["final_pass_rate"] == 1.0
    assert res["violations"] == {"number_not_found": 0, "advice": 0}


def test_ai_counts_first_attempt_violations_even_when_retry_recovers(personas_dir, synthetic_store):
    items = metric_items(personas_dir, synthetic_store)
    name, m = next((n, x) for n, x in items.items() if x.flags and x.flags[0].id != FlagId.insufficient_data)
    bad = echo(m)
    bad["insights"][0]["observation"] = "Bạn nên bán FPT ngay."
    llm = FakeLLM([bad, echo(m)])
    res = evaluate_ai({name: m}, llm, CFG, frozenset(synthetic_store.symbols), runs=1)
    assert res["first_attempt_pass_rate"] == 0.0 and res["final_pass_rate"] == 1.0
    assert res["violations"]["advice"] >= 1


def test_api_errors_are_not_counted_as_ai_unfaithfulness(personas_dir, synthetic_store):
    from app.ai.llm import LLMError

    items = dict(list(metric_items(personas_dir, synthetic_store).items())[:3])
    res = evaluate_ai(items, FakeLLM([LLMError("429 quota")]), CFG, frozenset(), runs=1)
    assert res["reports"] == 3 and res["api_errors"] == 3 and res["answered"] == 0
    assert res["first_attempt_pass_rate"] is None and res["final_pass_rate"] is None


def test_rates_are_computed_only_over_reports_the_model_actually_answered(personas_dir, synthetic_store):
    from app.ai.llm import LLMError

    items = metric_items(personas_dir, synthetic_store)
    names = [n for n, m in items.items() if m.flags and m.flags[0].id != FlagId.insufficient_data][:2]
    good_item = {names[0]: items[names[0]]}
    good = echo(items[names[0]])

    class Scripted(FakeLLM):
        def __init__(self):
            super().__init__([{}])
            self.n = 0

        def generate_json(self, system, user, schema):
            self.n += 1
            if self.n <= 2:  # the first report: both attempts hit the API error
                raise LLMError("503")
            return good

    both = {names[1]: items[names[1]], names[0]: items[names[0]]}
    llm = Scripted()
    res = evaluate_ai(both, llm, CFG, frozenset(), runs=1)
    assert res["reports"] == 2 and res["api_errors"] == 1 and res["answered"] == 1
    # the second report answered correctly only if its metrics match `good`; otherwise it fails a guardrail,
    # either way the failed API report is excluded from the denominator
    assert res["final_pass_rate"] in (0.0, 1.0)
    assert good_item


def test_a_transient_error_on_the_first_attempt_is_not_a_first_attempt_failure(personas_dir, synthetic_store):
    from app.ai.llm import LLMError

    items = metric_items(personas_dir, synthetic_store)
    name, m = next(iter(items.items()))
    res = evaluate_ai({name: m}, FakeLLM([LLMError("503"), echo(m)]), CFG, frozenset(), runs=1)
    assert res["api_errors"] == 0 and res["final_pass_rate"] == 1.0
    assert res["first_attempt_pass_rate"] is None  # no first attempt that the model answered


def test_violation_codes_are_counted_so_failures_can_be_explained(personas_dir, synthetic_store):
    items = metric_items(personas_dir, synthetic_store)
    name, m = next((n, x) for n, x in items.items() if x.flags and x.flags[0].id != FlagId.insufficient_data)
    res = evaluate_ai({name: m}, FakeLLM([{"garbage": 1}, echo(m)]), CFG, frozenset(), runs=1)
    assert res["violation_codes"] == {"schema": 1}
    ex = res["violation_examples"]
    assert len(ex) == 1 and ex[0]["file"] == name and ex[0]["code"] == "schema" and ex[0]["detail"]


def test_ai_latency_summary_present(personas_dir, synthetic_store):
    items = dict(list(metric_items(personas_dir, synthetic_store).items())[:2])
    m = next(iter(items.values()))
    res = evaluate_ai(items, FakeLLM([echo(m)]), CFG, frozenset(), runs=1)
    assert set(res["latency_ms"]) == {"p50", "max"}


# ---------------------------------------------------------------- speed
def test_synthetic_file_has_5000_valid_rows(synthetic_store):
    from app.core.validate import validate

    r = validate(synthetic_csv(synthetic_store, 5000), synthetic_store)
    assert r.errors == [] and len(r.rows) == 5000


def test_speed_reports_median_and_max(personas_dir, synthetic_store):
    res = evaluate_speed(personas_dir, synthetic_store, CFG)
    assert res["files"] == 22 and res["p50_ms"] <= res["max_ms"]
    assert res["synthetic_5000_rows_ms"] > 0


# ---------------------------------------------------------------- end to end
def test_run_eval_skip_llm_writes_consistent_json_and_markdown(personas_dir, synthetic_dir, tmp_path):
    out = tmp_path / "eval"
    res = run_eval(personas_dir=personas_dir, prices_dir=synthetic_dir, out_dir=out, thresholds_path=ROOT / "config" / "thresholds.yaml",
                   llm=None, runs=1)
    data = json.loads((out / "results.json").read_text(encoding="utf-8"))
    md = (out / "results.md").read_text(encoding="utf-8")
    assert data["formula_version"] == "0.3" and data["ai"] is None and "run_date" in data and "git_commit" in data
    assert res == data
    for c in data["detection"]["per_flag"].values():
        if c["precision"] is not None:
            assert f"{c['precision']:.0%}" in md
    assert "bỏ qua" in md.lower() and "Hiệu năng" in md


def test_ai_can_be_evaluated_on_one_seed_only(personas_dir, synthetic_dir, tmp_path):
    seen = []

    class Counting(FakeLLM):
        def generate_json(self, system, user, schema):
            seen.append(1)
            payload = json.loads(user[user.index("{"):])
            payload["formula_version"] = "x"
            return echo(Metrics.model_validate(payload))

    res = run_eval(personas_dir=personas_dir, prices_dir=synthetic_dir, out_dir=tmp_path / "e",
                   thresholds_path=ROOT / "config" / "thresholds.yaml", llm=Counting([{}]), runs=1, ai_seed=1)
    assert res["ai"]["reports"] == 11 and len(seen) == 11
    assert res["ai"]["scope"] == "seed 1 (11/22 tệp)"
    assert res["detection"]["n_files"] == 22  # detection and speed still cover every file


def test_baseline_is_kept_under_truoc_hieu_chinh(personas_dir, synthetic_dir, tmp_path):
    out = tmp_path / "eval"
    kwargs = dict(personas_dir=personas_dir, prices_dir=synthetic_dir, out_dir=out,
                  thresholds_path=ROOT / "config" / "thresholds.yaml", llm=None, runs=1)
    run_eval(**kwargs, save_baseline=True)
    assert (out / "baseline.json").exists()
    run_eval(**kwargs)
    assert "Trước hiệu chỉnh" in (out / "results.md").read_text(encoding="utf-8")
