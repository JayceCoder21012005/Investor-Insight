# 05 — Flags and risk profile

## Goal
Score the risk questionnaire; turn metrics into flags and an investor type.

## Files
`app/core/risk.py`, `app/core/flags.py`, `tests/test_risk.py`, `tests/test_flags.py`

## risk.py
`score(answers: list[int]) -> RiskProfile(score, tier, level)`; 5 answers, each 1–4.

| question (UI text) | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Thời gian dự định đầu tư | < 1 năm | 1–3 năm | 3–5 năm | > 5 năm |
| Kinh nghiệm đầu tư chứng khoán | < 1 năm | 1–3 năm | 3–5 năm | > 5 năm |
| Danh mục giảm 20% trong một tháng, bạn sẽ | Bán hết | Bán bớt | Giữ nguyên | Mua thêm |
| Mục tiêu chính | Bảo toàn vốn | Thu nhập ổn định | Tăng trưởng | Tăng trưởng mạnh |
| Mức lỗ tối đa chấp nhận trong một năm | < 5% | 5–15% | 15–30% | > 30% |

- tier from `risk_tiers.*.score` ranges: conservative / balanced / growth
- level from question 2: 1 → beginner, 2 → intermediate, 3–4 → experienced

## flags.py
`evaluate(metrics, cfg) -> (flags, investor_type)`; `Flag = {id, severity: "warn", evidence_keys: list[str]}`

| id | fires when | evidence_keys |
|---|---|---|
| overtrading | avg_turnover > monthly_warn OR any month > spike_vs_3m × mean of previous 3 months and ≥ spike_min_value | activity.avg_turnover, activity.trades_per_month |
| concentration | hhi > hhi_warn OR top_symbol_weight > top_symbol_warn | concentration.hhi, concentration.top_symbol_weight |
| disposition | de > de_warn | disposition.pgr, disposition.plr, holding.avg_days_win, holding.avg_days_loss |
| chasing | ratio > ratio_warn | chasing.ratio, chasing.n_buys |
| herding | lift ≥ lift_warn | herding.lift, herding.n_sells |
| risk_mismatch | hhi > tier.hhi_max OR vol_annual > tier.vol_ratio_max × benchmark_vol | concentration.hhi, performance.vol_annual, performance.benchmark_vol |
| overconfidence | overtrading fired AND excess < 0 | activity.avg_turnover, performance.excess |

Sample gate: disposition and herding need `n_sells ≥ min_sample.sells`; chasing needs `n_buys ≥ min_sample.buys`. If not met, add `{id: "insufficient_data", evidence_keys: [the tendency]}` instead.

investor_type (first match): overtrading → "Giao dịch ngắn hạn"; concentration → "Tập trung"; trades_per_month < 2 and mean holding > 90 days → "Nắm giữ dài hạn"; else "Cân bằng".

## Acceptance
- Answers [1,1,1,1,1] → conservative, beginner; [4,4,4,4,4] → growth, experienced.
- n_sells 6 with de 0.4 → no disposition flag, one insufficient_data entry.
- overconfidence never fires without overtrading.
