# Output templates

Pick the lightest form that fits. Headings in Vietnamese, since the reader is Vietnamese; keep file names, keys and code terms in English. Cut sections that have nothing to say instead of padding them with "N/A".

## A. Quick answer (a question about how something works or is defined)
2–6 sentences: the answer, then the source (`specs/04-metrics.md §Disposition`), then one line on any caveat or gap you noticed while checking. Offer the deeper analysis only if the request hints at a change.

## B. Requirement / change analysis (behavior will change)

```
## Phân tích: <tên ngắn>

**Nhu cầu**: <ai cần gì, để làm gì> — **Giải pháp đề xuất**: <nếu user đã nêu>
**Loại yêu cầu**: yêu cầu mới | đổi quy tắc | hành vi bất thường | câu hỏi

### Căn cứ
- `file §mục` — điều đã quy định, trích ngắn
- (những gì spec/kế hoạch KHÔNG nói)

### Phân tích
Quy tắc nghiệp vụ · dữ liệu đầu vào · trường hợp biên (có ít nhất 1 ví dụ tính tay) · phạm vi MVP · ràng buộc bất biến

### Ảnh hưởng
| Thành phần | Thay đổi |   (spec / module / test / persona / eval / UI / formula_version)

### Khoảng trống & mâu thuẫn
| # | Ở đâu | Vấn đề | Mức | Đề xuất |   (Mức: chặn | giả định được)

### Câu hỏi cần làm rõ  (≤ 4, xếp theo mức chặn)
1. <câu hỏi> — (a) <lựa chọn> → <hệ quả> **(đề xuất)** · (b) ... · (c) ...

### Giả định tạm thời (nếu chưa có trả lời)
- ...

### Đề xuất tiếp theo
- Acceptance criteria (mẫu bên dưới) / đoạn spec sửa / quyết định cần chốt / việc nên cắt nếu trễ
```

Acceptance criteria — project style, each with a number someone can compute by hand:
```
- Given <dữ liệu nhỏ>, when <hành động>, then <kết quả cụ thể, có số>.
  e.g. 10 BUYs, 3 after a ≥10% 5-session rise → chasing.ratio 0.3
```

## C. Vague problem ("báo cáo chưa thuyết phục", "dashboard khó hiểu", "user không tin số")
Don't jump to features. Frame the problem first:
1. **Who** has it and in which moment (end user on the dashboard, a reviewer reading the report, the team in eval)?
2. **Evidence**: what was observed, vs what is a guess. Ask for one concrete example.
3. **Hypotheses**: 2–4 plausible causes, each mapped to the part of the pipeline it lives in (data, metric definition, threshold, explanation text, UI).
4. **Cheapest discriminating check** for each hypothesis (a persona to run, a metric to print, a user to ask).
5. **Candidate responses**, in cut-order terms, with the invariant each respects.
Then ask the 1–3 questions whose answers pick between hypotheses.

## D. Conflict / gap report (the user asks "spec có khớp kế hoạch không", or you found conflicts)
```
| # | Chủ đề | Nguồn A (trích) | Nguồn B (trích) | Hệ quả nếu để nguyên | Đề xuất (theo thứ tự thẩm quyền) |
```
Sort by consequence for the 23/11 deliverable, not by file order. End with the 1–3 that need a human decision.

## Worked mini-example (form B, abridged)
Request: "Thêm chỉ số tỷ lệ thắng (win rate) vào dashboard."
- Need: user wants a quick feel for how often their sells make money. Solution given: a new "win rate" number.
- Sources: 03 defines `Realized.realized` per SELL, 04 has `holding.avg_days_win/loss` but no win rate; the plan lists no such indicator and no warning threshold.
- Gaps: unit of count (per SELL line vs per closed position vs per symbol); is a sell with realized exactly 0 a win; are fees/tax included (03 says realized is net of fee and tax); sample gate (`min_sample.sells` = 10?); is it a *flag* or info only (no threshold → info only, otherwise a new flag touches 05/08/09/10/11/12).
- Questions: (1) Info-only card, or a warning with a threshold? recommend info-only (no new flag, no persona/eval churn). (2) Count per SELL or per fully closed position? recommend per SELL (already in `Realized`).
- Acceptance: 4 SELLs with realized +120,000 / −30,000 / +5,000 / −8,000 → win_rate 0.5; n_sells 4 < 10 → displayed as "Chưa đủ dữ liệu".
- Impact: 04 (one key), 10 (card), 12 optional, `formula_version` bump because Metrics schema grows.
