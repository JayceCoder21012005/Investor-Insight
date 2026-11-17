"""Settings (env) and Thresholds (thresholds.yaml). Invalid config -> app refuses to start."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas import Model

DEFAULT_THRESHOLDS = Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    database_url_direct: str = ""
    test_database_url: str = ""
    # LLM: pick a provider with LLM_PROVIDER (gemini | anthropic), or leave it empty and the one with a key is used.
    gemini_api_key: str = ""
    llm_api_key: str = ""  # Anthropic key
    llm_provider: str = ""
    llm_model: str = ""  # empty = the provider's default
    # Gemini only: models tried in order when the previous one is out of quota. None = default chain, "" = none.
    llm_fallback_models: str | None = None
    cors_origin: str = "http://localhost:3000"
    thresholds_path: Path = DEFAULT_THRESHOLDS
    prices_dir: Path = Path(__file__).resolve().parent.parent / "data" / "prices"
    articles_dir: Path = Path(__file__).resolve().parent.parent / "content" / "articles"
    personas_dir: Path = Path(__file__).resolve().parent.parent / "data" / "personas"

    @property
    def direct_database_url(self) -> str:
        """Neon's pooled and direct strings differ only by "-pooler" in the host; migrations need the direct one."""
        if self.database_url_direct:
            return self.database_url_direct
        return re.sub(r"(@ep-[^.@/]*)-pooler\.", lambda m: m.group(1) + ".", self.database_url)


# ---- thresholds.yaml, field by field ----
class MinSample(Model):
    sells: int
    buys: int


class ConcentrationCfg(Model):
    hhi_warn: float
    top_symbol_warn: float


class TurnoverCfg(Model):
    monthly_warn: float
    spike_vs_3m: float
    spike_baseline_months: int
    spike_min_value: float


class DispositionCfg(Model):
    de_warn: float


class ChasingCfg(Model):
    lookback_sessions: int
    rise: float
    ratio_warn: float


class HerdingCfg(Model):
    index_drop: float
    include_next_session: bool
    lift_warn: float


class InvestorTypeCfg(Model):
    long_hold_days: float
    long_hold_max_trades_per_month: float


class TierCfg(Model):
    score: tuple[int, int]
    hhi_max: float
    vol_ratio_max: float  # portfolio volatility allowed, as a multiple of VN-Index volatility


class RiskTiersCfg(Model):
    conservative: TierCfg
    balanced: TierCfg
    growth: TierCfg


class FeesCfg(Model):
    broker_tiers: list[tuple[float, float]]
    sell_tax: float


class GuardrailCfg(Model):
    rel_tol: float
    abs_tol: float
    max_retries: int
    advice_patterns: list[str]


class Thresholds(Model):
    formula_version: str
    min_sample: MinSample
    concentration: ConcentrationCfg
    turnover: TurnoverCfg
    disposition: DispositionCfg
    chasing: ChasingCfg
    herding: HerdingCfg
    investor_type: InvestorTypeCfg
    risk_tiers: RiskTiersCfg
    fees: FeesCfg
    guardrail: GuardrailCfg


def load_thresholds(path: Path = DEFAULT_THRESHOLDS) -> Thresholds:
    return Thresholds.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
