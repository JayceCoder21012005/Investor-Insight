"""Deterministic Vietnamese text for every flag, used when the LLM output cannot be trusted.

Every sentence is built only from metric values, so templates pass the same guardrails as LLM text.
"""
from __future__ import annotations

from app.ai.guardrails import flatten_metrics
from app.schemas import Flag, FlagId, Insight, Metrics, ReportContent

LIMITATIONS = (
    "Dữ liệu do bạn cung cấp hoặc là dữ liệu mô phỏng, và các chỉ số chỉ phản ánh số liệu giao dịch, "
    "không đọc được ý định hay hoàn cảnh của bạn. Nội dung chỉ để tự nhìn lại, không phải khuyến nghị đầu tư."
)

FLAG_NAME = {
    FlagId.overtrading: "giao dịch quá thường xuyên",
    FlagId.concentration: "tập trung danh mục",
    FlagId.disposition: "chốt lời sớm, giữ lỗ lâu",
    FlagId.chasing: "mua đuổi giá tăng",
    FlagId.herding: "bán theo thị trường chung",
    FlagId.risk_mismatch: "lệch khẩu vị rủi ro",
    FlagId.overconfidence: "giao dịch nhiều nhưng kém thị trường",
    FlagId.insufficient_data: "chưa đủ dữ liệu",
}
TIER_NAME = {"conservative": "thận trọng", "balanced": "cân bằng", "growth": "tăng trưởng"}


# ---- number formatting in Vietnamese style (comma decimal)
def _vi(s: str) -> str:
    return s.replace(".", ",")


def pct(x: float, d: int = 0) -> str:
    return _vi(f"{x * 100:.{d}f}%")


def num(x: float, d: int = 2) -> str:
    return _vi(f"{x:.{d}f}")


def _title(flag: FlagId) -> str:
    name = FLAG_NAME[flag]
    return name[0].upper() + name[1:]


# ---- per-flag text: (observation, self-check question)
def _overtrading(m: Metrics) -> tuple[str, str]:
    a = m.metrics.activity
    return (f"Vòng quay danh mục trung bình là {pct(a.avg_turnover)} mỗi tháng, với khoảng "
            f"{num(a.trades_per_month, 1)} lệnh mỗi tháng. Mức này cao hơn nhiều nhà đầu tư giao dịch ít, "
            "là dấu hiệu đáng để xem lại tần suất giao dịch của chính bạn.",
            "Mỗi lệnh gần đây của bạn có gắn với một lý do đầu tư rõ ràng, hay chủ yếu là phản ứng với biến động giá?")


def _concentration(m: Metrics) -> tuple[str, str]:
    c = m.metrics.concentration
    return (f"Chỉ số tập trung HHI của danh mục là {num(c.hhi)}, trong đó mã lớn nhất ({c.top_symbol}) chiếm "
            f"{pct(c.top_symbol_weight)} giá trị danh mục. Danh mục càng tập trung thì kết quả càng phụ thuộc vào ít mã.",
            "Bạn có chủ ý để một mã chiếm tỷ trọng lớn như vậy, và bạn chấp nhận được mức biến động đi kèm không?")


def _disposition(m: Metrics) -> tuple[str, str]:
    d, h = m.metrics.disposition, m.metrics.holding
    text = (f"Tỷ lệ chốt lời (PGR) là {pct(d.pgr)}, trong khi tỷ lệ cắt lỗ (PLR) là {pct(d.plr)}. "
            "Chốt lời thường xuyên hơn cắt lỗ là dấu hiệu của xu hướng chốt lời sớm và giữ mã đang lỗ.")
    if h.avg_days_win is not None and h.avg_days_loss is not None:
        text += (f" Thời gian nắm giữ trung bình của lệnh lãi là {h.avg_days_win:.0f} ngày, "
                 f"của lệnh lỗ là {h.avg_days_loss:.0f} ngày.")
    return text, "Khi một mã đang lỗ, bạn dựa vào tiêu chí nào để quyết định tiếp tục giữ, và tiêu chí đó có giống khi mã đang lãi không?"


def _chasing(m: Metrics) -> tuple[str, str]:
    c = m.metrics.chasing
    return (f"{pct(c.ratio)} trong số {c.n_buys} lệnh mua diễn ra sau khi mã đã tăng mạnh trong vài phiên liền trước. "
            "Đây là dấu hiệu của xu hướng mua theo đà tăng.",
            "Trước khi mua một mã vừa tăng mạnh, bạn có so sánh mức giá hiện tại với kế hoạch ban đầu của mình không?")


def _herding(m: Metrics) -> tuple[str, str]:
    h = m.metrics.herding
    return (f"Số lệnh bán rơi vào phiên VN-Index giảm mạnh (hoặc phiên liền sau) cao gấp {num(h.lift, 1)} lần so với "
            f"mức ngẫu nhiên, trên tổng {h.n_sells} lệnh bán. Đây là dấu hiệu bán theo biến động chung của thị trường.",
            "Khi thị trường giảm mạnh, quyết định bán của bạn đến từ đánh giá riêng từng mã hay từ tâm lý chung?")


def _risk_mismatch(m: Metrics) -> tuple[str, str]:
    c, p = m.metrics.concentration, m.metrics.performance
    return (f"Chỉ số tập trung HHI là {num(c.hhi)} và độ biến động lợi suất hằng năm là {pct(p.vol_annual)}, "
            f"so với {pct(p.benchmark_vol)} của VN-Index trong cùng thời gian. "
            f"Ít nhất một trong hai chỉ số này vượt khoảng thường phù hợp với khẩu vị {TIER_NAME[m.profile.tier.value]} "
            "mà bạn đã khai báo.",
            "Mức biến động này có khớp với mức lỗ tối đa bạn nói là chấp nhận được khi trả lời bảng hỏi không?")


def _overconfidence(m: Metrics) -> tuple[str, str]:
    a, p = m.metrics.activity, m.metrics.performance
    return (f"Vòng quay danh mục trung bình là {pct(a.avg_turnover)} mỗi tháng nhưng lợi suất thấp hơn VN-Index "
            f"{pct(abs(p.excess), 1)} trong cùng kỳ. Giao dịch nhiều mà không vượt thị trường là dấu hiệu nên xem lại "
            "mức tự tin vào các quyết định ngắn hạn.".replace("nên xem lại", "đáng để xem lại"),
            "Những lệnh giao dịch thêm gần đây có thực sự cải thiện kết quả của bạn so với việc giữ nguyên danh mục không?")


_INSUFFICIENT_PHRASES = {
    "disposition.n_sells": ("xu hướng chốt lời và cắt lỗ", "lệnh bán"),
    "chasing.n_buys": ("xu hướng mua đuổi", "lệnh mua"),
    "herding.n_sells": ("xu hướng bán theo thị trường", "lệnh bán"),
}


def _insufficient(m: Metrics, flag: Flag) -> tuple[str, str]:
    flat = flatten_metrics(m)
    parts = []
    for key in flag.evidence_keys:
        label, unit = _INSUFFICIENT_PHRASES.get(key, (key, "lệnh"))
        count = flat.get(key)
        parts.append(f"{label} (hiện có {int(count) if count is not None else 0} {unit})")
    return ("Số lệnh hiện có chưa đủ để đánh giá: " + "; ".join(parts) +
            ". Báo cáo này không đưa ra kết luận về các khuynh hướng đó.",
            "Bạn có thể bổ sung thêm lịch sử giao dịch để các chỉ số này đáng tin cậy hơn không?")


_BUILDERS = {
    FlagId.overtrading: _overtrading, FlagId.concentration: _concentration, FlagId.disposition: _disposition,
    FlagId.chasing: _chasing, FlagId.herding: _herding, FlagId.risk_mismatch: _risk_mismatch,
    FlagId.overconfidence: _overconfidence,
}


def insight_for(flag: Flag, m: Metrics) -> Insight:
    if flag.id == FlagId.insufficient_data:
        observation, question = _insufficient(m, flag)
    else:
        observation, question = _BUILDERS[flag.id](m)
    return Insight(flag_id=flag.id, title=_title(flag.id), observation=observation,
                   evidence_keys=flag.evidence_keys, self_check_question=question)


def summary_for(m: Metrics) -> str:
    perf = m.metrics.performance
    head = (f"Trong {m.period.months} tháng, lợi suất danh mục là {pct(perf.twr, 1)} so với VN-Index "
            f"{pct(perf.benchmark_return, 1)}.")
    names = [FLAG_NAME[f.id] for f in m.flags]
    if names:
        return head + " Các dấu hiệu cần xem lại: " + ", ".join(names) + "."
    return head + " Chưa thấy dấu hiệu hành vi nổi bật trong dữ liệu này."


def strengths_for(m: Metrics) -> list[str]:
    out: list[str] = []
    ids = {f.id for f in m.flags}
    if m.metrics.performance.excess > 0:
        out.append(f"Lợi suất cao hơn VN-Index {pct(m.metrics.performance.excess, 1)} trong cùng kỳ.")
    if FlagId.concentration not in ids:
        out.append(f"Danh mục không quá tập trung (HHI {num(m.metrics.concentration.hhi)}).")
    return out[:2]


def template_content(m: Metrics) -> ReportContent:
    return ReportContent(summary=summary_for(m), insights=[insight_for(f, m) for f in m.flags],
                         strengths=strengths_for(m), limitations=LIMITATIONS)
