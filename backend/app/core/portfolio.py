"""Daily portfolio value, time-weighted return, volatility, benchmark comparison, weights."""
from __future__ import annotations

import itertools
import math
import statistics
from collections import defaultdict
from datetime import date

from app.core.prices import INDEX_SYMBOL, PriceStore, UnknownSymbolError
from app.schemas import DailyPoint, LedgerResult, PortfolioResult, PricedTrade, RebasedPoint, Side

TRADING_DAYS_PER_YEAR = 250
OTHER_SECTOR = "Khác"


def _value(positions: dict, d: date, closes: dict) -> float:
    return sum(p.qty * closes[sym][d] for sym, p in positions.items())


def compute_portfolio(trades: list[PricedTrade], ledger: LedgerResult, prices: PriceStore) -> PortfolioResult:
    days = sorted(ledger.end)
    if not days:
        raise ValueError("no trades")
    closes = {s: prices.close_series(s).to_dict() for s in {t.symbol for t in trades}}
    index_close = prices.close_series(INDEX_SYMBOL).to_dict()

    flows: dict[date, float] = defaultdict(float)  # gross BUY - SELL value
    for t in trades:
        flows[t.trade_date] += (1 if t.side == Side.BUY else -1) * t.quantity * t.price

    daily: list[DailyPoint] = []
    prev_value = 0.0
    for d in days:
        v = _value(ledger.end[d], d, closes)
        ret = (v - flows.get(d, 0.0)) / prev_value - 1 if prev_value > 0 else None
        daily.append(DailyPoint(date=d, value=v, flow=flows.get(d, 0.0), ret=ret))
        prev_value = v

    rets = [p.ret for p in daily if p.ret is not None]
    twr = math.prod(1 + r for r in rets) - 1 if rets else 0.0
    vol = statistics.stdev(rets) * math.sqrt(TRADING_DAYS_PER_YEAR) if len(rets) >= 2 else 0.0
    index_rets = [index_close[b] / index_close[a] - 1 for a, b in itertools.pairwise(days)]
    benchmark_vol = (statistics.stdev(index_rets) * math.sqrt(TRADING_DAYS_PER_YEAR)
                     if len(index_rets) >= 2 else 0.0)

    first, last = days[0], days[-1]
    benchmark_return = index_close[last] / index_close[first] - 1

    level, rebased = 100.0, []
    for p in daily:
        if p.ret is not None:
            level *= 1 + p.ret
        rebased.append(RebasedPoint(date=p.date, portfolio=level,
                                    benchmark=100.0 * index_close[p.date] / index_close[first]))

    final = ledger.end[last]
    unrealized = sum(p.qty * (closes[s][last] - float(p.avg_cost)) for s, p in final.items())
    total = _value(final, last, closes)
    w_sym: dict[str, float] = {}
    w_sec: dict[str, float] = defaultdict(float)
    if total > 0:
        for s, p in final.items():
            w = p.qty * closes[s][last] / total
            w_sym[s] = w
            try:
                sector = prices.sector(s)
            except UnknownSymbolError:
                sector = OTHER_SECTOR
            w_sec[sector] += w

    return PortfolioResult(first_date=first, last_date=last, daily=daily, rebased=rebased, twr=twr,
                           vol_annual=vol, benchmark_vol=benchmark_vol, benchmark_return=benchmark_return, excess=twr - benchmark_return,
                           unrealized_pnl=unrealized, weights_symbol=w_sym, weights_sector=dict(w_sec))
