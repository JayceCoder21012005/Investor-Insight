import re
from collections import Counter
from pathlib import Path

import pytest

from app.ai.recommend import Article, load_articles, recommend
from app.config import load_thresholds
from app.schemas import Flag, FlagId, Level

ROOT = Path(__file__).resolve().parent.parent
CFG = load_thresholds(ROOT / "config" / "thresholds.yaml")
REAL = ROOT / "content" / "articles"
REAL_FLAGS = [f for f in FlagId if f != FlagId.insufficient_data]


def art(id, tags, level="beginner"):
    return Article(id=id, title=id, tags=tags, level=Level(level), body="x")


POOL = [
    art("disp-b", ["disposition"], "beginner"),
    art("disp-e", ["disposition"], "experienced"),
    art("chase-b", ["chasing"], "beginner"),
    art("over-i", ["overtrading"], "intermediate"),
    art("gen-b", ["general"], "beginner"),
    art("gen-i", ["general"], "intermediate"),
    art("gen-e", ["general"], "experienced"),
    art("gen-b2", ["general"], "beginner"),
]


def ids(articles):
    return [a.id for a in articles]


# ---------------------------------------------------------------- ranking (synthetic pool)
def test_flag_and_level_match_comes_first():
    out = recommend([FlagId.disposition], Level.beginner, POOL)
    assert out[0].id == "disp-b" and len(out) == 3


def test_flag_match_beats_level_match():
    out = recommend([FlagId.disposition], Level.beginner, POOL)
    assert "disp-e" in ids(out)[:2]  # score 2 beats general beginner score 1


def test_two_flags_rank_articles_covering_more_flags_higher():
    pool = POOL + [art("both", ["disposition", "chasing"], "intermediate")]
    assert recommend([FlagId.disposition, FlagId.chasing], Level.beginner, pool)[0].id == "both"


def test_ties_break_by_id():
    out = recommend([FlagId.disposition], Level.intermediate, POOL)
    assert ids(out) == ["disp-b", "disp-e", "gen-i"] or ids(out)[:2] == ["disp-b", "disp-e"]
    assert ids(out)[:2] == sorted(ids(out)[:2])


def test_no_flags_returns_three_general_articles_for_the_level():
    out = recommend([], Level.beginner, POOL)
    assert len(out) == 3 and all("general" in a.tags for a in out)
    assert ids(out)[:2] == ["gen-b", "gen-b2"]


def test_accepts_flag_objects_and_strings():
    flag = Flag(id=FlagId.chasing, evidence_keys=["chasing.ratio"])
    assert recommend([flag], Level.beginner, POOL)[0].id == "chase-b"
    assert recommend(["chasing"], Level.beginner, POOL)[0].id == "chase-b"


def test_never_returns_more_than_three_or_duplicates():
    out = recommend(list(FlagId), Level.beginner, POOL)
    assert len(out) <= 3 and len(set(ids(out))) == len(out)


def test_fewer_articles_than_three_is_fine():
    assert len(recommend([], Level.beginner, POOL[:1])) <= 1


# ---------------------------------------------------------------- the real content
@pytest.fixture(scope="module")
def articles():
    return load_articles(REAL)


def words(a: Article) -> int:
    return len(a.body.split())


def test_between_20_and_30_articles(articles):
    assert 20 <= len(articles) <= 30


def test_ids_are_unique_and_match_file_names(articles):
    assert len({a.id for a in articles}) == len(articles)
    assert {p.stem for p in REAL.glob("*.md")} == {a.id for a in articles}


def test_every_article_is_300_to_600_words(articles):
    bad = {a.id: words(a) for a in articles if not 300 <= words(a) <= 600}
    assert bad == {}


def test_tags_are_flag_ids_or_general(articles):
    allowed = {f.value for f in FlagId} | {"general"}
    for a in articles:
        assert a.tags and set(a.tags) <= allowed, a.id


def test_each_flag_has_at_least_two_articles(articles):
    count = Counter(t for a in articles for t in a.tags)
    for f in REAL_FLAGS:
        assert count[f.value] >= 2, f.value


def test_at_least_four_general_articles(articles):
    assert sum("general" in a.tags for a in articles) >= 4


def test_each_flag_has_a_beginner_article(articles):
    for f in REAL_FLAGS:
        assert any(f.value in a.tags and a.level == Level.beginner for a in articles), f.value


def test_articles_contain_no_investment_advice(articles):
    patterns = [re.compile(p, re.IGNORECASE) for p in CFG.guardrail.advice_patterns]
    for a in articles:
        for p in patterns:
            assert not p.search(a.body), f"{a.id}: {p.pattern}"


def test_every_flag_gets_three_recommendations_from_the_real_set(articles):
    for f in FlagId:
        out = recommend([f], Level.beginner, articles)
        assert len(out) == 3
        if f != FlagId.insufficient_data:
            assert f.value in out[0].tags


def test_no_flags_gives_general_articles_from_real_set(articles):
    out = recommend([], Level.experienced, articles)
    assert len(out) == 3 and all("general" in a.tags for a in out)
