from datetime import date

import pytest
from pydantic import ValidationError

from app.core.prices import NotTradingDayError, PriceStore, UnknownSymbolError
from app.schemas import PriceBar


def test_loads_symbols_and_trading_days_from_vnindex(price_dir):
    store = PriceStore(price_dir)
    assert store.symbols == {"VNINDEX", "AAA", "BBB"}
    assert len(store.trading_days) == 9
    assert store.trading_days[0] == date(2026, 1, 5)


def test_is_trading_day_false_for_weekend_and_holiday(price_dir):
    store = PriceStore(price_dir)
    assert store.is_trading_day(date(2026, 1, 5))
    assert not store.is_trading_day(date(2026, 1, 10))  # Saturday
    assert not store.is_trading_day(date(2026, 1, 14))  # missing session


def test_bar_returns_ohlc(price_dir):
    bar = PriceStore(price_dir).bar("AAA", date(2026, 1, 5))
    assert (bar.open, bar.high, bar.low, bar.close) == (10000, 10100, 9900, 10000)


def test_unknown_symbol_raises_typed_error(price_dir):
    with pytest.raises(UnknownSymbolError):
        PriceStore(price_dir).bar("ZZZ", date(2026, 1, 5))


def test_non_trading_date_raises_typed_error(price_dir):
    with pytest.raises(NotTradingDayError):
        PriceStore(price_dir).bar("AAA", date(2026, 1, 14))


def test_prev_session_skips_weekend_and_holiday(price_dir):
    store = PriceStore(price_dir)
    # sessions: 5,6,7,8,9,12,13,15,16 -> 5 sessions before the 16th is the 8th
    assert store.prev_session(date(2026, 1, 16), 5) == date(2026, 1, 8)
    assert store.prev_session(date(2026, 1, 12)) == date(2026, 1, 9)  # across weekend
    assert store.prev_session(date(2026, 1, 15)) == date(2026, 1, 13)  # across holiday


def test_prev_session_before_history_raises(price_dir):
    with pytest.raises(NotTradingDayError):
        PriceStore(price_dir).prev_session(date(2026, 1, 6), 5)


def test_next_session(price_dir):
    store = PriceStore(price_dir)
    assert store.next_session(date(2026, 1, 13)) == date(2026, 1, 15)
    assert store.next_session(date(2026, 1, 16)) is None


def test_close_series_indexed_by_date(price_dir):
    s = PriceStore(price_dir).close_series("AAA")
    assert s.loc[date(2026, 1, 8)] == 9900
    assert len(s) == 9


def test_sector_lookup(price_dir):
    store = PriceStore(price_dir)
    assert store.sector("AAA") == "Ngân hàng"
    with pytest.raises(UnknownSymbolError):
        store.sector("ZZZ")


def test_pricebar_rejects_low_above_open():
    with pytest.raises(ValidationError):
        PriceBar(date=date(2026, 1, 5), open=9000, high=10100, low=9500, close=10000, volume=1)


def test_pricebar_accepts_valid_bar():
    b = PriceBar(date=date(2026, 1, 5), open=10000, high=10100, low=9900, close=10050, volume=10)
    assert b.close == 10050
