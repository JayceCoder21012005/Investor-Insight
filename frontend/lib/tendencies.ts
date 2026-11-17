// Display metadata for the seven tendencies. Values, thresholds and flags all come from the API;
// this file only decides how they are labeled and which of them to show.
import type { Flag, Metrics, Thresholds } from "./api";
import { formatNumber, formatPercent } from "./format";

export type TendencyId =
  | "overtrading"
  | "concentration"
  | "disposition"
  | "chasing"
  | "herding"
  | "risk_mismatch"
  | "overconfidence";

export type Status = "ok" | "attention" | "insufficient";

export const STATUS_LABEL: Record<Status, string> = {
  ok: "Bình thường",
  attention: "Cần chú ý",
  insufficient: "Chưa đủ dữ liệu",
};

export type Headline = { value: string; caption: string; threshold: string };

export type Tendency = {
  id: TendencyId;
  label: string;
  /** Plain-language formula shown in the "Cách tính" popover. */
  formula: string;
  /** The sample-size key the API reports in `insufficient_data` when this tendency cannot be judged. */
  sampleKey?: string;
  headline: (m: Metrics, t: Thresholds) => Headline;
  /** Inputs listed under the formula so the user sees exactly which numbers were used. */
  inputs: (m: Metrics) => { label: string; value: string }[];
};

const pct0 = (x: number) => formatPercent(x, 0);

export const TENDENCIES: Tendency[] = [
  {
    id: "overtrading",
    label: "Giao dịch quá thường xuyên",
    formula:
      "Vòng quay tháng = giá trị bán trong tháng ÷ giá trị danh mục bình quân của tháng đó. Tín hiệu bật khi vòng quay trung bình vượt ngưỡng, hoặc khi một tháng cao hơn nhiều lần mức trung bình của ba tháng liền trước.",
    headline: (m, t) => ({
      value: pct0(m.metrics.activity.avg_turnover),
      caption: "Vòng quay trung bình mỗi tháng",
      threshold: `Ngưỡng: trên ${pct0(t.turnover.monthly_warn)} mỗi tháng, hoặc một tháng gấp ${formatNumber(t.turnover.spike_vs_3m, 1)} lần trung bình ${t.turnover.spike_baseline_months} tháng trước (và từ ${pct0(t.turnover.spike_min_value)} trở lên)`,
    }),
    inputs: (m) => [
      { label: "Vòng quay trung bình", value: pct0(m.metrics.activity.avg_turnover) },
      { label: "Số lệnh mỗi tháng", value: formatNumber(m.metrics.activity.trades_per_month, 1) },
    ],
  },
  {
    id: "concentration",
    label: "Tập trung danh mục",
    formula:
      "HHI = tổng bình phương tỷ trọng giá trị của từng mã tại ngày cuối kỳ. Tín hiệu bật khi HHI vượt ngưỡng hoặc một mã chiếm tỷ trọng quá lớn.",
    headline: (m, t) => ({
      value: formatNumber(m.metrics.concentration.hhi, 2),
      caption: `HHI · mã lớn nhất ${m.metrics.concentration.top_symbol ?? "—"} chiếm ${pct0(m.metrics.concentration.top_symbol_weight)}`,
      threshold: `Ngưỡng: HHI trên ${formatNumber(t.concentration.hhi_warn, 2)} hoặc một mã trên ${pct0(t.concentration.top_symbol_warn)}`,
    }),
    inputs: (m) => [
      { label: "HHI", value: formatNumber(m.metrics.concentration.hhi, 2) },
      { label: "Mã lớn nhất", value: `${m.metrics.concentration.top_symbol ?? "—"} (${pct0(m.metrics.concentration.top_symbol_weight)})` },
      { label: "Ngành lớn nhất", value: `${m.metrics.concentration.top_sector ?? "—"} (${pct0(m.metrics.concentration.top_sector_weight)})` },
    ],
  },
  {
    id: "disposition",
    label: "Chốt lời sớm, giữ lỗ lâu",
    sampleKey: "disposition.n_sells",
    formula:
      "Vào mỗi ngày có lệnh bán, đếm các vị thế lãi/lỗ đã chốt và chưa chốt. PGR = lãi đã chốt ÷ (lãi đã chốt + lãi chưa chốt); PLR tính tương tự cho lỗ; DE = PGR − PLR (Odean, 1998). Vị thế có giá vốn nằm giữa giá thấp và cao của ngày không được tính.",
    headline: (m, t) => ({
      value: formatNumber(m.metrics.disposition.de, 2),
      caption: `DE = PGR − PLR · ${m.metrics.disposition.n_sells} lệnh bán`,
      threshold: `Ngưỡng: DE trên ${formatNumber(t.disposition.de_warn, 2)}, cần tối thiểu ${t.min_sample.sells} lệnh bán`,
    }),
    inputs: (m) => [
      { label: "PGR (tỷ lệ chốt lời)", value: pct0(m.metrics.disposition.pgr) },
      { label: "PLR (tỷ lệ cắt lỗ)", value: pct0(m.metrics.disposition.plr) },
      { label: "Ngày nắm giữ TB, lệnh lãi", value: formatNumber(m.metrics.holding.avg_days_win, 0) },
      { label: "Ngày nắm giữ TB, lệnh lỗ", value: formatNumber(m.metrics.holding.avg_days_loss, 0) },
    ],
  },
  {
    id: "chasing",
    label: "Mua đuổi giá tăng",
    sampleKey: "chasing.n_buys",
    formula:
      "Tỷ lệ lệnh mua mà mã đã tăng từ mức ngưỡng trở lên trong các phiên liền trước ngày mua. Tính trên giá điều chỉnh.",
    headline: (m, t) => ({
      value: pct0(m.metrics.chasing.ratio),
      caption: `${m.metrics.chasing.n_buys} lệnh mua`,
      threshold: `Ngưỡng: trên ${pct0(t.chasing.ratio_warn)} lệnh mua (mã đã tăng từ ${pct0(t.chasing.rise)} trong ${t.chasing.lookback_sessions} phiên trước), cần tối thiểu ${t.min_sample.buys} lệnh mua`,
    }),
    inputs: (m) => [
      { label: "Tỷ lệ mua đuổi", value: pct0(m.metrics.chasing.ratio) },
      { label: "Số lệnh mua", value: String(m.metrics.chasing.n_buys) },
    ],
  },
  {
    id: "herding",
    label: "Bán theo thị trường chung",
    sampleKey: "herding.n_sells",
    formula:
      "lift = (tỷ lệ lệnh bán rơi vào phiên VN-Index giảm mạnh hoặc phiên liền sau) ÷ (tỷ lệ các phiên đó trong cả giai đoạn). Lift bằng 1 là mức ngẫu nhiên.",
    headline: (m, t) => ({
      value: formatNumber(m.metrics.herding.lift, 1),
      caption: `lift · ${m.metrics.herding.n_sells} lệnh bán`,
      threshold: `Ngưỡng: từ ${formatNumber(t.herding.lift_warn, 1)} trở lên (phiên VN-Index giảm từ ${pct0(Math.abs(t.herding.index_drop))}), cần tối thiểu ${t.min_sample.sells} lệnh bán`,
    }),
    inputs: (m) => [
      { label: "Lift", value: formatNumber(m.metrics.herding.lift, 1) },
      { label: "Số lệnh bán", value: String(m.metrics.herding.n_sells) },
    ],
  },
  {
    id: "risk_mismatch",
    label: "Lệch khẩu vị rủi ro",
    formula:
      "So HHI của danh mục với giới hạn của nhóm khẩu vị bạn đã khai báo, và so độ biến động lợi suất hằng năm với độ biến động của VN-Index trong cùng thời gian (tối đa bao nhiêu lần tùy nhóm khẩu vị).",
    headline: (m, t) => {
      const tier = t.risk_tiers[m.profile.tier];
      return {
        value: `${formatNumber(m.metrics.concentration.hhi, 2)} · ${pct0(m.metrics.performance.vol_annual)}`,
        caption: "HHI · độ biến động hằng năm",
        threshold: `Giới hạn nhóm đã khai: HHI tối đa ${formatNumber(tier.hhi_max, 2)}, biến động tối đa ${formatNumber(tier.vol_ratio_max, 1)} lần VN-Index (${pct0(tier.vol_ratio_max * m.metrics.performance.benchmark_vol)})`,
      };
    },
    inputs: (m) => [
      { label: "HHI", value: formatNumber(m.metrics.concentration.hhi, 2) },
      { label: "Độ biến động hằng năm", value: pct0(m.metrics.performance.vol_annual) },
      { label: "Độ biến động VN-Index cùng kỳ", value: pct0(m.metrics.performance.benchmark_vol) },
    ],
  },
  {
    id: "overconfidence",
    label: "Giao dịch nhiều nhưng kém thị trường",
    formula:
      "Tín hiệu chỉ bật khi cả hai điều kiện cùng đúng: vòng quay cao (như ở mục giao dịch quá thường xuyên) và lợi suất thấp hơn VN-Index trong cùng kỳ.",
    headline: (m) => ({
      value: formatPercent(m.metrics.performance.excess, 1),
      caption: "Chênh lệch lợi suất so với VN-Index",
      threshold: "Điều kiện: vòng quay cao và chênh lệch dưới 0",
    }),
    inputs: (m) => [
      { label: "Vòng quay trung bình", value: pct0(m.metrics.activity.avg_turnover) },
      { label: "Lợi suất danh mục", value: formatPercent(m.metrics.performance.twr, 1) },
      { label: "Lợi suất VN-Index", value: formatPercent(m.metrics.performance.benchmark_return, 1) },
    ],
  },
];

/** How the API's flag list maps onto the three statuses shown on a tendency card. */
export function statusOf(id: TendencyId, flags: Flag[]): Status {
  if (flags.some((f) => f.id === id)) return "attention";
  const key = TENDENCIES.find((t) => t.id === id)?.sampleKey;
  const lacking = flags.find((f) => f.id === "insufficient_data");
  if (key && lacking?.evidence_keys.includes(key)) return "insufficient";
  return "ok";
}
