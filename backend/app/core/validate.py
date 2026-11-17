"""CSV bytes -> clean TradeRows or a row-level error report (Vietnamese messages).

Row numbers are 1-based over *data* rows (the header is not counted).
"""
from __future__ import annotations

import csv
import io
import re

from pydantic import ValidationError

from app.core.prices import INDEX_SYMBOL, PriceStore
from app.schemas import RowIssue, Side, TradeRow, ValidationResult

REQUIRED = ["trade_date", "symbol", "side", "quantity", "price"]
OPTIONAL = ["fee", "tax"]

# Header spellings from other brokers map here later; keys are lowercase, stripped.
COLUMN_ALIASES: dict[str, str] = {
    "trade_date": "trade_date", "date": "trade_date", "ngày giao dịch": "trade_date", "ngày": "trade_date",
    "ngay giao dich": "trade_date", "ngay": "trade_date",
    "symbol": "symbol", "ticker": "symbol", "mã": "symbol", "mã ck": "symbol", "mã cp": "symbol", "ma": "symbol",
    "side": "side", "loại lệnh": "side", "loai lenh": "side", "mua/bán": "side",
    "quantity": "quantity", "khối lượng": "quantity", "khoi luong": "quantity", "kl": "quantity",
    "price": "price", "giá": "price", "gia": "price", "giá khớp": "price",
    "fee": "fee", "phí": "fee", "phi": "fee",
    "tax": "tax", "thuế": "tax", "thue": "tax",
}

FIELD_VI = {"trade_date": "Ngày giao dịch", "symbol": "Mã cổ phiếu", "side": "Loại lệnh",
            "quantity": "Khối lượng", "price": "Giá", "fee": "Phí", "tax": "Thuế"}

# pydantic error type -> Vietnamese template ({f} = field label)
ERROR_VI = {
    "missing": "{f} bị thiếu",
    "date_type": "{f} không hợp lệ, cần định dạng YYYY-MM-DD",
    "date_parsing": "{f} không hợp lệ, cần định dạng YYYY-MM-DD",
    "date_from_datetime_parsing": "{f} không hợp lệ, cần định dạng YYYY-MM-DD",
    "int_parsing": "{f} phải là số nguyên",
    "int_from_float": "{f} phải là số nguyên",
    "int_type": "{f} phải là số nguyên",
    "greater_than": "{f} phải lớn hơn 0",
    "greater_than_equal": "{f} không được âm",
    "string_pattern_mismatch": "{f} không hợp lệ (3–10 ký tự chữ hoặc số)",
    "string_too_short": "{f} bị thiếu",
    "enum": "{f} phải là BUY/SELL (hoặc Mua/Bán)",
    "buy_tax": "Lệnh mua không có thuế, hãy để trống hoặc 0",
}
CUSTOM_ERROR_FIELD = {"buy_tax": "tax"}

_THOUSANDS = re.compile(r"[,\s  ]")
_TRAILING_ZERO_DECIMAL = re.compile(r"^(\d+)\.0+$")


def _file_error(msg: str) -> ValidationResult:
    return ValidationResult(rows=[], errors=[RowIssue(row=0, field="file", message=msg)], warnings=[])


def _clean_number(raw: str) -> str:
    s = _THOUSANDS.sub("", raw)
    m = _TRAILING_ZERO_DECIMAL.match(s)
    return m.group(1) if m else s


def _issue_from_pydantic(row_no: int, err: dict) -> RowIssue:
    etype = err["type"]
    loc = err["loc"]
    field = str(loc[0]) if loc else CUSTOM_ERROR_FIELD.get(etype, "row")
    label = FIELD_VI.get(field, field)
    template = ERROR_VI.get(etype, "{f} không hợp lệ")
    return RowIssue(row=row_no, field=field, message=f"Dòng {row_no}: " + template.format(f=label))


def _read_table(csv_bytes: bytes) -> tuple[list[str], list[dict[str, str]]] | str:
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "Tệp phải được lưu bằng mã hóa UTF-8"
    if not text.strip():
        return "Tệp CSV rỗng"
    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    raw_header = next(reader)
    header = [COLUMN_ALIASES.get(h.strip().lower(), h.strip().lower()) for h in raw_header]
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        return f"Thiếu cột bắt buộc: {', '.join(missing)}"
    rows = []
    for cells in reader:
        if not any(c.strip() for c in cells):
            continue
        rows.append({h: (cells[i].strip() if i < len(cells) else "") for i, h in enumerate(header)})
    return header, rows


def _row_payload(row_no: int, raw: dict[str, str]) -> dict:
    payload: dict = {"row_no": row_no}
    for col in REQUIRED + OPTIONAL:
        v = raw.get(col, "")
        if v == "":
            continue  # missing required -> pydantic "missing"; optional -> None
        payload[col] = _clean_number(v) if col in ("quantity", "price", "fee", "tax") else v
    return payload


def validate(csv_bytes: bytes, prices: PriceStore) -> ValidationResult:
    table = _read_table(csv_bytes)
    if isinstance(table, str):
        return _file_error(table)
    _, raw_rows = table

    errors: list[RowIssue] = []
    warnings: list[RowIssue] = []
    parsed: list[TradeRow] = []

    # Step 1: shape and types, one pydantic model per row.
    for i, raw in enumerate(raw_rows, start=1):
        try:
            parsed.append(TradeRow.model_validate(_row_payload(i, raw)))
        except ValidationError as e:
            errors.extend(_issue_from_pydantic(i, err) for err in e.errors())

    # Step 2a: checks that need price data (independent per row).
    tradable = prices.symbols - {INDEX_SYMBOL}
    for r in parsed:
        symbol_ok = r.symbol in tradable
        day_ok = prices.is_trading_day(r.trade_date)
        if not symbol_ok:
            errors.append(RowIssue(row=r.row_no, field="symbol",
                                   message=f"Dòng {r.row_no}: Mã {r.symbol} không có trong dữ liệu giá"))
        if not day_ok:
            errors.append(RowIssue(row=r.row_no, field="trade_date",
                                   message=f"Dòng {r.row_no}: Ngày {r.trade_date} không phải phiên giao dịch"))
        if r.quantity % 100 != 0:
            warnings.append(RowIssue(row=r.row_no, field="quantity",
                                     message=f"Dòng {r.row_no}: Khối lượng {r.quantity} là lô lẻ (không chia hết cho 100)"))
        if symbol_ok and day_ok:
            bar = prices.bar(r.symbol, r.trade_date)
            if not (bar.low * 0.95 <= r.price <= bar.high * 1.05):
                warnings.append(RowIssue(
                    row=r.row_no, field="price",
                    message=f"Dòng {r.row_no}: Giá {r.price:,} nằm ngoài khoảng giá phiên "
                            f"{bar.low:,.0f}–{bar.high:,.0f} (±5%)"))

    # Step 2b: running holdings. Date order (stable), so a newest-first export is not flagged.
    held: dict[str, int] = {}
    for r in sorted(parsed, key=lambda t: (t.trade_date, t.row_no)):
        if r.side == Side.BUY:
            held[r.symbol] = held.get(r.symbol, 0) + r.quantity
        else:
            have = held.get(r.symbol, 0)
            if r.quantity > have:
                errors.append(RowIssue(
                    row=r.row_no, field="quantity",
                    message=f"Dòng {r.row_no}: Bán {r.quantity} {r.symbol} nhưng chỉ đang nắm giữ {have}"))
            held[r.symbol] = max(0, have - r.quantity)

    errors.sort(key=lambda x: x.row)
    warnings.sort(key=lambda x: x.row)
    return ValidationResult(rows=[] if errors else parsed, errors=errors, warnings=warnings)
