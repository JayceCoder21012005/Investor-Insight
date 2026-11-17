# 09 — Article recommendations

## Goal
Suggest 3 learning articles matching the user's flags and experience level.

## Files
`app/ai/recommend.py`, `content/articles/*.md`, `tests/test_recommend.py`

## Content
20–30 short Vietnamese markdown articles (300–600 words), written by the team, not copied from the web. Frontmatter:
```yaml
---
id: disposition-101
title: "Vì sao ta thường chốt lời sớm và giữ lỗ lâu?"
tags: [disposition]          # flag ids from 05
level: beginner              # beginner | intermediate | experienced
---
```
Minimum coverage: 2 articles per flag id (overtrading, concentration, disposition, chasing, herding, risk_mismatch, overconfidence) + 4 general (diversification, risk tolerance, fees and tax, reading a portfolio report).

## recommend(flags, level) -> list[Article]
- score = 2 × |article.tags ∩ fired flag ids| + (1 if article.level == level else 0)
- sort by score desc, then id; return top 3; no flags → general articles for the level.
- Load articles once at startup.

## Acceptance
- Flags [disposition], level beginner → first result tagged disposition and beginner.
- No flags → 3 general articles.

## Upgrade (only if time remains)
Embedding search over article text, keeping the same function signature.
