from datetime import date
from pathlib import Path

import pytest

from app.config import load_thresholds
from app.core.fees import apply_fees
from app.schemas import Side, TradeRow

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")


def row(n, d, side, qty, price, fee=None, tax=None):
    return TradeRow(row_no=n, trade_date=d, symbol="AAA", side=side, quantity=qty, price=price,
                    fee=fee, tax=tax)


D = date(2026, 1, 5)


def test_small_day_uses_030_percent_and_sell_tax():
    out = apply_fees([row(1, D, Side.BUY, 100, 10_000), row(2, D, Side.SELL, 100, 13_000)], CFG)
    # day total 2.3M < 100M -> 0.3%
    assert out[0].fee == 3_000 and out[0].tax == 0
    assert out[1].fee == 3_900 and out[1].tax == 1_300  # 0.1% of 1.3M


def test_day_total_250m_uses_025_percent_for_every_trade():
    trades = [row(1, D, Side.BUY, 10_000, 10_000), row(2, D, Side.BUY, 10_000, 15_000)]
    out = apply_fees(trades, CFG)  # 100M + 150M = 250M
    assert [t.fee for t in out] == [250_000, 375_000]


def test_tier_boundary_is_exclusive_upper_bound():
    out = apply_fees([row(1, D, Side.BUY, 10_000, 10_000)], CFG)  # exactly 100M -> second tier
    assert out[0].fee == 250_000


def test_top_tier_above_500m():
    out = apply_fees([row(1, D, Side.BUY, 100_000, 10_000)], CFG)  # 1bn
    assert out[0].fee == 1_500_000


def test_provided_fee_and_tax_are_never_overwritten():
    out = apply_fees([row(1, D, Side.SELL, 100, 13_000, fee=1, tax=2)], CFG)
    assert (out[0].fee, out[0].tax) == (1, 2)


def test_tiers_are_per_day():
    out = apply_fees([row(1, date(2026, 1, 5), Side.BUY, 10_000, 10_000),
                      row(2, date(2026, 1, 6), Side.BUY, 100, 10_000)], CFG)
    assert out[0].fee == 250_000 and out[1].fee == 3_000


def test_rounding_is_half_up():
    # 150 * 10_010 = 1_501_500 * 0.003 = 4504.5 -> 4505 (banker's rounding would give 4504)
    out = apply_fees([row(1, D, Side.BUY, 150, 10_010)], CFG)
    assert out[0].fee == 4_505


def test_buy_with_tax_is_rejected_by_model():
    with pytest.raises(ValueError):
        row(1, D, Side.BUY, 100, 10_000, tax=5)
