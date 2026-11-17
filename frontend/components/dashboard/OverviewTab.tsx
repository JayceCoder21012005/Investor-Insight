"use client";

import { ArrowDownRight, ArrowUpRight, Coins, LineChart, Receipt, Scale, type LucideIcon } from "lucide-react";
import { type Accent, ACCENT_CHIP, Card, Heading } from "@/components/kit";
import type { Metrics, PortfolioView } from "@/lib/api";
import { formatPercent, formatVnd } from "@/lib/format";
import { cn } from "@/lib/utils";
import { PortfolioChart, WeightBars } from "./charts";


function Stat({ label, value, sub, icon: Icon, accent, trend }: {
  label: string;
  value: string;
  sub?: string;
  icon: LucideIcon;
  accent: Accent;
  trend?: number;
}) {
  const TrendIcon = trend === undefined ? null : trend >= 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <Card accent={accent} className="relative flex flex-col gap-1 p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-muted-foreground">{label}</p>
        <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg border-2 border-border", ACCENT_CHIP[accent])}>
          <Icon className="size-4" aria-hidden />
        </span>
      </div>
      <p className="mt-1 flex items-center gap-1 text-2xl font-extrabold tabular-nums">
        {value}
        {TrendIcon && <TrendIcon className="size-5" aria-hidden />}
      </p>
      {sub && <p className="text-xs font-medium text-muted-foreground">{sub}</p>}
    </Card>
  );
}

export function OverviewTab({ metrics, portfolio }: { metrics: Metrics; portfolio: PortfolioView }) {
  const p = metrics.metrics.performance;
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label="Lợi suất danh mục (TWR)" value={formatPercent(p.twr)} icon={LineChart} accent="indigo" trend={p.twr} />
        <Stat label="VN-Index cùng kỳ" value={formatPercent(p.benchmark_return)} icon={Scale} accent="orange" />
        <Stat
          label="Chênh lệch so với VN-Index"
          value={formatPercent(p.excess)}
          icon={Scale}
          accent={p.excess >= 0 ? "mint" : "pink"}
          trend={p.excess}
        />
        <Stat label="Lãi/lỗ đã thực hiện" value={formatVnd(p.realized_pnl)} sub={`Chưa thực hiện: ${formatVnd(p.unrealized_pnl)}`} icon={Coins} accent="gold" />
        <Stat label="Chi phí giao dịch" value={`Phí ${formatVnd(p.fees_total)}`} sub={`Thuế ${formatVnd(p.tax_total)}`} icon={Receipt} accent="sky" />
      </div>

      <Card accent="indigo">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <Heading className="text-2xl">Danh mục so với VN-Index</Heading>
            <p className="text-xs font-medium text-muted-foreground">Cả hai quy về 100 tại ngày giao dịch đầu tiên.</p>
          </div>
          <span
            className={cn(
              "rounded-md border-2 border-border px-2 py-0.5 text-xs font-bold shadow-[2px_2px_0_0_var(--ink)]",
              p.excess >= 0 ? "bg-mint text-ink" : "bg-pink text-ink",
            )}
          >
            {p.excess >= 0 ? "Hơn" : "Kém"} VN-Index {formatPercent(Math.abs(p.excess))}
          </span>
        </div>
        <PortfolioChart data={portfolio.rebased} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card accent="sky" corner>
          <Heading className="mb-3 text-2xl">Tỷ trọng theo mã (ngày cuối kỳ)</Heading>
          <WeightBars title="Tỷ trọng theo mã" weights={portfolio.weights_symbol} />
        </Card>
        <Card accent="orange" corner>
          <Heading className="mb-3 text-2xl">Tỷ trọng theo ngành</Heading>
          <WeightBars title="Tỷ trọng theo ngành" weights={portfolio.weights_sector} color="#f08a24" />
        </Card>
      </div>
    </div>
  );
}
