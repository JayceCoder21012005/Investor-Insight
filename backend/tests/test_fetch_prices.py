from datetime import date

import pandas as pd
import pytest

from scripts.fetch_prices import PriceDataError, check_consistency, normalize_frame


def raw(closes, symbol_unit=1):
    return pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-01-05", "2026-01-06"]),
            "open": [c * symbol_unit for c in closes],
            "high": [c * symbol_unit + 0.2 for c in closes],
            "low": [c * symbol_unit - 0.2 for c in closes],
            "close": [c * symbol_unit for c in closes],
            "volume": [100, 200],
        }
    )


def test_stock_prices_are_multiplied_by_1000():
    df = normalize_frame("FPT", raw([95.0, 96.0]))
    assert list(df["close"]) == [95000.0, 96000.0]
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert df["date"].iloc[0] == date(2026, 1, 5)


def test_vnindex_is_not_multiplied():
    df = normalize_frame("VNINDEX", raw([1650.0, 1660.0]))
    assert list(df["close"]) == [1650.0, 1660.0]


def test_invalid_bar_is_rejected():
    bad = raw([95.0, 96.0])
    bad.loc[0, "low"] = 99.0  # low above open/close
    with pytest.raises(PriceDataError):
        normalize_frame("FPT", bad)


def test_consistency_requires_same_dates_as_vnindex():
    vn = normalize_frame("VNINDEX", raw([1650.0, 1660.0]))
    short = normalize_frame("FPT", raw([95.0, 96.0]).iloc[:1])
    with pytest.raises(PriceDataError, match="FPT"):
        check_consistency({"VNINDEX": vn, "FPT": short}, min_sessions=1, max_sessions=10)


DCHART = {"s": "ok", "t": [1762128000, 1762214400], "o": [92.122, 92.389], "h": [94.341, 92.921],
          "l": [91.856, 90.259], "c": [93.187, 91.679], "v": [20963600, 10620700]}


def test_vndirect_payload_becomes_a_vnstock_style_frame():
    from scripts.fetch_prices import parse_dchart

    df = normalize_frame("FPT", parse_dchart("FPT", DCHART))
    assert list(df["date"]) == [date(2025, 11, 3), date(2025, 11, 4)]  # epoch seconds, Vietnam calendar day
    assert list(df["close"]) == [93187.0, 91679.0] and list(df["volume"]) == [20963600, 10620700]


@pytest.mark.parametrize("payload", [{"s": "no_data", "t": []}, {"s": "ok", "t": []}, {"error": "x"}])
def test_vndirect_empty_or_error_payload_is_a_price_data_error(payload):
    from scripts.fetch_prices import parse_dchart

    with pytest.raises(PriceDataError, match="FPT"):
        parse_dchart("FPT", payload)


def test_consistency_checks_session_count_range():
    vn = normalize_frame("VNINDEX", raw([1650.0, 1660.0]))
    with pytest.raises(PriceDataError, match="sessions"):
        check_consistency({"VNINDEX": vn}, min_sessions=240, max_sessions=250)
