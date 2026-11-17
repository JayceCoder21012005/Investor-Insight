from pathlib import Path

import pytest

from app.config import load_thresholds
from app.core.risk import score
from app.schemas import Level, Tier

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")


def test_all_ones_is_conservative_beginner():
    p = score([1, 1, 1, 1, 1], CFG)
    assert (p.score, p.tier, p.level) == (5, Tier.conservative, Level.beginner)


def test_all_fours_is_growth_experienced():
    p = score([4, 4, 4, 4, 4], CFG)
    assert (p.score, p.tier, p.level) == (20, Tier.growth, Level.experienced)


@pytest.mark.parametrize("answers,tier", [
    ([2, 2, 2, 2, 1], Tier.conservative),  # 9
    ([2, 2, 2, 2, 2], Tier.balanced),      # 10
    ([3, 3, 3, 3, 2], Tier.balanced),      # 14
    ([3, 3, 3, 3, 3], Tier.growth),        # 15
])
def test_tier_boundaries_come_from_thresholds(answers, tier):
    assert score(answers, CFG).tier == tier


@pytest.mark.parametrize("q2,level", [(1, Level.beginner), (2, Level.intermediate),
                                      (3, Level.experienced), (4, Level.experienced)])
def test_level_comes_from_question_two(q2, level):
    assert score([2, q2, 2, 2, 2], CFG).level == level


@pytest.mark.parametrize("bad", [[1, 1, 1, 1], [1, 1, 1, 1, 1, 1], [0, 1, 1, 1, 1], [1, 1, 1, 1, 5]])
def test_invalid_answers_raise(bad):
    with pytest.raises(ValueError):
        score(bad, CFG)
