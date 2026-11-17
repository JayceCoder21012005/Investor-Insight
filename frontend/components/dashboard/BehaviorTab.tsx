"use client";

import { Info } from "lucide-react";
import { Badge } from "@/components/kit";
import type { Metrics, Thresholds } from "@/lib/api";
import { TENDENCIES } from "@/lib/tendencies";
import { HoldingChart, PgrPlrChart, TurnoverChart } from "./charts";
import { TendencyCard } from "./TendencyCard";

export function BehaviorTab({ metrics, thresholds }: { metrics: Metrics; thresholds: Thresholds }) {
  const m = metrics.metrics;
  return (
    <div className="space-y-6">
      <div className="comic-panel flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl bg-sky px-4 py-3 text-sm font-medium text-ink">
        <Info className="size-5 shrink-0" aria-hidden />
        <p className="flex-1">
          Mỗi thẻ là một dấu hiệu để bạn tự xem lại, không phải kết luận hay chẩn đoán. Mở &quot;Cách tính&quot; để xem công
          thức và số liệu đầu vào.
        </p>
        {metrics.investor_type && (
          <span className="inline-flex items-center gap-2">
            Kiểu nhà đầu tư theo quy tắc: <Badge tone="pop" tilt>{metrics.investor_type}</Badge>
          </span>
        )}
      </div>
      <div className="grid gap-7 pt-2 lg:grid-cols-2">
        {TENDENCIES.map((tendency) => (
          <TendencyCard key={tendency.id} tendency={tendency} metrics={metrics} thresholds={thresholds}>
            {tendency.id === "overtrading" && <TurnoverChart data={m.activity.monthly_turnover} />}
            {tendency.id === "disposition" && (
              <div className="grid grid-cols-2 gap-2">
                <PgrPlrChart pgr={m.disposition.pgr} plr={m.disposition.plr} />
                <HoldingChart win={m.holding.avg_days_win ?? null} loss={m.holding.avg_days_loss ?? null} />
              </div>
            )}
          </TendencyCard>
        ))}
      </div>
    </div>
  );
}
