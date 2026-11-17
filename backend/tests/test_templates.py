from pathlib import Path

import pytest

from app.ai.guardrails import check
from app.ai.templates import LIMITATIONS, insight_for, strengths_for, summary_for, template_content
from app.config import load_thresholds
from app.schemas import FlagId
from tests.helpers import mk_flagged

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")
SYMBOLS = frozenset({"FPT", "VCB", "HPG", "VND"})

ALL_FLAGS = dict(
    activity={"avg_turnover": 1.5, "trades_per_month": 12.0},
    concentration={"hhi": 0.45, "top_symbol": "FPT", "top_symbol_weight": 0.55},
    disposition={"pgr": 0.4, "plr": 0.1, "de": 0.3, "n_sells": 30},
    chasing={"ratio": 0.5, "n_buys": 40},
    herding={"lift": 3.0, "n_sells": 30},
    performance={"excess": -0.0523, "vol_annual": 0.31},
)


def all_flags_metrics():
    return mk_flagged(**ALL_FLAGS)


def test_scenario_really_fires_every_real_flag():
    ids = {f.id for f in all_flags_metrics().flags}
    assert ids == set(FlagId) - {FlagId.insufficient_data}


def test_every_flag_template_passes_the_guardrails():
    m = all_flags_metrics()
    parsed, violations = check(template_content(m).model_dump(mode="json"), m, CFG, SYMBOLS)
    assert violations == [] and parsed is not None


def test_insufficient_data_template_passes_the_guardrails():
    m = mk_flagged(disposition={"de": 0.4, "n_sells": 6}, chasing={"ratio": 0.9, "n_buys": 4},
                   herding={"lift": 5.0, "n_sells": 6})
    assert [f.id for f in m.flags] == [FlagId.insufficient_data]
    parsed, violations = check(template_content(m).model_dump(mode="json"), m, CFG, SYMBOLS)
    assert violations == []
    text = parsed.insights[0].observation
    assert "6" in text and "4" in text


def test_quiet_investor_gets_summary_without_insights():
    m = mk_flagged()
    content = template_content(m)
    assert content.insights == []
    assert check(content.model_dump(mode="json"), m, CFG, SYMBOLS)[1] == []


def test_each_insight_uses_the_flags_evidence_keys():
    m = all_flags_metrics()
    for flag in m.flags:
        ins = insight_for(flag, m)
        assert ins.flag_id == flag.id and ins.evidence_keys == flag.evidence_keys
        assert ins.self_check_question.endswith("?")


def test_missing_holding_days_are_skipped_not_printed_as_none():
    m = mk_flagged(disposition={"de": 0.3, "n_sells": 30}, holding={"avg_days_win": None, "avg_days_loss": None})
    flag = next(f for f in m.flags if f.id == FlagId.disposition)
    assert "None" not in insight_for(flag, m).observation


def test_summary_mentions_period_and_flag_names_and_is_short():
    m = all_flags_metrics()
    s = summary_for(m)
    assert "6 tháng" in s and len(s.split()) <= 60


def test_strengths_are_factual_and_checked():
    m = mk_flagged(performance={"excess": 0.0412})
    strengths = strengths_for(m)
    assert strengths and any("4,1%" in s for s in strengths)
    assert check({"summary": "ok", "insights": [], "strengths": strengths, "limitations": LIMITATIONS}, m, CFG, SYMBOLS)[1] == []


def test_limitations_state_data_provenance_and_not_advice():
    assert "mô phỏng" in LIMITATIONS and "khuyến nghị" in LIMITATIONS


@pytest.mark.parametrize("fid", [f for f in FlagId if f != FlagId.insufficient_data])
def test_templates_never_give_advice_wording(fid):
    m = all_flags_metrics()
    flag = next(f for f in m.flags if f.id == fid)
    ins = insight_for(flag, m)
    text = " ".join([ins.title, ins.observation, ins.self_check_question]).lower()
    assert "nên " not in text and "khuyến nghị mua" not in text
