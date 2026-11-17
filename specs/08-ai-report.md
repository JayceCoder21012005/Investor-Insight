# 08 — AI report and guardrails

## Goal
Generate a Vietnamese explanation of the metrics that cannot contain invented numbers or investment advice.

## Files
`app/ai/{llm,prompts,guardrails,templates,report}.py`, `tests/test_guardrails.py`, `tests/test_report.py` (fake LLM)

## llm.py
```python
class LLMClient(Protocol):
    def generate_json(self, system: str, user: str, schema: dict) -> dict: ...
```
One real implementation using structured/JSON-schema output; model from `LLM_MODEL`. Timeout 30 s. A `FakeLLM` for tests.

## Input
Only: `profile.tier`, `profile.level`, `investor_type`, `metrics`, `flags`. Never names, emails, account numbers.

## Output schema
Defined as pydantic models `Insight` and `ReportContent` (`summary: str = Field(max_length=600)`, `insights: list[Insight]`, `evidence_keys: list[str] = Field(min_length=1)`, `flag_id: FlagId`). Send `ReportContent.model_json_schema()` to the LLM; parse with `ReportContent.model_validate_json`. Shape:
```json
{"summary": "string, <= 60 words",
 "insights": [{"flag_id": "string", "title": "string", "observation": "string",
               "evidence_keys": ["string"], "self_check_question": "string"}],
 "strengths": ["string"],
 "limitations": "string"}
```

## System prompt rules (prompts.py)
- Explain only the provided metrics; one insight per flag in `flags`.
- Cite the metric keys used in `evidence_keys`; numbers only from those metrics.
- Describe behaviors as signals for self-reflection, not psychological diagnoses.
- Never recommend buying, selling, or holding any specific stock; never predict prices.
- Match vocabulary to `level`. Write in Vietnamese.
- `limitations`: mention data is user-provided/simulated and metrics cannot read intent.

## guardrails.py — run in order
1. Schema validation (pydantic). Fail → retry.
2. Number check: extract numbers from `summary` and each `observation`. Parse Vietnamese format (`1.234,5`), `%`, `triệu` (×1e6), `tỷ` (×1e9). Each number must equal some allowed value within `max(rel_tol×|v|, abs_tol)`. Allowed values = cited evidence values (summary: all metric values) in forms: raw, ×100, rounded to 0/1/2 decimals, /1e6, /1e9, plus `period.months`.
3. Advice filter: regexes from `guardrail.advice_patterns`; also fail if an observation mentions a ticker together with a buy/sell verb.
4. Coverage: every flag id has exactly one insight.

On fail of 1–4: retry up to `max_retries` with the violation list appended to the user prompt. Still failing → replace only failing insights with `templates.py` text; summary falls back to a template if it fails.

## templates.py
One deterministic Vietnamese template per flag id and for summary, filled from metrics, e.g. disposition: "Tỷ lệ chốt lời (PGR) là {pgr:.0%}, cao hơn tỷ lệ cắt lỗ (PLR) {plr:.0%}..."

## report.py
`build_report(metrics, flags, profile, llm, cfg) -> Report` storing `content, attempts, passed, violations, latency_ms, model`. `passed` = no template fallback used.

## Acceptance
- Observation with a number not in metrics → violation `number_not_found`. When the number matches a metric the insight did not cite, the violation detail names up to 3 such keys, and the retry prompt adds one fix hint per violation code (the check itself is unchanged).
- "Bạn nên bán FPT" → violation `advice`.
- FakeLLM returning bad output twice → report built from templates, `passed=false`.
