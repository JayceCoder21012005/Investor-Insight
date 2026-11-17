from pathlib import Path

import pytest

from app.config import load_thresholds
from app.core.flags import evaluate
from app.schemas import Metrics
from tests.helpers import mk

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")


def ids(m: Metrics) -> list[str]:
    return [f.id.value for f in evaluate(m, CFG)[0]]


def test_quiet_investor_has_no_flags_and_is_balanced():
    flags, kind = evaluate(mk(), CFG)
    assert flags == [] and kind == "Cân bằng"


# ---- overtrading
def test_overtrading_by_average_turnover_above_one():
    assert "overtrading" in ids(mk(activity={"avg_turnover": 1.01}))
    assert "overtrading" not in ids(mk(activity={"avg_turnover": 1.0}))  # strictly greater


def test_overtrading_by_spike_against_previous_three_month_mean():
    # previous 3 months mean 0.5 -> 2x = 1.0 ; 1.1 spikes
    assert "overtrading" in ids(mk(monthly=[0.5, 0.5, 0.5, 1.1]))
    assert "overtrading" not in ids(mk(monthly=[0.5, 0.5, 0.5, 1.0]))


def test_spike_month_must_itself_reach_the_monthly_warning_level():
    # 30x the baseline, but a 30% turnover month is not "trading too much": noise on a tiny base
    assert "overtrading" not in ids(mk(monthly=[0.01, 0.01, 0.01, 0.3]))
    # 0.1 -> 0.65 is 6x, yet still below one turnover a month: an active month, not overtrading (formula 0.3)
    assert "overtrading" not in ids(mk(monthly=[0.1, 0.1, 0.1, 0.65]))
    assert "overtrading" in ids(mk(monthly=[0.2, 0.2, 0.2, 1.0]))  # exactly at the floor counts


def test_spike_needs_three_previous_months_and_nonzero_baseline():
    assert "overtrading" not in ids(mk(monthly=[0.2, 0.2, 0.9]))
    assert "overtrading" not in ids(mk(monthly=[0.0, 0.0, 0.0, 0.9]))


def test_overtrading_evidence_keys():
    f = evaluate(mk(activity={"avg_turnover": 1.5}), CFG)[0][0]
    assert f.evidence_keys == ["activity.avg_turnover", "activity.trades_per_month"] and f.severity == "warn"


# ---- concentration
def test_concentration_by_hhi_or_top_symbol():
    assert "concentration" in ids(mk(concentration={"hhi": 0.26}))
    assert "concentration" in ids(mk(concentration={"top_symbol_weight": 0.41}))
    assert "concentration" not in ids(mk(concentration={"hhi": 0.25, "top_symbol_weight": 0.40}))


# ---- disposition (sample gate)
def test_disposition_fires_with_enough_sells():
    flags = evaluate(mk(disposition={"de": 0.06, "n_sells": 10}), CFG)[0]
    f = next(x for x in flags if x.id.value == "disposition")
    assert f.evidence_keys == ["disposition.pgr", "disposition.plr", "holding.avg_days_win",
                               "holding.avg_days_loss"]


def test_disposition_threshold_is_strict():
    assert "disposition" not in ids(mk(disposition={"de": 0.05}))


def test_disposition_below_sample_gives_single_insufficient_data_instead():
    flags, _ = evaluate(mk(disposition={"de": 0.4, "n_sells": 6}, herding={"n_sells": 6}), CFG)
    assert [f.id.value for f in flags] == ["insufficient_data"]  # one entry covering both tendencies
    assert flags[0].evidence_keys == ["disposition.n_sells", "herding.n_sells"]


# ---- chasing
def test_chasing_threshold_and_gate():
    assert "chasing" in ids(mk(chasing={"ratio": 0.31}))
    assert "chasing" not in ids(mk(chasing={"ratio": 0.30}))
    flags = evaluate(mk(chasing={"ratio": 0.9, "n_buys": 9}), CFG)[0]
    assert [f.id.value for f in flags] == ["insufficient_data"]
    assert flags[0].evidence_keys == ["chasing.n_buys"]


# ---- herding
def test_herding_is_inclusive_at_threshold_and_gated():
    assert "herding" in ids(mk(herding={"lift": 2.0}))
    assert "herding" not in ids(mk(herding={"lift": 1.99}))
    assert "herding" not in ids(mk(herding={"lift": 5.0, "n_sells": 9}))


# ---- risk mismatch
def test_risk_mismatch_uses_declared_tier_limits():
    assert "risk_mismatch" in ids(mk(concentration={"hhi": 0.31}))              # balanced max 0.30
    assert "risk_mismatch" not in ids(mk(tier="growth", concentration={"hhi": 0.31}))
    # conservative max 0.25: five equal stocks (0.20) plus some price drift is not a mismatch
    assert "risk_mismatch" not in ids(mk(tier="conservative", concentration={"hhi": 0.22}))
    assert "risk_mismatch" in ids(mk(tier="conservative", concentration={"hhi": 0.26}))


def test_risk_mismatch_volatility_is_relative_to_the_market_over_the_same_period():
    # balanced: up to 1.6 x the VN-Index volatility. Index 0.20 -> limit 0.32
    assert "risk_mismatch" not in ids(mk(performance={"vol_annual": 0.31, "benchmark_vol": 0.20}))
    assert "risk_mismatch" in ids(mk(performance={"vol_annual": 0.33, "benchmark_vol": 0.20}))
    # the same 0.33 in a calmer market (index 0.15 -> limit 0.24) and for a conservative investor (1.3 x)
    assert "risk_mismatch" in ids(mk(performance={"vol_annual": 0.25, "benchmark_vol": 0.15}))
    assert "risk_mismatch" in ids(mk(tier="conservative", performance={"vol_annual": 0.27, "benchmark_vol": 0.20}))
    assert "risk_mismatch" not in ids(mk(tier="conservative", performance={"vol_annual": 0.25, "benchmark_vol": 0.20}))


def test_risk_mismatch_cites_the_benchmark_volatility():
    flag = next(f for f in evaluate(mk(performance={"vol_annual": 0.5}), CFG)[0] if f.id.value == "risk_mismatch")
    assert flag.evidence_keys == ["concentration.hhi", "performance.vol_annual", "performance.benchmark_vol"]


# ---- overconfidence
def test_overconfidence_needs_overtrading_and_negative_excess():
    both = ids(mk(activity={"avg_turnover": 1.5}, performance={"excess": -0.02}))
    assert "overconfidence" in both
    assert "overconfidence" not in ids(mk(activity={"avg_turnover": 1.5}, performance={"excess": 0.02}))
    assert "overconfidence" not in ids(mk(performance={"excess": -0.2}))  # never without overtrading


# ---- investor type
def test_investor_type_first_match_wins():
    _, k = evaluate(mk(activity={"avg_turnover": 1.5}, concentration={"hhi": 0.5}), CFG)
    assert k == "Giao dịch ngắn hạn"
    assert evaluate(mk(concentration={"hhi": 0.5}), CFG)[1] == "Tập trung"


def test_long_term_holder_needs_few_trades_and_long_holding():
    assert evaluate(mk(activity={"trades_per_month": 1.5}, holding={"avg_days": 120.0}), CFG)[1] == "Nắm giữ dài hạn"
    assert evaluate(mk(activity={"trades_per_month": 1.5}, holding={"avg_days": 60.0}), CFG)[1] == "Cân bằng"
    assert evaluate(mk(activity={"trades_per_month": 1.5}, holding={"avg_days": None}), CFG)[1] == "Cân bằng"
    assert evaluate(mk(activity={"trades_per_month": 2.0}, holding={"avg_days": 120.0}), CFG)[1] == "Cân bằng"


def test_flag_order_follows_spec_table():
    m = mk(activity={"avg_turnover": 1.5}, concentration={"hhi": 0.5},
           disposition={"de": 0.2}, chasing={"ratio": 0.5}, herding={"lift": 3.0},
           performance={"excess": -0.1})
    assert ids(m) == ["overtrading", "concentration", "disposition", "chasing", "herding",
                      "risk_mismatch", "overconfidence"]


@pytest.mark.parametrize("tier", ["conservative", "balanced", "growth"])
def test_evaluate_accepts_every_tier(tier):
    evaluate(mk(tier=tier), CFG)
