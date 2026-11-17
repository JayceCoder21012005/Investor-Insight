from pathlib import Path

import pytest

from app.config import load_thresholds
from app.core.metrics import compute_metrics
from app.schemas import Level, PricedTrade, RiskProfile, Side, Tier
from tests.conftest import SESSIONS, build_store

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")
PROFILE = RiskProfile(score=12, tier=Tier.balanced, level=Level.intermediate)
FLAT = [100] * 9


def t(n, idx, side, qty, price, symbol="AAA", fee=0, tax=0):
    return PricedTrade(row_no=n, trade_date=SESSIONS[idx], symbol=symbol, side=side, quantity=qty,
                       price=price, fee=fee, tax=tax)


def metrics(tmp_path, closes, trades, index=None, sectors=None, spread=0.0):
    store = build_store(tmp_path, {"VNINDEX": index or [1000] * 9, **closes}, sectors=sectors, spread=spread)
    return compute_metrics(trades, store, PROFILE, CFG)


def test_hhi_of_weights_half_third_fifth_is_038(tmp_path):
    closes = {"AAA": FLAT, "BBB": FLAT, "CCC": FLAT}
    trades = [t(1, 0, Side.BUY, 50, 100, "AAA"), t(2, 0, Side.BUY, 30, 100, "BBB"),
              t(3, 0, Side.BUY, 20, 100, "CCC")]
    m = metrics(tmp_path, closes, trades, sectors={"AAA": "X", "BBB": "X", "CCC": "Y"}).metrics.concentration
    assert m.hhi == pytest.approx(0.38)
    assert (m.top_symbol, m.top_symbol_weight) == ("AAA", pytest.approx(0.5))
    assert (m.top_sector, m.top_sector_weight) == ("X", pytest.approx(0.8))


def test_period_start_end_and_calendar_months(tmp_path):
    m = metrics(tmp_path, {"AAA": FLAT}, [t(1, 2, Side.BUY, 100, 100)])
    assert m.period.start == SESSIONS[2] and m.period.end == SESSIONS[-1] and m.period.months == 1
    assert m.formula_version == CFG.formula_version
    assert (m.profile.tier, m.profile.level) == (Tier.balanced, Level.intermediate)


def test_monthly_turnover_is_sell_value_over_mean_portfolio_value(tmp_path):
    trades = [t(1, 0, Side.BUY, 100, 100), t(2, 4, Side.SELL, 50, 100)]
    a = metrics(tmp_path, {"AAA": FLAT}, trades).metrics.activity
    # V = 10000 for idx0..3, 5000 for idx4..8 -> mean 65000/9 ; sells 5000
    assert a.monthly_turnover[0].month == "2026-01"
    assert a.monthly_turnover[0].value == pytest.approx(5000 / (65000 / 9))
    assert a.avg_turnover == pytest.approx(5000 / (65000 / 9))
    assert a.trades_per_month == pytest.approx(2.0)


def test_holding_days_split_by_win_and_loss(tmp_path):
    closes = {"AAA": FLAT, "BBB": FLAT}
    trades = [t(1, 0, Side.BUY, 100, 100, "AAA"), t(2, 0, Side.BUY, 100, 100, "BBB"),
              t(3, 3, Side.SELL, 100, 120, "AAA"),   # win, held 3 calendar days (Jan 5 -> 8)
              t(4, 8, Side.SELL, 100, 80, "BBB")]    # loss, held 11 days (Jan 5 -> 16)
    h = metrics(tmp_path, closes, trades).metrics.holding
    assert h.avg_days_win == pytest.approx(3) and h.avg_days_loss == pytest.approx(11)
    assert h.avg_days == pytest.approx(7)


def test_holding_is_none_without_sells(tmp_path):
    h = metrics(tmp_path, {"AAA": FLAT}, [t(1, 0, Side.BUY, 100, 100)]).metrics.holding
    assert (h.avg_days_win, h.avg_days_loss, h.avg_days) == (None, None, None)


def test_disposition_acceptance_example(tmp_path):
    # Day 1 buy A, B, C at 100. Day 2: A sold at gain, B closes 110 (paper gain), C closes 90 (paper loss).
    closes = {"AAA": [100, 120] + [120] * 7, "BBB": [100, 110] + [110] * 7, "CCC": [100, 90] + [90] * 7}
    trades = [t(1, 0, Side.BUY, 100, 100, "AAA"), t(2, 0, Side.BUY, 100, 100, "BBB"),
              t(3, 0, Side.BUY, 100, 100, "CCC"), t(4, 1, Side.SELL, 100, 120, "AAA")]
    d = metrics(tmp_path, closes, trades).metrics.disposition
    assert (d.pgr, d.plr, d.de) == (pytest.approx(0.5), pytest.approx(0.0), pytest.approx(0.5))
    assert (d.n_sell_days, d.n_sells) == (1, 1)


def test_disposition_skips_position_whose_cost_is_inside_day_range(tmp_path):
    closes = {"AAA": [100, 120] + [120] * 7, "BBB": FLAT}
    trades = [t(1, 0, Side.BUY, 100, 100, "AAA"), t(2, 0, Side.BUY, 100, 100, "BBB"),
              t(3, 1, Side.SELL, 100, 120, "AAA")]
    # spread 5 gives BBB low 95 <= 100 <= high 105 on day 2 -> skipped, so PG = 0
    d = metrics(tmp_path, closes, trades, spread=5).metrics.disposition
    assert d.pgr == pytest.approx(1.0) and d.plr == 0.0 and d.de == pytest.approx(1.0)


def test_disposition_realized_loss_counts_toward_plr(tmp_path):
    closes = {"AAA": [100, 80] + [80] * 7, "BBB": [100, 110] + [110] * 7}
    trades = [t(1, 0, Side.BUY, 100, 100, "AAA"), t(2, 0, Side.BUY, 100, 100, "BBB"),
              t(3, 1, Side.SELL, 100, 80, "AAA")]
    d = metrics(tmp_path, closes, trades).metrics.disposition
    assert d.plr == pytest.approx(1.0) and d.pgr == pytest.approx(0.0)  # RL=1, PL=0 ; RG=0, PG=1
    assert d.de == pytest.approx(-1.0)


def test_disposition_zero_denominators_give_zero(tmp_path):
    d = metrics(tmp_path, {"AAA": FLAT}, [t(1, 0, Side.BUY, 100, 100)]).metrics.disposition
    assert (d.pgr, d.plr, d.de, d.n_sell_days, d.n_sells) == (0.0, 0.0, 0.0, 0, 0)


def test_chasing_ratio_three_of_ten_after_ten_percent_rise(tmp_path):
    closes = {"AAA": [100, 100, 100, 100, 100, 110, 110, 110, 110], "BBB": FLAT}
    trades = [t(1, 6, Side.BUY, 100, 110, "AAA"), t(2, 7, Side.BUY, 100, 110, "AAA"),
              t(3, 8, Side.BUY, 100, 110, "AAA")]
    trades += [t(4 + i, 6 + i % 3, Side.BUY, 100, 100, "BBB") for i in range(7)]
    c = metrics(tmp_path, closes, trades).metrics.chasing
    assert c.n_buys == 10 and c.ratio == pytest.approx(0.3)


def test_chasing_buys_without_enough_history_do_not_count_as_chasing(tmp_path):
    c = metrics(tmp_path, {"AAA": FLAT}, [t(1, 0, Side.BUY, 100, 100)]).metrics.chasing
    assert c.n_buys == 1 and c.ratio == 0.0


def test_herding_lift_for_sells_on_index_drop_days(tmp_path):
    # index drops 3% on idx2; drop days = {idx2, idx3 (next session)} -> baseline 2/9
    index = [1000, 1000, 970] + [970] * 6
    trades = [t(1, 0, Side.BUY, 400, 100), t(2, 1, Side.SELL, 100, 100), t(3, 2, Side.SELL, 100, 100),
              t(4, 3, Side.SELL, 100, 100), t(5, 5, Side.SELL, 100, 100)]
    h = metrics(tmp_path, {"AAA": FLAT}, trades, index=index).metrics.herding
    assert h.n_sells == 4 and h.lift == pytest.approx((2 / 4) / (2 / 9))


def test_herding_without_drop_days_is_zero(tmp_path):
    trades = [t(1, 0, Side.BUY, 200, 100), t(2, 1, Side.SELL, 100, 100)]
    assert metrics(tmp_path, {"AAA": FLAT}, trades).metrics.herding.lift == 0.0


def test_performance_totals(tmp_path):
    closes = {"AAA": [100] * 8 + [120]}
    trades = [t(1, 0, Side.BUY, 100, 100, fee=30), t(2, 4, Side.SELL, 50, 110, fee=17, tax=5)]
    p = metrics(tmp_path, closes, trades).metrics.performance
    # avg cost 100.3 ; realized = 50*(110-100.3) - 17 - 5 = 463
    assert p.realized_pnl == pytest.approx(463)
    assert (p.fees_total, p.tax_total) == (47, 5)
    assert p.unrealized_pnl == pytest.approx(50 * (120 - 100.3))
    assert p.excess == pytest.approx(p.twr - p.benchmark_return)


def test_flags_start_empty_and_investor_type_unset(tmp_path):
    m = metrics(tmp_path, {"AAA": FLAT}, [t(1, 0, Side.BUY, 100, 100)])
    assert m.flags == [] and m.investor_type is None
