import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import load_thresholds
from app.core.risk import score
from app.core.validate import validate
from scripts.generate_personas import PersonaSpec, generate_all, load_specs

ROOT = Path(__file__).resolve().parent.parent
CFG = load_thresholds(ROOT / "config" / "thresholds.yaml")
SPECS = load_specs(ROOT / "scripts" / "persona_specs.yaml")


@pytest.fixture(scope="module")
def out(tmp_path_factory, synthetic_store):
    d = tmp_path_factory.mktemp("personas")
    generate_all(synthetic_store, SPECS, seeds=2, out_dir=d)
    return d


def test_eleven_personas_defined():
    assert [s.id for s in SPECS.personas] == [f"P{i:02d}" for i in range(1, 12)]


def test_range_with_lo_above_hi_is_rejected():
    with pytest.raises(ValidationError):
        PersonaSpec(id="PX", title="t", description="d", tier="balanced", answers=[2, 2, 2, 2, 2],
                    labels=[], behaviors=["dca"], params={"x": (5.0, 1.0)})


def test_generator_never_reads_thresholds_or_flags():
    src = (ROOT / "scripts" / "generate_personas.py").read_text(encoding="utf-8")
    assert "thresholds" not in src and "core.flags" not in src and "core.risk" not in src


def test_files_written_for_every_persona_and_seed(out):
    for s in SPECS.personas:
        for seed in (1, 2):
            assert (out / f"{s.id}_s{seed}.csv").exists()
    labels = json.loads((out / "labels.json").read_text(encoding="utf-8"))
    assert len(labels) == 22 and labels["P03_s1"] == ["disposition"] and labels["P06_s2"] == ["overtrading", "disposition"]


def test_every_csv_passes_validation_with_zero_errors(out, synthetic_store):
    for f in sorted(out.glob("P*_s*.csv")):
        r = validate(f.read_bytes(), synthetic_store)
        assert r.errors == [], f"{f.name}: {r.errors[:3]}"
        assert len(r.rows) > 0


def test_same_seed_gives_identical_output(synthetic_store, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate_all(synthetic_store, SPECS, seeds=1, out_dir=a)
    generate_all(synthetic_store, SPECS, seeds=1, out_dir=b)
    for f in a.glob("P*.csv"):
        assert f.read_bytes() == (b / f.name).read_bytes()


def test_different_seeds_differ(out):
    assert (out / "P01_s1.csv").read_bytes() != (out / "P01_s2.csv").read_bytes()


def test_fee_and_tax_columns_are_blank(out):
    lines = (out / "P01_s1.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "trade_date,symbol,side,quantity,price,fee,tax"
    assert all(line.endswith(",,") for line in lines[1:])


def test_quantities_are_round_lots(out):
    for f in out.glob("P*_s1.csv"):
        for line in f.read_text(encoding="utf-8").splitlines()[1:]:
            assert int(line.split(",")[3]) % 100 == 0


def test_p10_has_exactly_six_buys_and_p08_never_sells(out):
    p10 = (out / "P10_s1.csv").read_text(encoding="utf-8")
    assert len(p10.splitlines()) - 1 == 6 and ",SELL," not in p10
    assert ",SELL," not in (out / "P08_s1.csv").read_text(encoding="utf-8")


def _rows(path: Path) -> list[list[str]]:
    return [line.split(",") for line in path.read_text(encoding="utf-8").splitlines()[1:]]


def _final_weights(path: Path, store) -> dict[str, float]:
    qty: dict[str, int] = {}
    for _, sym, side, q, _price, *_ in _rows(path):
        qty[sym] = qty.get(sym, 0) + (int(q) if side == "BUY" else -int(q))
    last = store.trading_days[-1]
    value = {s: q * store.bar(s, last).close for s, q in qty.items() if q > 0}
    total = sum(value.values())
    return {s: v / total for s, v in value.items()}


@pytest.mark.parametrize("seed", [1, 2])
def test_p08_spends_about_the_same_money_on_each_of_its_five_stocks(out, seed):
    """Monthly equal buys: a stock whose lot costs more than one month's slice must still be bought."""
    spent: dict[str, float] = {}
    for _, sym, side, q, price, *_ in _rows(out / f"P08_s{seed}.csv"):
        spent[sym] = spent.get(sym, 0.0) + int(q) * int(price)
    total = sum(spent.values())
    assert sorted(spent) == ["ACB", "FPT", "PNJ", "VCB", "VNM"]
    assert all(0.15 <= v / total <= 0.25 for v in spent.values()), {s: round(v / total, 2) for s, v in spent.items()}


@pytest.mark.parametrize("seed", [1, 2])
def test_p07_main_stock_stays_the_largest_holding_near_half(out, synthetic_store, seed):
    w = _final_weights(out / f"P07_s{seed}.csv", synthetic_store)
    assert max(w.values()) >= 0.40, {s: round(x, 2) for s, x in w.items()}


def test_answers_score_into_declared_tier_and_level(out):
    answers = json.loads((out / "answers.json").read_text(encoding="utf-8"))
    for s in SPECS.personas:
        p = score(answers[s.id], CFG)
        assert p.tier.value == s.tier, f"{s.id}: {p.tier} != {s.tier}"
