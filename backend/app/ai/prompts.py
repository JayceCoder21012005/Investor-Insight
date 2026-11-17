"""Prompts for the report. The model explains numbers it is given; it never computes or advises."""
from __future__ import annotations

import json

from app.schemas import Metrics, Violation

SYSTEM_PROMPT = """Bạn là trợ lý giải thích hành vi giao dịch của một nhà đầu tư cá nhân, dựa trên các chỉ số do hệ thống đã tính sẵn. Viết bằng tiếng Việt.

Quy tắc bắt buộc:
1. Chỉ giải thích các chỉ số được cung cấp. Viết đúng một insight cho mỗi cờ trong "flags", không thêm insight cho cờ không có.
2. Mọi con số trong "summary" và "observation" phải lấy từ các chỉ số được cung cấp (không tự tính, không làm tròn khác đi quá mức, không nhắc ngưỡng cảnh báo hay con số nào ngoài chỉ số được cung cấp). Trong "evidence_keys" của mỗi insight, liệt kê đúng các khóa chỉ số bạn đã dùng, ví dụ "disposition.pgr"; evidence_keys của cờ chỉ là gợi ý, dùng thêm chỉ số nào thì phải thêm khóa của chỉ số đó.
3. Mô tả hành vi như tín hiệu để người dùng tự xem lại, không phải chẩn đoán tâm lý hay đánh giá con người.
4. Không khuyến nghị mua, bán hay nắm giữ bất kỳ mã cổ phiếu nào; không dự báo giá; không dùng cấu trúc như "nên mua", "nên bán", "nên chốt lời", "giá mục tiêu". Không nhắc tên mã cổ phiếu cùng với động từ mua/bán. Câu hỏi tự kiểm tra cũng không được là lời khuyên.
5. Chọn từ ngữ theo mức kinh nghiệm: beginner dùng câu ngắn, giải thích thuật ngữ bằng lời thường; intermediate dùng thuật ngữ cơ bản; experienced có thể dùng thuật ngữ chuyên ngành.
6. "summary" tối đa 60 từ (2-3 câu ngắn, không liệt kê lại từng insight). Mỗi insight gồm: title, observation (1-3 câu nêu số liệu), self_check_question (một câu hỏi mở để người dùng tự suy ngẫm), flag_id và evidence_keys.
7. "strengths" là các điểm tích cực có số liệu hỗ trợ (có thể để trống). "limitations" phải nêu rằng dữ liệu do người dùng cung cấp hoặc mô phỏng và các chỉ số không đọc được ý định của người giao dịch.
8. Nếu cờ là insufficient_data, giải thích rằng số lệnh chưa đủ để kết luận về khuynh hướng liên quan, không suy đoán thêm.
"""


def round_floats(node, digits: int = 4):
    if isinstance(node, float):
        return round(node, digits)
    if isinstance(node, dict):
        return {k: round_floats(v, digits) for k, v in node.items()}
    if isinstance(node, list):
        return [round_floats(v, digits) for v in node]
    return node


def metrics_payload(m: Metrics) -> dict:
    """The only data the model sees: profile tier/level, investor type, period, metrics and flags.

    Floats are rounded to 4 decimals here, at serialization, never inside the calculation.
    """
    return round_floats({
        "profile": {"tier": m.profile.tier.value, "level": m.profile.level.value},
        "investor_type": m.investor_type,
        "period": m.period.model_dump(mode="json"),
        "metrics": m.metrics.model_dump(mode="json"),
        "flags": [f.model_dump(mode="json") for f in m.flags],
    })


def build_user_prompt(m: Metrics) -> str:
    payload = json.dumps(metrics_payload(m), ensure_ascii=False, indent=2)
    return ("Dưới đây là dữ liệu chỉ số của một nhà đầu tư. Hãy viết báo cáo theo đúng schema JSON yêu cầu.\n\n"
            + payload)


RETRY_HINTS = {
    "number_not_found": "Xóa con số đó; hoặc nếu nó là giá trị của một chỉ số được cung cấp, thêm khóa chỉ số đó "
                        "vào evidence_keys của insight. Không nhắc ngưỡng cảnh báo.",
    "schema": "Trả đúng schema JSON; \"summary\" tối đa 60 từ (khoảng 2-3 câu ngắn).",
    "advice": "Viết lại thành mô tả hành vi, bỏ mọi lời khuyên mua/bán/nắm giữ và dự báo giá.",
    "coverage": "Viết đúng một insight cho mỗi cờ trong \"flags\", không thêm cờ khác.",
    "evidence_key": "Chỉ dùng khóa có trong dữ liệu chỉ số, ví dụ \"disposition.pgr\".",
}


def format_retry(violations: list[Violation]) -> str:
    lines = [f"- [{v.code}] {v.scope}: {v.detail}" for v in violations]
    hints = [f"- Cách sửa [{code}]: {RETRY_HINTS[code]}"
             for code in dict.fromkeys(v.code for v in violations) if code in RETRY_HINTS]
    return ("\n\nLần trả lời trước vi phạm các quy tắc sau. Hãy sửa đúng các điểm này và giữ nguyên phần còn lại:\n"
            + "\n".join(lines + hints))
