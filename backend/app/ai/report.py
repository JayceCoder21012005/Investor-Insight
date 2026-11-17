"""Generate -> check -> retry once with the violation list -> fall back to templates for what still fails."""
from __future__ import annotations

import time

from app.ai.guardrails import check
from app.ai.llm import LLMClient
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt, format_retry
from app.ai.templates import LIMITATIONS, insight_for, strengths_for, summary_for, template_content
from app.config import Thresholds
from app.schemas import Insight, Metrics, ReportContent, ReportResult, Violation


def _fallback(content: ReportContent | None, violations: list[Violation], m: Metrics) -> ReportContent:
    """Replace only the parts that failed; keep every part that passed."""
    if content is None:
        return template_content(m)
    bad = {v.scope for v in violations}
    flag_ids = [f.id for f in m.flags]

    insights: list[Insight] = []
    for flag in m.flags:
        mine = [i for i in content.insights if i.flag_id == flag.id]
        if f"insight:{flag.id.value}" in bad or len(mine) != 1:
            insights.append(insight_for(flag, m))
        else:
            insights.append(mine[0])
    assert [i.flag_id for i in insights] == flag_ids

    return ReportContent(
        summary=summary_for(m) if "summary" in bad else content.summary,
        insights=insights,
        strengths=strengths_for(m) if "strengths" in bad else content.strengths,
        limitations=LIMITATIONS if "limitations" in bad else content.limitations,
    )


def build_report(m: Metrics, llm: LLMClient, cfg: Thresholds,
                 symbols: frozenset[str] = frozenset()) -> ReportResult:
    started = time.perf_counter()
    schema = ReportContent.model_json_schema()
    user = build_user_prompt(m)

    content: ReportContent | None = None
    violations: list[Violation] = []
    first_attempt: list[Violation] = []
    attempts = 0
    for attempt in range(1 + cfg.guardrail.max_retries):
        attempts += 1
        prompt = user if attempt == 0 else user + format_retry(violations)
        try:
            raw = llm.generate_json(SYSTEM_PROMPT, prompt, schema)
        except Exception as e:  # timeout, refusal, API error: all handled the same way
            content, violations = None, [Violation(code="llm_error", scope="report", detail=str(e)[:300])]
            if attempt == 0:
                first_attempt = violations
            continue
        content, violations = check(raw, m, cfg, symbols)
        if attempt == 0:
            first_attempt = violations
        if not violations:
            break

    passed = not violations
    if not passed:
        content = _fallback(content, violations, m)
    assert content is not None
    return ReportResult(content=content, attempts=attempts, passed=passed, violations=violations,
                        first_attempt_violations=first_attempt,
                        latency_ms=int((time.perf_counter() - started) * 1000), model=llm.model)
