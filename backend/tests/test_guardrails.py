from pathlib import Path

import pytest

from app.ai.guardrails import check, extract_numbers, number_allowed, parse_numbers
from app.config import load_thresholds
from tests.helpers import mk_flagged as mk

CFG = load_thresholds(Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml")
SYMBOLS = frozenset({"FPT", "VCB", "HPG"})


def insight(flag="disposition", observation="Bạn có xu hướng chốt lời sớm hơn cắt lỗ.", keys=("disposition.pgr",),
            title="Chốt lời sớm", question="Bạn có lý do rõ ràng khi chốt lời không?"):
    return {"flag_id": flag, "title": title, "observation": observation,
            "evidence_keys": list(keys), "self_check_question": question}


def content(summary="Danh mục có dấu hiệu cần xem lại.", insights=None, strengths=(), limitations="Dữ liệu mô phỏng."):
    return {"summary": summary, "insights": insights if insights is not None else [insight()],
            "strengths": list(strengths), "limitations": limitations}


def metrics():
    # disposition fires: de 0.4 with enough sells; pgr 0.35 plr 0.2
    return mk(disposition={"pgr": 0.35, "plr": 0.2, "de": 0.4, "n_sells": 30})


def run(raw, m=None):
    return check(raw, m or metrics(), CFG, SYMBOLS)


def codes(violations):
    return sorted(v.code for v in violations)


# ---------------------------------------------------------------- number parsing
@pytest.mark.parametrize("text,expected", [
    ("1.234,5", [1234.5]),
    ("0,35", [0.35]),
    ("35%", [35.0]),
    ("35,5%", [35.5]),
    ("2 triệu", [2_000_000.0]),
    ("1,2 tỷ", [1_200_000_000.0]),
    ("hơn 15 nghìn đồng", [15_000.0]),
])
def test_vietnamese_number_formats(text, expected):
    got = [c for token in parse_numbers(text) for c in token.candidates[:1]]
    assert got == pytest.approx(expected)


@pytest.mark.parametrize("text", ["0,4139 tỷ trọng", "0,35 tỷ lệ", "0,2 tỷ suất", "0,41 Tỷ trọng"])
def test_ty_as_the_start_of_a_word_is_not_the_billion_unit(text):
    # "tỷ trọng" (weight), "tỷ lệ" (ratio), "tỷ suất" (rate) follow a number in normal prose
    (tok,) = parse_numbers(text)
    assert tok.candidates[0] < 1


def test_ambiguous_dot_is_read_both_ways():
    (tok,) = parse_numbers("1.234")
    assert sorted(tok.candidates) == pytest.approx([1.234, 1234.0])


def test_numbers_inside_identifiers_and_iso_dates_are_ignored():
    assert extract_numbers("Hồ sơ P03 và VN30 từ 2026-01-05 đến 2026-06-30", set()) == []


def test_day_month_year_of_the_analysis_period_may_be_written_in_prose():
    # fixture period is 2026-01-05 .. 2026-06-30
    raw = content(summary="Từ tháng 1 năm 2026 đến tháng 6 năm 2026, hay từ 1/2026 đến 6/2026.")
    assert run(raw)[1] == []


def test_other_months_and_years_are_still_checked():
    _, v = run(content(summary="Trong năm 2025 và tháng 9."))
    assert [x.code for x in v] == ["number_not_found", "number_not_found"]


def test_period_dates_are_not_numbers_to_check():
    m = metrics()
    text = f"Giai đoạn từ {m.period.start} đến {m.period.end}"
    assert extract_numbers(text, {str(m.period.start), str(m.period.end)}) == []


# ---------------------------------------------------------------- number check
def test_valid_report_has_no_violations():
    parsed, v = run(content())
    assert v == [] and parsed is not None


@pytest.mark.parametrize("text", ["35%", "35,0%", "0,35", "35 %", "0.35"])
def test_cited_value_in_several_forms_is_accepted(text):
    _, v = run(content(insights=[insight(observation=f"Tỷ lệ chốt lời là {text}.")]))
    assert v == []


def test_number_not_in_metrics_is_violation():
    _, v = run(content(insights=[insight(observation="Tỷ lệ chốt lời là 77%.")]))
    assert codes(v) == ["number_not_found"] and v[0].scope == "insight:disposition"


def test_rounding_tolerance_accepts_rounded_value():
    m = mk(disposition={"pgr": 0.3849, "plr": 0.2, "de": 0.4, "n_sells": 30})
    _, v = run(content(insights=[insight(observation="Tỷ lệ chốt lời là 38%.")]), m)
    assert v == []
    _, v = run(content(insights=[insight(observation="Tỷ lệ chốt lời là 45%.")]), m)
    assert codes(v) == ["number_not_found"]


def test_negative_values_can_be_quoted_as_absolute_gap():
    m = mk(disposition={"de": 0.4, "n_sells": 30}, performance={"excess": -0.0523})
    raw = content(summary="Lợi suất thấp hơn VN-Index khoảng 5,2%.")
    assert run(raw, m)[1] == []


def test_insight_may_only_use_its_cited_metrics():
    # plr 20% exists in metrics, but this insight cites only pgr
    _, v = run(content(insights=[insight(observation="Tỷ lệ cắt lỗ là 20%.")]))
    assert codes(v) == ["number_not_found"]
    _, v = run(content(insights=[insight(observation="Tỷ lệ cắt lỗ là 20%.", keys=("disposition.pgr", "disposition.plr"))]))
    assert v == []


def test_an_uncited_real_metric_is_named_in_the_violation_so_the_retry_can_cite_it():
    _, v = run(content(insights=[insight(observation="Tỷ lệ cắt lỗ là 20%.")]))
    assert "disposition.plr" in v[0].detail and "evidence_keys" in v[0].detail
    _, v = run(content(insights=[insight(observation="Tỷ lệ chốt lời là 77%.")]))
    assert "không có trong số liệu" in v[0].detail and "evidence_keys" not in v[0].detail


def test_summary_may_use_any_metric_and_period_months():
    raw = content(summary="Trong 6 tháng, tỷ lệ cắt lỗ là 20% còn tỷ lệ chốt lời là 35%.")
    assert run(raw)[1] == []


def test_amounts_in_million_dong():
    m = mk(disposition={"de": 0.4, "n_sells": 30}, performance={"realized_pnl": 12_500_000.0})
    assert run(content(summary="Lãi đã thực hiện khoảng 12,5 triệu đồng."), m)[1] == []
    assert codes(run(content(summary="Lãi đã thực hiện khoảng 40 triệu đồng."), m)[1]) == ["number_not_found"]


def test_number_allowed_helper_uses_both_tolerances():
    assert number_allowed(0.049, [0.0], CFG)   # absolute tolerance 0.051
    assert not number_allowed(0.06, [0.0], CFG)
    assert number_allowed(1010.0, [1000.0], CFG)  # relative 1%
    assert not number_allowed(1020.0, [1000.0], CFG)


# ---------------------------------------------------------------- advice
@pytest.mark.parametrize("sentence", [
    "Bạn nên bán FPT ngay.",
    "Nên chốt lời khi có lãi.",
    "Chúng tôi khuyến nghị mua thêm.",
    "Giá sẽ tăng giá trong tuần tới.",
    "Giá mục tiêu là hợp lý.",
])
def test_advice_patterns_are_blocked(sentence):
    _, v = run(content(insights=[insight(observation=sentence)]))
    assert "advice" in codes(v)


def test_ticker_with_buy_sell_verb_is_blocked_even_without_pattern():
    _, v = run(content(insights=[insight(observation="Bạn đã mua FPT nhiều lần.")]))
    assert "advice" in codes(v)


def test_ticker_without_verb_is_allowed():
    m = mk(concentration={"hhi": 0.26, "top_symbol_weight": 0.45}, disposition={"n_sells": 30})
    raw = content(insights=[insight(flag="concentration", observation="FPT chiếm 45% danh mục.",
                                    keys=("concentration.top_symbol_weight",))])
    assert run(raw, m)[1] == []


def test_advice_in_summary_or_question_is_blocked():
    _, v = run(content(summary="Bạn nên mua thêm cổ phiếu."))
    assert [x.scope for x in v if x.code == "advice"] == ["summary"]
    _, v = run(content(insights=[insight(question="Bạn có nên bán không?")]))
    assert "advice" in codes(v)


# ---------------------------------------------------------------- coverage / schema / keys
def test_missing_insight_for_a_fired_flag_is_coverage_violation():
    _, v = run(content(insights=[]))
    assert codes(v) == ["coverage"] and v[0].scope == "insight:disposition"


def test_duplicate_insight_for_a_flag_is_coverage_violation():
    _, v = run(content(insights=[insight(), insight()]))
    assert "coverage" in codes(v)


def test_insight_for_a_flag_that_did_not_fire_is_coverage_violation():
    _, v = run(content(insights=[insight(), insight(flag="chasing", observation="Mua đuổi.", keys=("chasing.ratio",))]))
    assert [x.scope for x in v if x.code == "coverage"] == ["insight:chasing"]


def test_schema_violation_for_malformed_output():
    parsed, v = run({"summary": "x"})
    assert parsed is None and codes(v) == ["schema"]


def test_json_string_input_is_parsed():
    import json

    assert run(json.dumps(content()))[1] == []
    assert codes(run("not json")[1]) == ["schema"]


def test_summary_longer_than_60_words_is_schema_violation():
    parsed, v = run(content(summary=" ".join(["từ"] * 61)))
    assert parsed is None and codes(v) == ["schema"]


def test_unknown_evidence_key_is_violation():
    _, v = run(content(insights=[insight(keys=("disposition.nonexistent",))]))
    assert "evidence_key" in codes(v)


def test_no_flags_means_no_insights_allowed():
    m = mk()
    assert run(content(insights=[]), m)[1] == []
    assert "coverage" in codes(run(content(), m)[1])
