import statistics
from datetime import date

import pytest

from app.core.ledger import build_ledger
from app.core.portfolio import compute_portfolio
from app.schemas import PricedTrade, Side
from tests.conftest import SESSIONS, build_store


def t(n, d, side, qty, price, symbol="AAA", fee=0, tax=0):
    return PricedTrade(row_no=n, trade_date=d, symbol=symbol, side=side, quantity=qty, price=price,
                       fee=fee, tax=tax)


def run(tmp_path, closes, trades, sectors=None, index=None):
    store = build_store(tmp_path, {"VNINDEX": index or [1000] * 9, **closes}, sectors=sectors)
    return compute_portfolio(trades, build_ledger(trades, store), store)


FLAT = [100] * 9


def test_two_days_no_flows_value_100_to_110_gives_ten_percent(tmp_path):
    closes = {"AAA": [100, 110] + [110] * 7}
    res = run(tmp_path, closes, [t(1, SESSIONS[0], Side.BUY, 1, 100)])
    assert res.daily[1].ret == pytest.approx(0.10)
    assert res.twr == pytest.approx(0.10)  # all later returns are 0


def test_flows_are_removed_from_return(tmp_path):
    # day0: buy 100 @100 (V=10000). day1: price 110, buy another 100 @110 (flow 11000).
    # V1 = 200*110 = 22000, r1 = (22000-11000)/10000 - 1 = 0.10
    closes = {"AAA": [100, 110] + [110] * 7}
    trades = [t(1, SESSIONS[0], Side.BUY, 100, 100), t(2, SESSIONS[1], Side.BUY, 100, 110)]
    res = run(tmp_path, closes, trades)
    assert res.daily[1].ret == pytest.approx(0.10)


def test_first_trade_day_has_no_return_and_series_starts_there(tmp_path):
    res = run(tmp_path, {"AAA": FLAT}, [t(1, SESSIONS[2], Side.BUY, 100, 100)])
    assert res.daily[0].date == SESSIONS[2] and res.daily[0].ret is None
    assert res.first_date == SESSIONS[2] and res.last_date == SESSIONS[-1]


def test_benchmark_excess_and_rebased_series(tmp_path):
    index = [1000, 1000, 1100] + [1100] * 6
    closes = {"AAA": [100] * 9}
    res = run(tmp_path, closes, [t(1, SESSIONS[0], Side.BUY, 100, 100)], index=index)
    assert res.benchmark_return == pytest.approx(0.10)
    assert res.twr == pytest.approx(0.0)
    assert res.excess == pytest.approx(-0.10)
    assert res.rebased[0].portfolio == 100 and res.rebased[0].benchmark == 100
    assert res.rebased[-1].benchmark == pytest.approx(110)


def test_volatility_uses_sample_std_times_sqrt_250(tmp_path):
    closes = {"AAA": [100, 110, 99, 99, 99, 99, 99, 99, 99]}
    res = run(tmp_path, closes, [t(1, SESSIONS[0], Side.BUY, 1, 100)])
    rets = [0.10, 99 / 110 - 1] + [0.0] * 6
    assert res.vol_annual == pytest.approx(statistics.stdev(rets) * 250 ** 0.5)


def test_benchmark_volatility_is_measured_over_the_same_sessions(tmp_path):
    index = [1000, 900, 1000, 1100, 1100, 1100, 1100, 1100, 1100]
    res = run(tmp_path, {"AAA": [100] * 9}, [t(1, SESSIONS[2], Side.BUY, 100, 100)], index=index)
    # the portfolio starts on session 2, so the index move 1000 -> 900 -> 1000 before it does not count
    rets = [0.10] + [0.0] * 5
    assert res.benchmark_vol == pytest.approx(statistics.stdev(rets) * 250 ** 0.5)


def test_unrealized_pnl_and_weights(tmp_path):
    closes = {"AAA": [100] * 8 + [120], "BBB": [200] * 9}
    trades = [t(1, SESSIONS[0], Side.BUY, 100, 100, "AAA", fee=50),
              t(2, SESSIONS[0], Side.BUY, 50, 200, "BBB")]
    res = run(tmp_path, closes, trades, sectors={"AAA": "Ngân hàng", "BBB": "Thép"})
    # AAA avg cost = (10000+50)/100 = 100.5 -> 100*(120-100.5) = 1950 ; BBB 0
    assert res.unrealized_pnl == pytest.approx(1950)
    # values: AAA 12000, BBB 10000
    assert res.weights_symbol["AAA"] == pytest.approx(12000 / 22000)
    assert res.weights_sector["Thép"] == pytest.approx(10000 / 22000)
    assert sum(res.weights_symbol.values()) == pytest.approx(1.0)


def test_fully_sold_portfolio_skips_days_with_zero_prior_value(tmp_path):
    trades = [t(1, SESSIONS[0], Side.BUY, 100, 100), t(2, SESSIONS[1], Side.SELL, 100, 100)]
    res = run(tmp_path, {"AAA": FLAT}, trades)
    assert res.daily[2].ret is None  # prior value is zero
    assert res.twr == pytest.approx(0.0)
    assert res.weights_symbol == {}


def test_uses_only_days_from_first_trade(tmp_path):
    res = run(tmp_path, {"AAA": FLAT}, [t(1, date(2026, 1, 12), Side.BUY, 100, 100)])
    assert res.daily[0].date == date(2026, 1, 12)
