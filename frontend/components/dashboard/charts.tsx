"use client";

import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from "recharts";
import type { PortfolioView } from "@/lib/api";
import { formatDate, formatNumber, formatPercent } from "@/lib/format";

// SVG presentation attributes (stroke, fill) do not resolve CSS variables, so the theme colours are spelled
// out here; they match --chart-1, --chart-2, --ink and --muted-foreground in globals.css (light theme only).
// Indigo and orange stay distinct for colour-blind readers.
const C1 = "#4f46e5";
const C2 = "#f08a24";
const INK = "#1f1b3d";
const GRID = "rgba(31, 27, 61, 0.14)";
const MUTED_TEXT = "#55526e";
const HOVER = "rgba(31, 27, 61, 0.06)";

const axis = { stroke: INK, strokeWidth: 2, fontSize: 12, fontWeight: 600, tick: { fill: MUTED_TEXT } };
const grid = { strokeDasharray: "4 4", stroke: GRID };

/** Tooltip drawn as a small comic panel. */
function ComicTooltip({
  active,
  payload,
  label,
  formatValue,
  formatLabel,
}: Partial<TooltipContentProps<number, string>> & {
  formatValue: (v: number) => string;
  formatLabel?: (l: string) => ReactNode;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="comic-panel rounded-lg bg-card px-3 py-2 text-xs font-semibold text-card-foreground">
      {label !== undefined && <p className="mb-1 font-bold">{formatLabel ? formatLabel(String(label)) : String(label)}</p>}
      {payload.map((p) => (
        <p key={String(p.dataKey)} className="flex items-center gap-2">
          <span className="size-2.5 rounded-sm border-[1.5px] border-border" style={{ background: p.color }} />
          {p.name}: <span className="tabular-nums">{formatValue(Number(p.value))}</span>
        </p>
      ))}
    </div>
  );
}

export function PortfolioChart({ data }: { data: PortfolioView["rebased"] }) {
  return (
    <div className="h-72 w-full" role="img" aria-label="Biểu đồ đường: danh mục so với VN-Index, quy về 100">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid {...grid} />
          <XAxis dataKey="date" tickFormatter={(d: string) => formatDate(d).slice(0, 5)} minTickGap={32} {...axis} />
          <YAxis domain={["auto", "auto"]} tickFormatter={(v: number) => formatNumber(v, 0)} width={48} {...axis} />
          <Tooltip
            content={<ComicTooltip formatValue={(v) => formatNumber(v, 1)} formatLabel={formatDate} />}
            cursor={{ stroke: INK, strokeWidth: 1.5, strokeDasharray: "3 3" }}
          />
          <Legend iconType="plainline" wrapperStyle={{ fontWeight: 700, fontSize: 13 }} />
          <Line type="monotone" dataKey="portfolio" name="Danh mục" stroke={C1} dot={false} strokeWidth={3.5}
                activeDot={{ r: 5, stroke: INK, strokeWidth: 2 }} />
          <Line type="monotone" dataKey="benchmark" name="VN-Index" stroke={C2} dot={false} strokeWidth={3}
                strokeDasharray="7 4" activeDot={{ r: 5, stroke: INK, strokeWidth: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function WeightBars({ title, weights, color = C1 }: { title: string; weights: Record<string, number>; color?: string }) {
  const data = Object.entries(weights)
    .map(([name, weight]) => ({ name, weight }))
    .sort((a, b) => b.weight - a.weight);
  if (data.length === 0) return <p className="text-sm text-muted-foreground">Hiện không còn vị thế nào.</p>;
  return (
    <div className="w-full" role="img" aria-label={title} style={{ height: Math.max(160, data.length * 34 + 40) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 0, left: 8 }}>
          <CartesianGrid {...grid} horizontal={false} />
          <XAxis type="number" tickFormatter={(v: number) => formatPercent(v, 0)} {...axis} />
          <YAxis type="category" dataKey="name" width={96} {...axis} />
          <Tooltip content={<ComicTooltip formatValue={(v) => formatPercent(v, 1)} />} cursor={{ fill: HOVER }} />
          <Bar dataKey="weight" name="Tỷ trọng" fill={color} stroke={INK} strokeWidth={2} radius={[0, 5, 5, 0]} barSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TurnoverChart({ data }: { data: { month: string; value: number }[] }) {
  return (
    <div className="h-40 w-full" role="img" aria-label="Vòng quay theo tháng">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="month" tickFormatter={(m: string) => m.slice(5)} {...axis} />
          <YAxis tickFormatter={(v: number) => formatPercent(v, 0)} width={44} {...axis} />
          <Tooltip content={<ComicTooltip formatValue={(v) => formatPercent(v, 0)} formatLabel={(m) => `Tháng ${m}`} />}
                   cursor={{ fill: HOVER }} />
          <Bar dataKey="value" name="Vòng quay" fill={C1} stroke={INK} strokeWidth={2} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PgrPlrChart({ pgr, plr }: { pgr: number; plr: number }) {
  const data = [
    { name: "PGR (chốt lời)", value: pgr },
    { name: "PLR (cắt lỗ)", value: plr },
  ];
  return (
    <div className="h-36 w-full" role="img" aria-label="So sánh PGR và PLR">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="name" {...axis} fontSize={11} />
          <YAxis tickFormatter={(v: number) => formatPercent(v, 0)} width={44} {...axis} />
          <Tooltip content={<ComicTooltip formatValue={(v) => formatPercent(v, 1)} />} cursor={{ fill: HOVER }} />
          <Bar dataKey="value" name="Tỷ lệ" fill={C1} stroke={INK} strokeWidth={2} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HoldingChart({ win, loss }: { win: number | null; loss: number | null }) {
  if (win === null || loss === null) return null;
  const data = [
    { name: "Lệnh lãi", days: win },
    { name: "Lệnh lỗ", days: loss },
  ];
  return (
    <div className="h-36 w-full" role="img" aria-label="Số ngày nắm giữ trung bình: lệnh lãi so với lệnh lỗ">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="name" {...axis} fontSize={11} />
          <YAxis width={36} {...axis} />
          <Tooltip content={<ComicTooltip formatValue={(v) => `${formatNumber(v, 0)} ngày`} />} cursor={{ fill: HOVER }} />
          <Bar dataKey="days" name="Số ngày" fill={C2} stroke={INK} strokeWidth={2} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
