"""Risk questionnaire scoring: 5 answers, each 1-4, mapped to a tier by thresholds.yaml."""
from __future__ import annotations

from app.config import Thresholds
from app.schemas import Level, RiskProfile, Tier

N_QUESTIONS = 5
EXPERIENCE_QUESTION = 2  # 1-based: "Kinh nghiệm đầu tư chứng khoán"


def score(answers: list[int], cfg: Thresholds) -> RiskProfile:
    if len(answers) != N_QUESTIONS or any(not isinstance(a, int) or not 1 <= a <= 4 for a in answers):
        raise ValueError(f"need {N_QUESTIONS} answers, each an integer 1-4")
    total = sum(answers)
    tier = None
    for name in Tier:
        lo, hi = getattr(cfg.risk_tiers, name.value).score
        if lo <= total <= hi:
            tier = name
            break
    if tier is None:
        raise ValueError(f"score {total} is outside every tier range")
    exp = answers[EXPERIENCE_QUESTION - 1]
    level = Level.beginner if exp == 1 else Level.intermediate if exp == 2 else Level.experienced
    return RiskProfile(score=total, tier=tier, level=level)
