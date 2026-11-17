# Kết quả đánh giá Investor Insight

- Ngày chạy: 2026-11-17 · formula_version: 0.3 · mô hình LLM: gemini-3.1-flash-lite · commit: n/a · số lần chạy mỗi hồ sơ: 3
- Nguồn giá: VNDIRECT, 2025-11-01 đến 2026-10-31
- Lưu ý: dữ liệu giao dịch là mô phỏng. Việc tự cài rồi tự phát hiện chỉ chứng minh mã chạy đúng đặc tả, không chứng minh hiệu quả trên nhà đầu tư thật.

## 1. Phát hiện khuynh hướng

Số tệp đánh giá: 33.

| Khuynh hướng | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| overtrading | 5 | 0 | 1 | 100% | 83% |
| concentration | 6 | 8 | 0 | 43% | 100% |
| disposition | 6 | 3 | 0 | 67% | 100% |
| chasing | 4 | 0 | 2 | 100% | 67% |
| herding | 3 | 0 | 0 | 100% | 100% |
| risk_mismatch | 3 | 3 | 0 | 50% | 100% |
| overconfidence | 4 | 0 | 1 | 100% | 80% |
| insufficient_data | 18 | 3 | 0 | 86% | 100% |

Nhãn `overconfidence` là nhãn phái sinh, không do persona khai báo: `overtrading AND performance.excess < 0`.

### Ma trận hồ sơ × khuynh hướng

Mỗi ô là số seed có bật cờ trên tổng số seed. Dấu ◆ đánh dấu cờ được kỳ vọng theo nhãn.

| Hồ sơ | overtrading | concentration | disposition | chasing | herding | risk_mismatch | overconfidence | insufficient_data |
|---|---|---|---|---|---|---|---|---|
| P01 | 3/3 ◆ | 3/3 | 1/3 | 0/3 | 0/3 | 2/3 | 3/3 | 0/3 |
| P02 | 0/3 | 3/3 ◆ | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 ◆ |
| P03 | 0/3 | 0/3 | 3/3 ◆ | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| P04 | 0/3 | 1/3 | 0/3 | 3/3 ◆ | 0/3 | 0/3 | 0/3 | 3/3 ◆ |
| P05 | 0/3 | 3/3 | 0/3 | 0/3 | 0/3 | 3/3 ◆ | 0/3 | 3/3 ◆ |
| P06 | 2/3 ◆ | 0/3 | 3/3 ◆ | 0/3 | 0/3 | 0/3 | 1/3 | 0/3 |
| P07 | 0/3 | 3/3 ◆ | 0/3 | 1/3 ◆ | 0/3 | 0/3 | 0/3 | 3/3 ◆ |
| P08 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 ◆ |
| P09 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| P10 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 1/3 | 0/3 | 3/3 ◆ |
| P11 | 0/3 | 1/3 | 2/3 | 0/3 | 3/3 ◆ | 0/3 | 0/3 | 0/3 |

## 2. AI bám số liệu

| Chỉ số | Giá trị |
|---|---|
| Phạm vi | toàn bộ 33 tệp |
| Số báo cáo | 99 |
| Mô hình trả lời được (không tính lỗi API) | 99 |
| Không đánh giá được do lỗi API (hết hạn mức, 503, mạng) | 0 |
| Qua guardrail ở lần sinh đầu tiên | 95% |
| Qua guardrail cuối cùng (không dùng mẫu thay thế) | 98% |
| Số vi phạm number_not_found (lần đầu) | 3 |
| Số vi phạm advice (lần đầu) | 1 |
| Vi phạm khác ở lần đầu (schema, coverage, evidence_key) | schema: 1 |
| Thời gian sinh báo cáo p50 / lớn nhất | 2.8 s / 41.6 s |

## 3. Hiệu năng

| Phép đo | Giá trị |
|---|---|
| Kiểm tra CSV + tính chỉ số, p50 (33 tệp) | 7 ms |
| Kiểm tra CSV + tính chỉ số, lớn nhất | 83 ms |
| Tệp tổng hợp 5.000 dòng | 668 ms |

## 4. Khảo sát người dùng (nhập tay)

<!-- manual:start -->
| Tiêu chí | Điểm trung bình (thang 1-5) |
|---|---|
| Dễ hiểu | chưa thu thập |
| Liên quan | chưa thu thập |
| Hữu ích | chưa thu thập |

Câu hỏi mở: chưa thu thập. Mẫu 5 người chỉ mang tính tham khảo.
<!-- manual:end -->

## Trước hiệu chỉnh

Lần chạy lưu ngày 2026-11-17 (formula_version 0.1).

| Khuynh hướng | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| overtrading | 6 | 11 | 0 | 35% | 100% |
| concentration | 4 | 10 | 2 | 29% | 67% |
| disposition | 6 | 2 | 0 | 75% | 100% |
| chasing | 4 | 0 | 2 | 100% | 67% |
| herding | 3 | 0 | 0 | 100% | 100% |
| risk_mismatch | 3 | 6 | 0 | 33% | 100% |
| overconfidence | 0 | 15 | 0 | 0% | — |
| insufficient_data | 18 | 3 | 0 | 86% | 100% |
