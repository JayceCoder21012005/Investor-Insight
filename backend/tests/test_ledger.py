from datetime import date
from decimal import Decimal

import pytest

from app.core.ledger import Ledger, build_ledger
from app.schemas import PricedTrade, Side
from tests.conftest import SESSIONS, build_store


def t(n, d, side, qty, price, fee=0, tax=0, symbol="AAA"):
    return PricedTrade(row_no=n, trade_date=d, symbol=symbol, side=side, quantity=qty, price=price,
                       fee=fee, tax=tax)


D1 = date(2026, 1, 5)


def test_average_cost_includes_buy_fees():
    lg = Ledger()
    lg.apply(t(1, D1, Side.BUY, 100, 10_000, fee=3_000))
    assert lg.positions["AAA"].avg_cost == Decimal(10_030)
    lg.apply(t(2, D1, Side.BUY, 100, 12_000, fee=3_600))
    pos = lg.positions["AAA"]
    assert pos.qty == 200 and pos.avg_cost == Decimal(11_033)  # acceptance example


def test_sell_realized_pnl_net_of_fee_and_tax_and_avg_cost_unchanged():
    lg = Ledger()
    lg.apply(t(1, D1, Side.BUY, 100, 10_000, fee=3_000))
    lg.apply(t(2, D1, Side.BUY, 100, 12_000, fee=3_600))
    r = lg.apply(t(3, date(2026, 1, 6), Side.SELL, 100, 13_000, fee=3_900, tax=1_300))
    assert r.realized == Decimal(191_500)
    assert r.avg_cost == Decimal(11_033)
    assert r.ret == pytest.approx(13_000 / 11_033 - 1)
    assert lg.positions["AAA"].qty == 100 and lg.positions["AAA"].avg_cost == Decimal(11_033)


def test_holding_days_is_quantity_weighted_over_fifo_lots():
    lg = Ledger()
    lg.apply(t(1, date(2026, 1, 1), Side.BUY, 100, 10_000))
    lg.apply(t(2, date(2026, 2, 1), Side.BUY, 100, 10_000))
    r = lg.apply(t(3, date(2026, 3, 1), Side.SELL, 150, 11_000))
    assert r.holding_days == pytest.approx((59 * 100 + 28 * 50) / 150)


def test_fifo_leftover_lot_is_used_by_next_sell():
    lg = Ledger()
    lg.apply(t(1, date(2026, 1, 1), Side.BUY, 100, 10_000))
    lg.apply(t(2, date(2026, 2, 1), Side.BUY, 100, 10_000))
    lg.apply(t(3, date(2026, 3, 1), Side.SELL, 150, 11_000))
    r = lg.apply(t(4, date(2026, 3, 11), Side.SELL, 50, 11_000))
    assert r.holding_days == pytest.approx(38)  # remaining 50 shares from Feb 1


def test_avg_cost_resets_when_position_closed():
    lg = Ledger()
    lg.apply(t(1, D1, Side.BUY, 100, 10_000))
    lg.apply(t(2, D1, Side.SELL, 100, 11_000))
    assert "AAA" not in lg.positions
    lg.apply(t(3, D1, Side.BUY, 100, 20_000))
    assert lg.positions["AAA"].avg_cost == Decimal(20_000)


def test_selling_more_than_held_raises():
    lg = Ledger()
    lg.apply(t(1, D1, Side.BUY, 100, 10_000))
    with pytest.raises(ValueError):
        lg.apply(t(2, D1, Side.SELL, 200, 10_000))


def test_snapshots_cover_each_trading_day_from_first_trade(tmp_path):
    store = build_store(tmp_path, {"VNINDEX": [1000] * 9, "AAA": [10_000] * 9})
    trades = [t(1, SESSIONS[1], Side.BUY, 100, 10_000), t(2, SESSIONS[3], Side.SELL, 100, 10_000)]
    res = build_ledger(trades, store)
    days = sorted(res.end)
    assert days[0] == SESSIONS[1] and days[-1] == SESSIONS[-1]
    assert res.start[SESSIONS[1]] == {}  # nothing held at the open of the first trade day
    assert res.end[SESSIONS[1]]["AAA"].qty == 100
    assert res.start[SESSIONS[2]]["AAA"].qty == 100
    assert res.end[SESSIONS[3]] == {}
    assert len(res.realized) == 1 and res.realized[0].date == SESSIONS[3]


def test_trade_on_non_trading_day_raises(tmp_path):
    store = build_store(tmp_path, {"VNINDEX": [1000] * 9, "AAA": [10_000] * 9})
    with pytest.raises(ValueError):
        build_ledger([t(1, date(2026, 1, 14), Side.BUY, 100, 10_000)], store)
