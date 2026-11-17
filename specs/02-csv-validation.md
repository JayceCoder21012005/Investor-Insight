# 02 — CSV validation and fees

## Goal
Turn an uploaded CSV into clean `TradeRow`s or a row-level error report.

## Files
`app/core/validate.py`, `app/core/fees.py`, `app/schemas.py` (TradeRow, ValidationResult), `tests/test_validate.py`, `tests/test_fees.py`

## CSV
| column | type | required |
|---|---|---|
| trade_date | YYYY-MM-DD | yes |
| symbol | str, uppercase | yes |
| side | BUY / SELL | yes |
| quantity | int > 0 | yes |
| price | VND per share, > 0 | yes |
| fee | VND | no |
| tax | VND | no |

Keep a `COLUMN_ALIASES` dict so other brokers' headers can map later.

## Models (`schemas.py`)
```python
class TradeRow(Model):
    row_no: Annotated[int, Field(ge=1)]
    trade_date: date
    symbol: Symbol
    side: Side
    quantity: PositiveQty
    price: Annotated[int, Field(gt=0)]
    fee: VND | None = None
    tax: VND | None = None

    @field_validator("side", mode="before")
    def normalize_side(cls, v): ...          # accepts "buy", "Mua", "B" → BUY

    @model_validator(mode="after")
    def buy_has_no_tax(self): ...            # BUY with tax > 0 → error

class RowIssue(Model):
    row: int; field: str; message: str

class ValidationResult(Model):
    rows: list[TradeRow]; errors: list[RowIssue]; warnings: list[RowIssue]
```
Step 1: parse each CSV row with `TradeRow.model_validate`; convert each `ValidationError` entry into a Vietnamese `RowIssue` (map pydantic error types → messages in one dict). Step 2: run the checks below that need prices or running state.

## validate(csv_bytes, prices) -> ValidationResult
`ValidationResult = {rows: list[TradeRow], errors: list[{row, field, message}], warnings: list[{row, field, message}]}`

Process rows in file order, tracking held quantity per symbol.

| check | level |
|---|---|
| missing required column | file error (stop) |
| bad date, or not a trading day | row error |
| symbol not in PriceStore | row error |
| quantity not positive int, price ≤ 0 | row error |
| SELL quantity > held quantity | row error |
| quantity % 100 != 0 | warning "lô lẻ" |
| price outside [day_low×0.95, day_high×1.05] | warning |

Any row error → `rows = []`. Messages in Vietnamese with the 1-based row number.

## fees.py
- `apply_fees(rows: list[TradeRow]) -> list[PricedTrade]`: only fills blank `fee`/`tax` (models are frozen; build new objects). `PricedTrade` = `TradeRow` with `fee: VND` and `tax: VND` required, so downstream code never sees `None`.
- Fee: group by `trade_date`, sum `quantity*price`, pick rate from `fees.broker_tiers` (upper bound exclusive except last), `fee = round(value*rate)` per trade.
- Tax: SELL → `round(value*fees.sell_tax)`; BUY → 0.

## Acceptance
- Oversell → error on that row.
- quantity 150 → warning, row kept.
- Day total 250M → every trade that day uses 0.25%.
- Provided fee/tax are never overwritten.
