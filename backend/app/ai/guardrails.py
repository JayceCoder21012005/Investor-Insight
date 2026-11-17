"""Check AI output before it reaches a user. Four checks, in order:

1. schema   - parse into ReportContent
2. numbers  - every number in the text must come from the metrics it cites
3. advice   - no buy/sell/hold advice, no price predictions
4. coverage - exactly one insight per fired flag
"""
from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import ValidationError

from app.config import Thresholds
from app.schemas import Metrics, ReportContent, Violation

# ------------------------------------------------------------------ number parsing
_UNITS = {"%": 1.0, "triệu": 1e6, "tỷ": 1e9, "nghìn": 1e3, "ngàn": 1e3}
_NUMBER = re.compile(
    r"(?<!\w)"
    r"(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?!\d)"
    # "tỷ" is the billion unit, except as the first syllable of tỷ lệ / tỷ trọng / tỷ suất / tỷ giá
    r"(?:\s*(?P<unit>%|triệu|tỷ(?!\s*(?:lệ|trọng|suất|giá)(?!\w))|nghìn|ngàn)(?!\w))?",
    re.IGNORECASE,
)
_DATES = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}")


@dataclass(frozen=True)
class NumberToken:
    text: str
    candidates: list[float]  # more than one when "1.234" could be 1234 or 1.234


def parse_numbers(text: str) -> list[NumberToken]:
    out: list[NumberToken] = []
    for m in _NUMBER.finditer(text):
        raw, unit = m.group("num"), (m.group("unit") or "").lower()
        mult = _UNITS.get(unit, 1.0)
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
            thousands = float(raw.replace(".", "").replace(",", "."))
            values = [thousands]
            if "," not in raw and raw.count(".") == 1:  # "1.234" may be an English decimal
                values.append(float(raw))
        else:
            values = [float(raw.replace(",", "."))]
        out.append(NumberToken(m.group(0).strip(), [v * mult for v in values]))
    return out


def extract_numbers(text: str, ignore: Iterable[str]) -> list[NumberToken]:
    """Numbers worth checking: full dates and any explicitly ignored strings are not metric claims."""
    cleaned = _DATES.sub(" ", text)
    for s in ignore:
        cleaned = cleaned.replace(s, " ")
    return parse_numbers(cleaned)


def _forms(v: float) -> set[float]:
    out: set[float] = set()
    for base in (v, abs(v)):
        for scaled in (base, base * 100):
            out.add(scaled)
            out.update(round(scaled, d) for d in (0, 1, 2))
        out.update((base / 1e6, base / 1e9))
    return out


def number_allowed(x: float, allowed: Iterable[float], cfg: Thresholds) -> bool:
    g = cfg.guardrail
    for v in allowed:
        for a in _forms(v):
            if abs(x - a) <= max(g.rel_tol * abs(a), g.abs_tol):
                return True
    return False


# ------------------------------------------------------------------ metric lookup
def _flatten(node, path: str, out: dict[str, float | None]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _flatten(v, f"{path}.{k}" if path else k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _flatten(v, f"{path}.{i}", out)
    elif isinstance(node, bool | str):
        return
    elif node is None:
        out[path] = None
    else:
        out[path] = float(node)


def flatten_metrics(m: Metrics) -> dict[str, float | None]:
    flat: dict[str, float | None] = {}
    _flatten(m.metrics.model_dump(), "", flat)
    flat["period.months"] = float(m.period.months)
    return flat


def _values_for(flat: dict[str, float | None], key: str) -> list[float] | None:
    """Numeric values under `key` (a leaf or a group); None when the key does not exist at all."""
    hits = [(p, v) for p, v in flat.items() if p == key or p.startswith(key + ".")]
    if not hits:
        return None
    return [v for _, v in hits if v is not None]


# ------------------------------------------------------------------ advice
_TRADE_VERBS = re.compile(r"\b(mua|bán|nắm giữ|giữ|chốt lời|cắt lỗ|gom|xả|bắt đáy)\b", re.IGNORECASE)
_TICKER = re.compile(r"\b[A-Z0-9]{3,10}\b")
_NOT_A_TICKER = {"VND"}  # also the currency code; "triệu VND" must not look like a stock mention


def _ticker_with_verb(text: str, symbols: frozenset[str]) -> bool:
    tickers = symbols - _NOT_A_TICKER
    for sentence in re.split(r"[.!?\n]+", text):
        if _TRADE_VERBS.search(sentence) and tickers & set(_TICKER.findall(sentence)):
            return True
    return False


# ------------------------------------------------------------------ main entry
def _scope(flag_id: str) -> str:
    return f"insight:{flag_id}"


def check(raw: dict | str, metrics: Metrics, cfg: Thresholds,
          symbols: frozenset[str] = frozenset()) -> tuple[ReportContent | None, list[Violation]]:
    # 1. schema
    try:
        content = (ReportContent.model_validate_json(raw) if isinstance(raw, str)
                   else ReportContent.model_validate(raw))
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        return None, [Violation(code="schema", scope="report", detail=str(e)[:300])]

    violations: list[Violation] = []
    flat = flatten_metrics(metrics)
    # The analysis period itself may be written out in prose ("từ tháng 1 năm 2026"): month count and the
    # day/month/year parts of its two end dates are facts about the data, not metric claims.
    p = metrics.period
    months = [flat["period.months"]]
    # Dates are matched exactly: a 1% tolerance on 2026 would also accept 2025.
    exact = {float(x) for d in (p.start, p.end) for x in (d.day, d.month, d.year)} | {flat["period.months"]}
    all_values = [v for v in flat.values() if v is not None]
    ignore = {str(metrics.period.start), str(metrics.period.end)}

    # evidence keys must exist
    insight_values: dict[int, list[float]] = {}
    for i, ins in enumerate(content.insights):
        vals = list(months)
        for key in ins.evidence_keys:
            found = _values_for(flat, key)
            if found is None:
                violations.append(Violation(code="evidence_key", scope=_scope(ins.flag_id.value),
                                            detail=f"khóa '{key}' không tồn tại trong chỉ số"))
            else:
                vals += found
        insight_values[i] = vals

    # 4. coverage (checked early so scopes are complete; order in the output is not significant)
    expected = [f.id.value for f in metrics.flags]
    seen = Counter(i.flag_id.value for i in content.insights)
    for fid in expected:
        if seen[fid] != 1:
            violations.append(Violation(code="coverage", scope=_scope(fid),
                                        detail=f"cần đúng 1 insight cho '{fid}', có {seen[fid]}"))
    for fid in seen:
        if fid not in expected:
            violations.append(Violation(code="coverage", scope=_scope(fid),
                                        detail=f"'{fid}' không phải cờ đang bật"))

    # 2. numbers
    def uncited_keys(candidates: list[float], limit: int = 3) -> list[str]:
        """Metrics a rejected number actually matches: the fix is then to cite one, not to drop the number.
        Named metrics come before items of a series (activity.monthly_turnover.3.value)."""
        hits = [k for k, v in flat.items()
                if v is not None and any(number_allowed(c, [v], cfg) for c in candidates)]
        hits.sort(key=lambda k: any(part.isdigit() for part in k.split(".")))
        return hits[:limit]

    def check_numbers(text: str, scope: str, allowed: list[float]) -> None:
        for tok in extract_numbers(text, ignore):
            if not any(c in exact or number_allowed(c, allowed, cfg) for c in tok.candidates):
                detail = f"số '{tok.text}' không có trong số liệu được dẫn"
                keys = uncited_keys(tok.candidates) if scope.startswith("insight:") else []
                if keys:
                    names = ", ".join(f"'{k}'" for k in keys)
                    detail += f"; số này khớp chỉ số {names}: nếu đúng ý, thêm khóa đó vào evidence_keys của insight này"
                violations.append(Violation(code="number_not_found", scope=scope, detail=detail))

    check_numbers(content.summary, "summary", all_values)
    for i, ins in enumerate(content.insights):
        for text in (ins.observation, ins.title, ins.self_check_question):
            check_numbers(text, _scope(ins.flag_id.value), insight_values[i])
    for s in content.strengths:
        check_numbers(s, "strengths", all_values)
    check_numbers(content.limitations, "limitations", all_values)

    # 3. advice
    patterns = [re.compile(p, re.IGNORECASE) for p in cfg.guardrail.advice_patterns]
    fields: list[tuple[str, str]] = [("summary", content.summary), ("limitations", content.limitations)]
    fields += [("strengths", s) for s in content.strengths]
    for ins in content.insights:
        fields += [(_scope(ins.flag_id.value), t) for t in (ins.observation, ins.title, ins.self_check_question)]
    for scope, text in fields:
        hit = next((p.pattern for p in patterns if p.search(text)), None)
        # The ticker+verb rule applies to prose that describes behavior (summary, insights).
        in_prose = scope == "summary" or scope.startswith("insight:")
        if hit is None and in_prose and _ticker_with_verb(text, symbols):
            hit = "ticker + động từ mua/bán"
        if hit is not None:
            violations.append(Violation(code="advice", scope=scope, detail=f"có dấu hiệu khuyến nghị: {hit}"))

    return content, violations
