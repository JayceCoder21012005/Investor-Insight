"use client";

import { useEffect, useState } from "react";
import { BarChart3, BookOpen, Bot, CalendarRange, Gauge } from "lucide-react";
import { Badge, ButtonLink, CoverTitle, ErrorBox, Eyebrow, Spinner } from "@/components/kit";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, type Article, type Metrics, type PortfolioView, type Thresholds, api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { LEVEL_LABEL, TIER_LABEL } from "@/lib/labels";
import { BehaviorTab } from "./BehaviorTab";
import { KnowledgeTab } from "./KnowledgeTab";
import { OverviewTab } from "./OverviewTab";
import { ReportTab } from "./ReportTab";

const TABS = [
  { id: "overview", label: "Tổng quan", icon: BarChart3 },
  { id: "behavior", label: "Hành vi", icon: Gauge },
  { id: "report", label: "Báo cáo AI", icon: Bot },
  { id: "knowledge", label: "Kiến thức", icon: BookOpen },
] as const;
type TabId = (typeof TABS)[number]["id"];

type Data = { metrics: Metrics; thresholds: Thresholds; portfolio: PortfolioView; articles: Article[] };

export function Dashboard({ profileId }: { profileId: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<{ message: string; noTrades: boolean } | null>(null);
  const [tab, setTab] = useState<TabId>("overview");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getMetrics(profileId),
      api.getThresholds(),
      api.getPortfolio(profileId),
      api.getArticles(profileId),
    ])
      .then(([metrics, thresholds, portfolio, articles]) => !cancelled && setData({ metrics, thresholds, portfolio, articles }))
      .catch((e: unknown) => {
        if (cancelled) return;
        const err = e instanceof ApiError ? e : null;
        setError({ message: err?.message ?? "Không tải được dữ liệu.", noTrades: err?.status === 409 });
      });
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  if (error) {
    return (
      <ErrorBox
        message={error.message}
        action={error.noTrades ? <ButtonLink href={`/upload?id=${profileId}`}>Tải dữ liệu giao dịch</ButtonLink> : undefined}
      />
    );
  }
  if (!data) return <Spinner label="Đang tính các chỉ số…" />;

  const { metrics } = data;
  return (
    <div className="space-y-8">
      <header className="comic-panel has-accent accent-gold relative overflow-hidden rounded-2xl bg-card p-5 sm:p-6">
        <div className="halftone absolute -top-8 -right-8 size-40 rounded-full text-primary/20" aria-hidden />
        <div className="relative flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-2">
            <Eyebrow>Hồ sơ của bạn</Eyebrow>
            <CoverTitle className="text-5xl sm:text-6xl">Bảng điều khiển</CoverTitle>
            <p className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <CalendarRange className="size-4" aria-hidden />
              {formatDate(metrics.period.start)} – {formatDate(metrics.period.end)} · công thức {metrics.formula_version}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="pop" tilt>{metrics.investor_type ?? "—"}</Badge>
            <Badge tone="info">Khẩu vị: {TIER_LABEL[metrics.profile.tier]}</Badge>
            <Badge>{LEVEL_LABEL[metrics.profile.level]}</Badge>
          </div>
        </div>
      </header>

      <Tabs value={tab} onValueChange={(v) => setTab(v as TabId)} className="gap-6">
        <TabsList aria-label="Các mục của bảng điều khiển" className="grid w-full grid-cols-2 gap-3 bg-transparent p-0 group-data-horizontal/tabs:h-auto sm:flex sm:flex-wrap sm:justify-start">
          {TABS.map(({ id, label, icon: Icon }) => (
            <TabsTrigger
              key={id}
              value={id}
              className="comic-press h-10 w-full flex-none rounded-lg sm:w-auto border-border bg-card px-4 text-sm font-bold text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-active:bg-primary data-active:text-primary-foreground"
            >
              <Icon aria-hidden />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="overview"><OverviewTab metrics={metrics} portfolio={data.portfolio} /></TabsContent>
        <TabsContent value="behavior"><BehaviorTab metrics={metrics} thresholds={data.thresholds} /></TabsContent>
        <TabsContent value="report"><ReportTab profileId={profileId} /></TabsContent>
        <TabsContent value="knowledge"><KnowledgeTab articles={data.articles} /></TabsContent>
      </Tabs>
    </div>
  );
}
