"""Shared test builders for Metrics objects."""
from datetime import date

from app.schemas import Metrics


def base() -> dict:
    """A quiet, well-sampled investor: no flag fires."""
    return {
        "formula_version": "0.1",
        "period": {"start": date(2026, 1, 5), "end": date(2026, 6, 30), "months": 6},
        "profile": {"tier": "balanced", "level": "intermediate"},
        "metrics": {
            "concentration": {"hhi": 0.10, "top_symbol": "AAA", "top_symbol_weight": 0.15,
                              "top_sector": "X", "top_sector_weight": 0.3},
            "activity": {"monthly_turnover": [{"month": f"2026-0{i}", "value": 0.2} for i in range(1, 7)],
                         "avg_turnover": 0.2, "trades_per_month": 5.0},
            "holding": {"avg_days_win": 20.0, "avg_days_loss": 25.0, "avg_days": 22.0},
            "disposition": {"pgr": 0.2, "plr": 0.2, "de": 0.0, "n_sell_days": 20, "n_sells": 30},
            "chasing": {"ratio": 0.1, "n_buys": 40},
            "herding": {"lift": 1.0, "n_sells": 30},
            "performance": {"twr": 0.1, "benchmark_return": 0.05, "excess": 0.05, "vol_annual": 0.15, "benchmark_vol": 0.15,
                            "realized_pnl": 1.0, "unrealized_pnl": 1.0, "fees_total": 1.0, "tax_total": 1.0},
        },
    }


def mk(**overrides) -> Metrics:
    """overrides like disposition={'de': 0.4} or tier='conservative'."""
    d = base()
    tier = overrides.pop("tier", None)
    if tier:
        d["profile"]["tier"] = tier
    months = overrides.pop("monthly", None)
    if months is not None:
        d["metrics"]["activity"]["monthly_turnover"] = [
            {"month": f"2026-{i + 1:02d}", "value": v} for i, v in enumerate(months)]
    for group, vals in overrides.items():
        d["metrics"][group].update(vals)
    return Metrics.model_validate(d)


def mk_flagged(**overrides) -> Metrics:
    """Like mk(), with flags and investor_type computed by the real rules."""
    from pathlib import Path

    from app.config import load_thresholds
    from app.core.flags import annotate

    cfg = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")
    return annotate(mk(**overrides), cfg)
