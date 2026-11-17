// Sample API payloads for tests only. Never imported by app code.
import type { Metrics, ReportOut, Thresholds } from "./api";

export const THRESHOLDS: Thresholds = {
  formula_version: "0.3",
  min_sample: { sells: 10, buys: 10 },
  concentration: { hhi_warn: 0.25, top_symbol_warn: 0.4 },
  turnover: { monthly_warn: 1.0, spike_vs_3m: 2.0, spike_baseline_months: 3, spike_min_value: 1.0 },
  disposition: { de_warn: 0.05 },
  chasing: { lookback_sessions: 5, rise: 0.1, ratio_warn: 0.3 },
  herding: { index_drop: -0.02, include_next_session: true, lift_warn: 2.0 },
  investor_type: { long_hold_days: 90, long_hold_max_trades_per_month: 2 },
  risk_tiers: {
    conservative: { score: [5, 9], hhi_max: 0.25, vol_ratio_max: 1.3 },
    balanced: { score: [10, 14], hhi_max: 0.3, vol_ratio_max: 1.6 },
    growth: { score: [15, 20], hhi_max: 0.45, vol_ratio_max: 2.0 },
  },
  fees: { broker_tiers: [[100000000, 0.003]], sell_tax: 0.001 },
  guardrail: { rel_tol: 0.01, abs_tol: 0.051, max_retries: 1, advice_patterns: [] },
} as unknown as Thresholds;

export const METRICS: Metrics = {
  formula_version: "0.2",
  period: { start: "2026-01-05", end: "2026-06-30", months: 6 },
  profile: { tier: "balanced", level: "intermediate" },
  metrics: {
    concentration: { hhi: 0.38, top_symbol: "FPT", top_symbol_weight: 0.5, top_sector: "Công nghệ", top_sector_weight: 0.6 },
    activity: {
      monthly_turnover: [
        { month: "2026-01", value: 0.2 },
        { month: "2026-02", value: 0.4 },
      ],
      avg_turnover: 0.3,
      trades_per_month: 4.5,
    },
    holding: { avg_days_win: 12, avg_days_loss: 40, avg_days: 25 },
    disposition: { pgr: 0.4, plr: 0.1, de: 0.3, n_sell_days: 12, n_sells: 24 },
    chasing: { ratio: 0.1, n_buys: 30 },
    herding: { lift: 1.2, n_sells: 24 },
    performance: {
      twr: 0.08,
      benchmark_return: 0.05,
      excess: 0.03,
      vol_annual: 0.22,
      benchmark_vol: 0.18,
      realized_pnl: 12500000,
      unrealized_pnl: 3000000,
      fees_total: 450000,
      tax_total: 120000,
    },
  },
  flags: [
    { id: "disposition", severity: "warn", evidence_keys: ["disposition.pgr", "disposition.plr"] },
    { id: "concentration", severity: "warn", evidence_keys: ["concentration.hhi"] },
  ],
  investor_type: "Tập trung",
} as Metrics;

export const REPORT: ReportOut = {
  id: "r1",
  created_at: "2026-11-17T10:00:00+00:00",
  formula_version: "0.2",
  model: "claude-opus-5-5",
  attempts: 1,
  passed: true,
  violations: [],
  latency_ms: 4200,
  metrics: METRICS,
  content: {
    summary: "Danh mục có hai dấu hiệu cần xem lại.",
    insights: [
      {
        flag_id: "disposition",
        title: "Chốt lời sớm, giữ lỗ lâu",
        observation: "Tỷ lệ chốt lời (PGR) là 40%, cao hơn tỷ lệ cắt lỗ (PLR) 10%.",
        evidence_keys: ["disposition.pgr", "disposition.plr"],
        self_check_question: "Khi một mã đang lỗ, bạn dựa vào tiêu chí nào để tiếp tục giữ?",
      },
    ],
    strengths: ["Lợi suất cao hơn VN-Index 3,0% trong cùng kỳ."],
    limitations: "Dữ liệu mô phỏng; chỉ số không đọc được ý định giao dịch.",
  },
} as ReportOut;
