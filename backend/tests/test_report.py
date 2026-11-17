import json
from pathlib import Path

import pytest

from app.ai.llm import FakeLLM, LLMError, to_output_schema
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt, metrics_payload
from app.ai.report import build_report
from app.ai.templates import template_content
from app.config import load_thresholds
from app.schemas import FlagId, ReportContent
from tests.helpers import mk_flagged

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")
SYMBOLS = frozenset({"FPT", "VCB", "HPG"})


def two_flag_metrics():
    return mk_flagged(
        disposition={"pgr": 0.4, "plr": 0.1, "de": 0.3, "n_sells": 30},
        chasing={"ratio": 0.5, "n_buys": 40},
    )


def good(m):
    return template_content(m).model_dump(mode="json")


def advice_in_first_insight(m):
    c = good(m)
    c["insights"][0]["observation"] = "Bạn nên bán FPT ngay."
    return c


def run(m, responses):
    llm = FakeLLM(responses)
    return build_report(m, llm, CFG, SYMBOLS), llm


def test_clean_first_attempt_passes():
    m = two_flag_metrics()
    res, llm = run(m, [good(m)])
    assert (res.attempts, res.passed, res.violations) == (1, True, [])
    assert len(llm.calls) == 1 and res.model == "fake-llm" and res.latency_ms >= 0
    assert {i.flag_id for i in res.content.insights} == {FlagId.disposition, FlagId.chasing}


def test_retry_gets_the_violation_list_and_can_recover():
    m = two_flag_metrics()
    res, llm = run(m, [advice_in_first_insight(m), good(m)])
    assert (res.attempts, res.passed) == (2, True)
    retry_prompt = llm.calls[1][1]
    assert "advice" in retry_prompt and "insight:disposition" in retry_prompt


def test_retry_prompt_says_how_to_fix_each_kind_of_violation():
    from app.ai.prompts import format_retry
    from app.schemas import Violation

    text = format_retry([Violation(code="number_not_found", scope="insight:x", detail="số '5%'"),
                         Violation(code="schema", scope="report", detail="summary longer than 60 words")])
    assert "evidence_keys" in text and "60 từ" in text
    assert format_retry([Violation(code="advice", scope="summary", detail="x")]).count("Cách sửa") == 1


def test_bad_output_twice_falls_back_to_templates_and_marks_not_passed():
    m = two_flag_metrics()
    res, _ = run(m, [advice_in_first_insight(m), advice_in_first_insight(m)])
    assert res.attempts == 2 and res.passed is False
    assert [v.code for v in res.violations] == ["advice"]
    assert "Bạn nên bán" not in res.content.model_dump_json()
    assert res.content == ReportContent.model_validate(template_content(m).model_dump())  # fully valid content


def test_only_failing_insights_are_replaced():
    m = two_flag_metrics()
    bad = advice_in_first_insight(m)
    kept = bad["insights"][1]["observation"]
    kept_flag = bad["insights"][1]["flag_id"]
    kept_text = f"Quan sát riêng: {kept}"
    bad["insights"][1]["observation"] = kept_text
    res, _ = run(m, [bad, bad])
    by_flag = {i.flag_id.value: i for i in res.content.insights}
    assert by_flag[kept_flag].observation == kept_text  # untouched
    other = next(i for i in res.content.insights if i.flag_id.value != kept_flag)
    assert "nên" not in other.observation and res.passed is False


def test_failing_summary_is_replaced_by_template_summary():
    m = two_flag_metrics()
    bad = good(m)
    bad["summary"] = "Bạn nên mua thêm cổ phiếu."
    res, _ = run(m, [bad, bad])
    assert "nên" not in res.content.summary and res.passed is False
    assert res.content.insights == ReportContent.model_validate(good(m)).insights


def test_unparseable_output_twice_uses_full_template_content():
    m = two_flag_metrics()
    res, _ = run(m, [{"nonsense": 1}, "not json"])
    assert res.passed is False and res.violations[0].code == "schema"
    assert len(res.content.insights) == 2


def test_llm_exception_is_retried_then_falls_back():
    m = two_flag_metrics()
    res, llm = run(m, [LLMError("timeout"), LLMError("timeout")])
    assert res.attempts == 2 and res.passed is False and res.violations[0].code == "llm_error"
    assert len(res.content.insights) == 2 and len(llm.calls) == 2


def test_llm_exception_then_good_output_passes():
    m = two_flag_metrics()
    res, _ = run(m, [LLMError("timeout"), good(m)])
    assert res.passed is True and res.attempts == 2


def test_missing_insight_is_filled_from_template():
    m = two_flag_metrics()
    partial = good(m)
    partial["insights"] = partial["insights"][:1]
    res, _ = run(m, [partial, partial])
    assert {i.flag_id for i in res.content.insights} == {FlagId.disposition, FlagId.chasing}
    assert res.passed is False


def test_max_retries_zero_means_a_single_call():
    cfg = CFG.model_copy(update={"guardrail": CFG.guardrail.model_copy(update={"max_retries": 0})})
    m = two_flag_metrics()
    llm = FakeLLM([advice_in_first_insight(m), good(m)])
    res = build_report(m, llm, cfg, SYMBOLS)
    assert res.attempts == 1 and len(llm.calls) == 1 and res.passed is False


def test_no_flags_report_has_summary_and_no_insights():
    m = mk_flagged()
    res, _ = run(m, [good(m)])
    assert res.passed and res.content.insights == []


# ---- what the model is allowed to see and be told
def test_llm_input_has_only_profile_type_metrics_and_flags():
    m = two_flag_metrics()
    payload = metrics_payload(m)
    assert set(payload) == {"profile", "investor_type", "period", "metrics", "flags"}
    assert set(payload["profile"]) == {"tier", "level"}


def test_payload_floats_are_rounded_to_four_decimals():
    m = mk_flagged(disposition={"pgr": 0.123456789, "de": 0.3, "n_sells": 30})
    assert metrics_payload(m)["metrics"]["disposition"]["pgr"] == 0.1235


def test_prompts_carry_the_rules_and_the_schema_contract():
    m = two_flag_metrics()
    user = build_user_prompt(m)
    assert json.loads(user[user.index("{"):])["flags"][0]["id"] == "disposition"
    for phrase in ("tiếng Việt", "không khuyến nghị", "evidence_keys", "chỉ số được cung cấp"):
        assert phrase.lower() in SYSTEM_PROMPT.lower()


def test_schema_sent_to_llm_is_the_report_schema():
    m = two_flag_metrics()
    _, llm = run(m, [good(m)])
    assert llm.calls[0][2] == ReportContent.model_json_schema()


def schema_keywords(node):
    """Keys used as JSON-schema keywords (property NAMES under "properties" are data, not keywords)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            if k == "properties":
                for sub in v.values():
                    yield from schema_keywords(sub)
            else:
                yield from schema_keywords(v)
    elif isinstance(node, list):
        for v in node:
            yield from schema_keywords(v)


@pytest.mark.parametrize("keyword", ["minLength", "maxLength", "minItems", "maxItems", "title", "default"])
def test_output_schema_strips_keywords_structured_outputs_may_reject(keyword):
    schema = to_output_schema(ReportContent.model_json_schema())
    assert keyword not in set(schema_keywords(schema))


def test_output_schema_keeps_property_named_title():
    schema = to_output_schema(ReportContent.model_json_schema())
    assert "title" in schema["$defs"]["Insight"]["properties"]


def test_output_schema_closes_every_object():
    schema = to_output_schema(ReportContent.model_json_schema())

    def objects(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                yield node
            for v in node.values():
                yield from objects(v)
        elif isinstance(node, list):
            for v in node:
                yield from objects(v)

    assert all(o.get("additionalProperties") is False for o in objects(schema))
