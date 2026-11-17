"""Positions, realized P&L and holding periods. Average cost drives P&L; FIFO lots only drive holding days."""
from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal

from app.core.prices import PriceStore
from app.schemas import LedgerResult, Position, PricedTrade, Realized, Side


class Ledger:
    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}
        self._lots: dict[str, deque[list]] = {}  # symbol -> deque of [trade_date, qty]

    def snapshot(self) -> dict[str, Position]:
        return dict(self.positions)

    def apply(self, t: PricedTrade) -> Realized | None:
        if t.side == Side.BUY:
            self._buy(t)
            return None
        return self._sell(t)

    def _buy(self, t: PricedTrade) -> None:
        old = self.positions.get(t.symbol)
        qty0, avg0 = (old.qty, old.avg_cost) if old else (0, Decimal(0))
        avg = (qty0 * avg0 + t.quantity * Decimal(t.price) + t.fee) / (qty0 + t.quantity)
        self.positions[t.symbol] = Position(qty=qty0 + t.quantity, avg_cost=avg)
        self._lots.setdefault(t.symbol, deque()).append([t.trade_date, t.quantity])

    def _sell(self, t: PricedTrade) -> Realized:
        pos = self.positions.get(t.symbol)
        if pos is None or t.quantity > pos.qty:
            raise ValueError(f"row {t.row_no}: selling {t.quantity} {t.symbol} but holding {pos.qty if pos else 0}")
        realized = t.quantity * (Decimal(t.price) - pos.avg_cost) - t.fee - t.tax
        ret = float(Decimal(t.price) / pos.avg_cost - 1) if pos.avg_cost > 0 else 0.0
        holding_days = self._consume_lots(t)
        left = pos.qty - t.quantity
        if left == 0:
            del self.positions[t.symbol]
            self._lots.pop(t.symbol, None)
        else:
            self.positions[t.symbol] = Position(qty=left, avg_cost=pos.avg_cost)  # avg cost unchanged
        return Realized(symbol=t.symbol, date=t.trade_date, qty=t.quantity, sell_price=t.price,
                        avg_cost=pos.avg_cost, realized=realized, ret=ret, holding_days=holding_days)

    def _consume_lots(self, t: PricedTrade) -> float:
        lots, need, weighted = self._lots[t.symbol], t.quantity, 0
        while need > 0:
            lot = lots[0]
            take = min(need, lot[1])
            weighted += take * (t.trade_date - lot[0]).days
            lot[1] -= take
            need -= take
            if lot[1] == 0:
                lots.popleft()
        return weighted / t.quantity


def build_ledger(trades: list[PricedTrade], prices: PriceStore) -> LedgerResult:
    if not trades:
        return LedgerResult(realized=[], start={}, end={})
    ordered = sorted(trades, key=lambda x: (x.trade_date, x.row_no))
    for t in ordered:
        if not prices.is_trading_day(t.trade_date):
            raise ValueError(f"row {t.row_no}: {t.trade_date} is not a trading day")
    by_day: dict = defaultdict(list)
    for t in ordered:
        by_day[t.trade_date].append(t)

    ledger, realized, start, end = Ledger(), [], {}, {}
    for d in (d for d in prices.trading_days if d >= ordered[0].trade_date):
        start[d] = ledger.snapshot()
        for t in by_day.get(d, []):
            r = ledger.apply(t)
            if r is not None:
                realized.append(r)
        end[d] = ledger.snapshot()
    return LedgerResult(realized=realized, start=start, end=end)
