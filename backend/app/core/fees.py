"""Fill blank fee/tax on trades. Provided values are never overwritten."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.config import Thresholds
from app.schemas import PricedTrade, Side, TradeRow


def _round_vnd(x: Decimal) -> int:
    return int(x.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _broker_rate(daily_value: int, cfg: Thresholds) -> Decimal:
    """Upper bounds are exclusive; the last tier is unbounded."""
    for upper, rate in cfg.fees.broker_tiers:
        if daily_value < upper:
            return Decimal(str(rate))
    return Decimal(str(cfg.fees.broker_tiers[-1][1]))


def apply_fees(rows: list[TradeRow], cfg: Thresholds) -> list[PricedTrade]:
    daily: dict[date, int] = defaultdict(int)
    for r in rows:
        daily[r.trade_date] += r.quantity * r.price
    out: list[PricedTrade] = []
    for r in rows:
        value = Decimal(r.quantity * r.price)
        fee = r.fee if r.fee is not None else _round_vnd(value * _broker_rate(daily[r.trade_date], cfg))
        if r.tax is not None:
            tax = r.tax
        elif r.side == Side.SELL:
            tax = _round_vnd(value * Decimal(str(cfg.fees.sell_tax)))
        else:
            tax = 0
        out.append(PricedTrade(**{**r.model_dump(), "fee": fee, "tax": tax}))
    return out
