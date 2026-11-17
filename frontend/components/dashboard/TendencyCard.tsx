import { ChevronDown, CircleCheck, CircleHelp, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { type Accent, ACCENT_CHIP, Badge, Card } from "@/components/kit";
import type { Metrics, Thresholds } from "@/lib/api";
import { STATUS_LABEL, type Status, type Tendency, statusOf } from "@/lib/tendencies";
import { cn } from "@/lib/utils";

const TONE: Record<Status, "good" | "warn" | "neutral"> = { ok: "good", attention: "warn", insufficient: "neutral" };
const ACCENT: Record<Status, Accent> = { ok: "mint", attention: "pink", insufficient: "sky" };
const ICON = { ok: CircleCheck, attention: TriangleAlert, insufficient: CircleHelp } as const;

export function TendencyCard({
  tendency,
  metrics,
  thresholds,
  children,
}: {
  tendency: Tendency;
  metrics: Metrics;
  thresholds: Thresholds;
  children?: ReactNode;
}) {
  const status = statusOf(tendency.id, metrics.flags ?? []);
  const headline = tendency.headline(metrics, thresholds);
  const Icon = ICON[status];
  return (
    <Card accent={ACCENT[status]} className="relative flex flex-col overflow-visible p-0">
      {status === "attention" && (
        <span aria-hidden className="comic-burst absolute -top-4 -right-3 flex size-12 rotate-12 items-center justify-center bg-ink">
          <span className="comic-burst flex size-[2.6rem] items-center justify-center bg-pink">
            <span className="comic-title text-xl text-ink">!</span>
          </span>
        </span>
      )}
      <div className="flex items-center justify-between gap-3 border-b-[2.5px] border-dashed border-border/40 px-5 py-3">
        <h3 className="flex items-center gap-2.5 text-base font-extrabold">
          <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg border-2 border-border", ACCENT_CHIP[ACCENT[status]])}>
            <Icon className="size-4" aria-hidden />
          </span>
          {tendency.label}
        </h3>
        <Badge tone={TONE[status]} className="mr-5">
          {STATUS_LABEL[status]}
        </Badge>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        <div>
          <p className="comic-title text-4xl tabular-nums">{headline.value}</p>
          <p className="text-sm font-medium text-muted-foreground">{headline.caption}</p>
        </div>
        <p className="w-fit rounded-md border-2 border-dashed border-border/60 bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
          {headline.threshold}
        </p>
        {children}
        <details className="group mt-auto rounded-lg border-2 border-border bg-card text-sm open:shadow-[3px_3px_0_0_var(--ink)]">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 font-bold select-none [&::-webkit-details-marker]:hidden">
            Cách tính
            <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden />
          </summary>
          <div className="border-t-2 border-dashed border-border/50 px-3 py-2">
            <p className="text-muted-foreground">{tendency.formula}</p>
            <ul className="mt-2 space-y-1">
              {tendency.inputs(metrics).map((input) => (
                <li key={input.label} className="flex justify-between gap-4 border-b border-dotted border-border/40 pb-1 last:border-0">
                  <span>{input.label}</span>
                  <span className="font-bold tabular-nums">{input.value}</span>
                </li>
              ))}
            </ul>
          </div>
        </details>
      </div>
    </Card>
  );
}
