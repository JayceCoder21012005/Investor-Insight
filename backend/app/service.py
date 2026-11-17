"""Glue between the DB rows, the pure core and the AI layer. No HTTP here."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine

from app.ai.llm import LLMClient
from app.ai.recommend import Article
from app.config import Settings, Thresholds
from app.core.flags import annotate
from app.core.metrics import compute_metrics
from app.core.prices import PriceStore
from app.models import Profile, Trade
from app.schemas import Level, Metrics, PricedTrade, RiskProfile, Side, Tier


@dataclass
class AppState:
    settings: Settings
    cfg: Thresholds
    prices: PriceStore
    articles: list[Article]
    engine: Engine
    llm: LLMClient | None

    @property
    def symbols(self) -> frozenset[str]:
        return frozenset(self.prices.symbols)


def to_priced(rows: list[Trade]) -> list[PricedTrade]:
    return [PricedTrade(row_no=r.row_no, trade_date=r.trade_date, symbol=r.symbol, side=Side(r.side),
                        quantity=r.quantity, price=r.price, fee=r.fee, tax=r.tax) for r in rows]


def analyze(profile: Profile, trades: list[PricedTrade], state: AppState) -> Metrics:
    """Metrics with flags and investor type, from stored trades and the profile's declared risk."""
    risk = RiskProfile(score=profile.score, tier=Tier(profile.tier), level=Level(profile.level))
    return annotate(compute_metrics(trades, state.prices, risk, state.cfg), state.cfg)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
