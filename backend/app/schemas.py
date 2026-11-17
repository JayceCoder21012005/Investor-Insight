"""Pydantic models: the contract between every layer (CSV -> core -> DB -> AI -> API).

Grouped by spec. Parse at the edge, trust inside.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


# ---- shared constrained types (00) ----
VND = Annotated[int, Field(ge=0)]
PositiveQty = Annotated[int, Field(gt=0)]
Ratio = Annotated[float, Field(ge=0, le=1)]
Symbol = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{3,10}$", to_upper=True)]


# ---- 01 prices ----
class PriceBar(Model):
    date: date
    open: Annotated[float, Field(gt=0)]
    high: Annotated[float, Field(gt=0)]
    low: Annotated[float, Field(gt=0)]
    close: Annotated[float, Field(gt=0)]
    volume: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def low_le_open_close_le_high(self) -> PriceBar:
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("require low <= open, close <= high")
        return self


class Bar(Model):
    open: float
    high: float
    low: float
    close: float


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Tier(StrEnum):
    conservative = "conservative"
    balanced = "balanced"
    growth = "growth"


class Level(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    experienced = "experienced"


# ---- 02 trades ----
_SIDE_ALIASES = {"buy": "BUY", "b": "BUY", "mua": "BUY", "sell": "SELL", "s": "SELL", "bán": "SELL", "ban": "SELL"}


class TradeRow(Model):
    row_no: Annotated[int, Field(ge=1)]
    trade_date: date
    symbol: Symbol
    side: Side
    quantity: PositiveQty
    price: Annotated[int, Field(gt=0)]
    fee: VND | None = None
    tax: VND | None = None

    @field_validator("symbol", mode="before")
    @classmethod
    def upper_symbol(cls, v):
        # StringConstraints checks the pattern before to_upper, so uppercase first.
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, v):
        if isinstance(v, str):
            return _SIDE_ALIASES.get(v.strip().lower(), v.strip().upper())
        return v

    @model_validator(mode="after")
    def buy_has_no_tax(self) -> TradeRow:
        if self.side == Side.BUY and self.tax:
            raise PydanticCustomError("buy_tax", "BUY must not carry tax")
        return self


class PricedTrade(TradeRow):
    """TradeRow with fee and tax filled in, so downstream code never sees None."""

    fee: VND
    tax: VND


class RowIssue(Model):
    row: int  # 0 = whole-file issue
    field: str
    message: str


class ValidationResult(Model):
    rows: list[TradeRow]
    errors: list[RowIssue]
    warnings: list[RowIssue]


# ---- 03 ledger / portfolio ----
class Position(Model):
    qty: int
    avg_cost: Decimal


class Realized(Model):
    symbol: str
    date: date
    qty: int
    sell_price: int
    avg_cost: Decimal
    realized: Decimal
    ret: float
    holding_days: float


class LedgerResult(Model):
    realized: list[Realized]
    start: dict[date, dict[str, Position]]  # positions at the open of each trading day
    end: dict[date, dict[str, Position]]  # positions after that day's trades


class DailyPoint(Model):
    date: date
    value: float
    flow: float
    ret: float | None


class RebasedPoint(Model):
    date: date
    portfolio: float
    benchmark: float


class PortfolioResult(Model):
    first_date: date
    last_date: date
    daily: list[DailyPoint]
    rebased: list[RebasedPoint]
    twr: float
    vol_annual: float
    benchmark_vol: float  # VN-Index volatility over the same sessions
    benchmark_return: float
    excess: float
    unrealized_pnl: float
    weights_symbol: dict[str, float]
    weights_sector: dict[str, float]


# ---- 04 metrics (+ 05 flags/risk) ----
class RiskProfile(Model):
    score: int
    tier: Tier
    level: Level


class ProfileInfo(Model):
    tier: Tier
    level: Level


class Period(Model):
    start: date
    end: date
    months: int


class Concentration(Model):
    hhi: float
    top_symbol: str | None
    top_symbol_weight: float
    top_sector: str | None
    top_sector_weight: float


class MonthlyTurnover(Model):
    month: str  # YYYY-MM
    value: float


class Activity(Model):
    monthly_turnover: list[MonthlyTurnover]
    avg_turnover: float
    trades_per_month: float


class Holding(Model):
    avg_days_win: float | None
    avg_days_loss: float | None
    avg_days: float | None  # all realized sells, quantity-weighted (used by investor_type)


class DispositionMetrics(Model):
    pgr: float
    plr: float
    de: float
    n_sell_days: int
    n_sells: int


class ChasingMetrics(Model):
    ratio: float
    n_buys: int


class HerdingMetrics(Model):
    lift: float
    n_sells: int


class Performance(Model):
    twr: float
    benchmark_return: float
    excess: float
    vol_annual: float
    benchmark_vol: float
    realized_pnl: float
    unrealized_pnl: float
    fees_total: float
    tax_total: float


class MetricValues(Model):
    concentration: Concentration
    activity: Activity
    holding: Holding
    disposition: DispositionMetrics
    chasing: ChasingMetrics
    herding: HerdingMetrics
    performance: Performance


class FlagId(StrEnum):
    overtrading = "overtrading"
    concentration = "concentration"
    disposition = "disposition"
    chasing = "chasing"
    herding = "herding"
    risk_mismatch = "risk_mismatch"
    overconfidence = "overconfidence"
    insufficient_data = "insufficient_data"


class Flag(Model):
    id: FlagId
    severity: str = "warn"
    evidence_keys: list[str]


class Metrics(Model):
    formula_version: str
    period: Period
    profile: ProfileInfo
    metrics: MetricValues
    flags: list[Flag] = Field(default_factory=list)
    investor_type: str | None = None


# ---- 08 AI report ----
MAX_SUMMARY_WORDS = 60


class Insight(Model):
    flag_id: FlagId
    title: Annotated[str, Field(max_length=120)]
    observation: str
    evidence_keys: Annotated[list[str], Field(min_length=1)]
    self_check_question: str


class ReportContent(Model):
    summary: Annotated[str, Field(max_length=600)]
    insights: list[Insight]
    strengths: list[str]
    limitations: str

    @field_validator("summary")
    @classmethod
    def summary_is_short(cls, v: str) -> str:
        if len(v.split()) > MAX_SUMMARY_WORDS:
            raise ValueError(f"summary longer than {MAX_SUMMARY_WORDS} words")
        return v


class Violation(Model):
    code: str  # schema | number_not_found | advice | coverage | evidence_key | llm_error
    scope: str  # summary | insight:<flag_id> | strengths | limitations | report
    detail: str


class ReportResult(Model):
    content: ReportContent
    attempts: int
    passed: bool
    violations: list[Violation]  # of the last attempt: why a template was used, if one was
    first_attempt_violations: list[Violation] = Field(default_factory=list)  # kept for evaluation
    latency_ms: int
    model: str


# ---- 07 API ----
class ProfileCreate(Model):
    answers: list[int]


class ProfileOut(Model):
    id: str
    tier: Tier
    level: Level


class ReportOut(Model):
    id: str
    created_at: str
    formula_version: str
    model: str
    attempts: int
    passed: bool
    violations: list[Violation]
    latency_ms: int
    content: ReportContent
    metrics: Metrics


class DemoItem(Model):
    persona_id: str
    title: str
    tier: Tier
    description: str


class PortfolioView(Model):
    """Series and weights behind the overview charts (the UI draws them, it never computes them)."""

    first_date: date
    last_date: date
    rebased: list[RebasedPoint]
    weights_symbol: dict[str, float]
    weights_sector: dict[str, float]
