from datetime import date

import pytest

from app.core.prices import PriceStore
from app.core.validate import validate

HEADER = "trade_date,symbol,side,quantity,price,fee,tax\n"


@pytest.fixture
def store(price_dir):
    return PriceStore(price_dir)


def csv(*lines, header=HEADER):
    return (header + "\n".join(lines) + "\n").encode("utf-8")


def test_valid_csv_returns_rows_without_errors(store):
    r = validate(csv("2026-01-05,AAA,BUY,100,10000,,", "2026-01-06,AAA,SELL,100,10100,,"), store)
    assert r.errors == [] and len(r.rows) == 2
    assert r.rows[0].fee is None and r.rows[1].row_no == 2


def test_missing_required_column_is_file_error(store):
    r = validate(b"trade_date,symbol,side,quantity\n2026-01-05,AAA,BUY,100\n", store)
    assert r.rows == [] and len(r.errors) == 1
    assert r.errors[0].row == 0 and "price" in r.errors[0].message


def test_header_aliases_and_side_aliases(store):
    hdr = "Ngày giao dịch,Mã,Loại lệnh,Khối lượng,Giá,Phí,Thuế\n"
    r = validate(csv("2026-01-05,aaa,Mua,100,10000,,", "2026-01-06,AAA,Bán,100,10100,,", header=hdr), store)
    assert r.errors == []
    assert [x.side.value for x in r.rows] == ["BUY", "SELL"] and r.rows[0].symbol == "AAA"


def test_bom_is_tolerated(store):
    r = validate(b"\xef\xbb\xbf" + csv("2026-01-05,AAA,BUY,100,10000,,"), store)
    assert r.errors == []


def test_bad_date_format_row_error_in_vietnamese(store):
    r = validate(csv("05/01/2026,AAA,BUY,100,10000,,"), store)
    assert r.rows == [] and r.errors[0].row == 1 and r.errors[0].field == "trade_date"
    assert "YYYY-MM-DD" in r.errors[0].message


def test_non_trading_day_is_error(store):
    r = validate(csv("2026-01-14,AAA,BUY,100,10000,,"), store)  # holiday gap in fixture
    assert r.rows == [] and "phiên" in r.errors[0].message


def test_unknown_symbol_and_index_symbol_are_errors(store):
    r = validate(csv("2026-01-05,ZZZ,BUY,100,10000,,", "2026-01-05,VNINDEX,BUY,100,1000,,"), store)
    assert [e.row for e in r.errors] == [1, 2] and all(e.field == "symbol" for e in r.errors)


@pytest.mark.parametrize("qty,price", [("0", "10000"), ("-100", "10000"), ("abc", "10000"),
                                       ("100", "0"), ("100", "-5")])
def test_non_positive_quantity_or_price_is_error(store, qty, price):
    r = validate(csv(f"2026-01-05,AAA,BUY,{qty},{price},,"), store)
    assert r.rows == [] and len(r.errors) >= 1


def test_oversell_is_error_on_that_row(store):
    r = validate(csv("2026-01-05,AAA,BUY,100,10000,,", "2026-01-06,AAA,SELL,200,10100,,"), store)
    assert r.rows == [] and [e.row for e in r.errors] == [2] and r.errors[0].field == "quantity"


def test_newest_first_file_does_not_false_flag_oversell(store):
    r = validate(csv("2026-01-06,AAA,SELL,100,10100,,", "2026-01-05,AAA,BUY,100,10000,,"), store)
    assert r.errors == []


def test_odd_lot_is_warning_and_row_kept(store):
    r = validate(csv("2026-01-05,AAA,BUY,150,10000,,"), store)
    assert r.errors == [] and len(r.rows) == 1
    assert r.warnings[0].field == "quantity" and "lô lẻ" in r.warnings[0].message


def test_price_outside_band_is_warning(store):
    r = validate(csv("2026-01-05,AAA,BUY,100,12000,,"), store)  # band 9405..10605
    assert r.errors == [] and len(r.rows) == 1 and r.warnings[0].field == "price"


def test_price_inside_band_has_no_warning(store):
    r = validate(csv("2026-01-05,AAA,BUY,100,10500,,"), store)
    assert r.warnings == []


def test_any_row_error_empties_rows_but_keeps_warnings(store):
    r = validate(csv("2026-01-05,AAA,BUY,150,10000,,", "2026-01-06,ZZZ,BUY,100,10000,,"), store)
    assert r.rows == [] and len(r.errors) == 1 and len(r.warnings) == 1


def test_buy_with_tax_is_error(store):
    r = validate(csv("2026-01-05,AAA,BUY,100,10000,,500"), store)
    assert r.rows == [] and r.errors[0].field == "tax"


def test_provided_fee_tax_are_parsed(store):
    r = validate(csv("2026-01-05,AAA,BUY,100,10000,3000,0", "2026-01-06,AAA,SELL,100,10100,3030,1010"), store)
    assert (r.rows[1].fee, r.rows[1].tax) == (3030, 1010)
    assert r.rows[0].trade_date == date(2026, 1, 5)


def test_empty_file_has_file_error(store):
    r = validate(b"", store)
    assert r.rows == [] and r.errors
