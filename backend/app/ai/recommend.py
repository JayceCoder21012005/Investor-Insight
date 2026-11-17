"""Pick 3 learning articles for the user's fired flags and experience level. Rule-based and deterministic."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

from app.schemas import Flag, FlagId, Level, Model

TOP_N = 3
GENERAL = "general"


class Article(Model):
    id: str
    title: str
    tags: list[str]
    level: Level
    body: str


def load_articles(directory: Path) -> list[Article]:
    """Markdown files with a YAML frontmatter block (id, title, tags, level). Load once at startup."""
    articles = []
    for path in sorted(Path(directory).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{path.name}: missing frontmatter")
        _, front, body = text.split("---", 2)
        meta = yaml.safe_load(front)
        articles.append(Article(body=body.strip(), **meta))
    return articles


def _flag_value(f: Flag | FlagId | str) -> str:
    if isinstance(f, Flag):
        return f.id.value
    return f.value if isinstance(f, FlagId) else str(f)


def recommend(flags: Iterable[Flag | FlagId | str], level: Level, articles: list[Article]) -> list[Article]:
    fired = {_flag_value(f) for f in flags}
    if not fired:
        pool = [a for a in articles if GENERAL in a.tags]
        scored = [(1 if a.level == level else 0, a) for a in pool]
    else:
        scored = [(2 * len(fired & set(a.tags)) + (1 if a.level == level else 0), a) for a in articles]
    ranked = sorted(scored, key=lambda s: (-s[0], s[1].id))
    return [a for score, a in ranked if score > 0 or not fired][:TOP_N]
