"""Behavioral metrics: one function returns the full Metrics object. Pure, deterministic."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.config import Thresholds
from app.core.ledger import build_ledger
from app.core.portfolio import compute_portfolio
from app.core.prices import INDEX_SYMBOL, NotTradingDayError, PriceStore
from app.schemas import (
    Activity,
    ChasingMetrics,
    Concentration,
    DispositionMetrics,
    HerdingMetrics,
    Holding,
    LedgerResult,
    Metrics,
    MetricValues,
    MonthlyTurnover,
    Performance,
    Period,
    PortfolioResult,
    PricedTrade,
    ProfileInfo,
    Realized,
    RiskProfile,
    Side,
)


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _months_between(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _weighted_days(rows: list[Realized]) -> float | None:
    qty = sum(r.qty for r in rows)
    return sum(r.holding_days * r.qty for r in rows) / qty if qty else None


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


# ------------------------------------------------------------------ groups
def _concentration(pf: PortfolioResult) -> Concentration:
    w = pf.weights_symbol
    top_sym = max(w, key=w.get) if w else None
    top_sec = max(pf.weights_sector, key=pf.weights_sector.get) if pf.weights_sector else None
    return Concentration(
        hhi=sum(x * x for x in w.values()),
        top_symbol=top_sym, top_symbol_weight=w[top_sym] if top_sym else 0.0,
        top_sector=top_sec, top_sector_weight=pf.weights_sector[top_sec] if top_sec else 0.0,
    )


def _activity(trades: list[PricedTrade], pf: PortfolioResult, months: int) -> Activity:
    sells: dict[str, float] = defaultdict(float)
    for t in trades:
        if t.side == Side.SELL:
            sells[_month_key(t.trade_date)] += t.quantity * t.price
    values: dict[str, list[float]] = defaultdict(list)
    for p in pf.daily:
        values[_month_key(p.date)].append(p.value)
    monthly = []
    for key in _months_between(pf.first_date, pf.last_date):
        vs = values.get(key, [])
        mean_v = sum(vs) / len(vs) if vs else 0.0
        monthly.append(MonthlyTurnover(month=key, value=sells[key] / mean_v if mean_v > 0 else 0.0))
    avg = sum(m.value for m in monthly) / len(monthly) if monthly else 0.0
    return Activity(monthly_turnover=monthly, avg_turnover=avg, trades_per_month=len(trades) / months)


def _holding(realized: list[Realized]) -> Holding:
    return Holding(
        avg_days_win=_weighted_days([r for r in realized if r.realized > 0]),
        avg_days_loss=_weighted_days([r for r in realized if r.realized < 0]),
        avg_days=_weighted_days(realized),
    )


def _disposition(ledger: LedgerResult, prices: PriceStore) -> DispositionMetrics:
    """Odean (1998): count positions, not shares, on each day with at least one sell."""
    sold: dict[date, dict[str, list[Realized]]] = defaultdict(lambda: defaultdict(list))
    for r in ledger.realized:
        sold[r.date][r.symbol].append(r)
    rg = rl = pg = pl = 0
    for d in sorted(sold):
        for sym, pos in ledger.start[d].items():
            if sym in sold[d]:
                net = sum(r.qty * (r.sell_price - r.avg_cost) for r in sold[d][sym])
                rg += net > 0
                rl += net < 0
            else:
                bar, cost = prices.bar(sym, d), float(pos.avg_cost)
                pg += bar.low > cost
                pl += bar.high < cost
    pgr, plr = _ratio(rg, rg + pg), _ratio(rl, rl + pl)
    return DispositionMetrics(pgr=pgr, plr=plr, de=pgr - plr, n_sell_days=len(sold),
                              n_sells=len(ledger.realized))


def _chasing(trades: list[PricedTrade], prices: PriceStore, cfg: Thresholds) -> ChasingMetrics:
    buys = [t for t in trades if t.side == Side.BUY]
    closes: dict[str, dict] = {}
    chased = 0
    for t in buys:
        series = closes.setdefault(t.symbol, prices.close_series(t.symbol).to_dict())
        try:
            recent = prices.prev_session(t.trade_date, 1)
            base = prices.prev_session(t.trade_date, 1 + cfg.chasing.lookback_sessions)
        except NotTradingDayError:
            continue  # not enough history: cannot be classified as chasing
        chased += series[recent] / series[base] - 1 >= cfg.chasing.rise
    return ChasingMetrics(ratio=_ratio(chased, len(buys)), n_buys=len(buys))


def _herding(trades: list[PricedTrade], pf: PortfolioResult, prices: PriceStore,
             cfg: Thresholds) -> HerdingMetrics:
    index = prices.close_series(INDEX_SYMBOL).to_dict()
    window = [d for d in prices.trading_days if pf.first_date <= d <= pf.last_date]
    in_window = set(window)
    drops: set[date] = set()
    for d in window:
        try:
            prev = prices.prev_session(d, 1)
        except NotTradingDayError:
            continue
        if index[d] / index[prev] - 1 <= cfg.herding.index_drop:
            drops.add(d)
            nxt = prices.next_session(d)
            if cfg.herding.include_next_session and nxt is not None and nxt in in_window:
                drops.add(nxt)
    sells = [t for t in trades if t.side == Side.SELL]
    if not sells or not drops:
        return HerdingMetrics(lift=0.0, n_sells=len(sells))
    on_drop = sum(t.trade_date in drops for t in sells)
    return HerdingMetrics(lift=(on_drop / len(sells)) / (len(drops) / len(window)), n_sells=len(sells))


def _performance(trades: list[PricedTrade], ledger: LedgerResult, pf: PortfolioResult) -> Performance:
    return Performance(
        twr=pf.twr, benchmark_return=pf.benchmark_return, excess=pf.excess, vol_annual=pf.vol_annual, benchmark_vol=pf.benchmark_vol,
        realized_pnl=float(sum(r.realized for r in ledger.realized)), unrealized_pnl=pf.unrealized_pnl,
        fees_total=float(sum(t.fee for t in trades)), tax_total=float(sum(t.tax for t in trades)),
    )


# ------------------------------------------------------------------ entry point
def compute_metrics(trades: list[PricedTrade], prices: PriceStore, profile: RiskProfile,
                    cfg: Thresholds) -> Metrics:
    ledger = build_ledger(trades, prices)
    pf = compute_portfolio(trades, ledger, prices)
    start, end = pf.first_date, pf.last_date
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    return Metrics(
        formula_version=cfg.formula_version,
        period=Period(start=start, end=end, months=months),
        profile=ProfileInfo(tier=profile.tier, level=profile.level),
        metrics=MetricValues(
            concentration=_concentration(pf),
            activity=_activity(trades, pf, months),
            holding=_holding(ledger.realized),
            disposition=_disposition(ledger, prices),
            chasing=_chasing(trades, prices, cfg),
            herding=_herding(trades, pf, prices, cfg),
            performance=_performance(trades, ledger, pf),
        ),
    )
