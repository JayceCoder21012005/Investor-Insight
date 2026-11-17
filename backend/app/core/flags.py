"""Turn Metrics into behavior flags and a rule-based investor type."""
from __future__ import annotations

from app.config import Thresholds
from app.schemas import Flag, FlagId, Metrics


def _spike(values: list[float], factor: float, window: int, floor: float) -> bool:
    """Any month above factor x the mean of the previous `window` months, that also reaches `floor`.

    The baseline must be > 0, and the floor stops tiny absolute turnover from counting as a spike.
    """
    for i in range(window, len(values)):
        base = sum(values[i - window:i]) / window
        if base > 0 and values[i] > factor * base and values[i] >= floor:
            return True
    return False


def evaluate(metrics: Metrics, cfg: Thresholds) -> tuple[list[Flag], str]:
    m = metrics.metrics
    tier = getattr(cfg.risk_tiers, metrics.profile.tier.value)
    flags: list[Flag] = []
    lacking: list[str] = []

    def add(fid: FlagId, keys: list[str]) -> None:
        flags.append(Flag(id=fid, severity="warn", evidence_keys=keys))

    overtrading = (m.activity.avg_turnover > cfg.turnover.monthly_warn
                   or _spike([x.value for x in m.activity.monthly_turnover], cfg.turnover.spike_vs_3m,
                         cfg.turnover.spike_baseline_months,
                         cfg.turnover.spike_min_value))
    if overtrading:
        add(FlagId.overtrading, ["activity.avg_turnover", "activity.trades_per_month"])

    concentrated = (m.concentration.hhi > cfg.concentration.hhi_warn
                    or m.concentration.top_symbol_weight > cfg.concentration.top_symbol_warn)
    if concentrated:
        add(FlagId.concentration, ["concentration.hhi", "concentration.top_symbol_weight"])

    if m.disposition.n_sells < cfg.min_sample.sells:
        lacking.append("disposition.n_sells")
    elif m.disposition.de > cfg.disposition.de_warn:
        add(FlagId.disposition, ["disposition.pgr", "disposition.plr", "holding.avg_days_win",
                                 "holding.avg_days_loss"])

    if m.chasing.n_buys < cfg.min_sample.buys:
        lacking.append("chasing.n_buys")
    elif m.chasing.ratio > cfg.chasing.ratio_warn:
        add(FlagId.chasing, ["chasing.ratio", "chasing.n_buys"])

    if m.herding.n_sells < cfg.min_sample.sells:
        lacking.append("herding.n_sells")
    elif m.herding.lift >= cfg.herding.lift_warn:
        add(FlagId.herding, ["herding.lift", "herding.n_sells"])

    # Volatility is judged against the market over the same sessions, so a calm or a stormy year does
    # not by itself make every stock portfolio "too risky" or "fine" (formula 0.3).
    too_volatile = m.performance.vol_annual > tier.vol_ratio_max * m.performance.benchmark_vol
    if m.concentration.hhi > tier.hhi_max or too_volatile:
        add(FlagId.risk_mismatch, ["concentration.hhi", "performance.vol_annual", "performance.benchmark_vol"])

    if overtrading and m.performance.excess < 0:
        add(FlagId.overconfidence, ["activity.avg_turnover", "performance.excess"])

    if lacking:
        # One entry covering every tendency without enough sample; keys are the sample-size metrics.
        # Order them as the spec table lists tendencies (disposition, chasing, herding).
        order = ["disposition.n_sells", "chasing.n_buys", "herding.n_sells"]
        add(FlagId.insufficient_data, [k for k in order if k in lacking])

    return flags, _investor_type(metrics, overtrading, concentrated, cfg)


def _investor_type(metrics: Metrics, overtrading: bool, concentrated: bool, cfg: Thresholds) -> str:
    if overtrading:
        return "Giao dịch ngắn hạn"
    if concentrated:
        return "Tập trung"
    hold = metrics.metrics.holding.avg_days
    it = cfg.investor_type
    if (metrics.metrics.activity.trades_per_month < it.long_hold_max_trades_per_month
            and hold is not None and hold > it.long_hold_days):
        return "Nắm giữ dài hạn"
    return "Cân bằng"


def annotate(metrics: Metrics, cfg: Thresholds) -> Metrics:
    """Metrics with flags and investor_type filled in (what the API returns and the AI reads)."""
    flags, investor_type = evaluate(metrics, cfg)
    return metrics.model_copy(update={"flags": flags, "investor_type": investor_type})
