"use client";

import {
  ArrowRight,
  BarChart3,
  Bot,
  CalendarClock,
  Crosshair,
  FileSpreadsheet,
  Flame,
  Layers,
  type LucideIcon,
  Repeat,
  Scale,
  ShieldAlert,
  Users,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { type Accent, ACCENT_CHIP, Badge, Button, ButtonLink, Card, CoverTitle, ErrorBox, Eyebrow, Heading } from "@/components/kit";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, type DemoItem, api } from "@/lib/api";
import { TIER_LABEL } from "@/lib/labels";
import { cn } from "@/lib/utils";

// One recognizable icon per demo persona; purely decorative.
const PERSONA_ICON: Record<string, LucideIcon> = {
  P01: Zap, P02: Crosshair, P03: Scale, P04: Flame, P05: ShieldAlert, P06: Repeat,
  P07: Layers, P08: CalendarClock, P09: BarChart3, P10: FileSpreadsheet, P11: Users,
};

// Risk tier as the colour of each panel's shadow and icon chip, so the list can be scanned by tier.
const TIER_ACCENT: Record<string, Accent> = {
  conservative: "mint",
  balanced: "sky",
  growth: "pink",
};

const STEPS = [
  { icon: FileSpreadsheet, title: "Tải lịch sử lệnh", text: "Tệp CSV từ công ty chứng khoán, kèm 5 câu hỏi khẩu vị rủi ro.", accent: "sky" },
  { icon: BarChart3, title: "Mã tính chỉ số", text: "Lợi suất, vòng quay, PGR/PLR, mua đuổi… bằng công thức cố định.", accent: "gold" },
  { icon: Bot, title: "AI diễn giải", text: "Viết lại bằng lời dễ hiểu; mọi con số đều được kiểm tra với số liệu gốc.", accent: "pink" },
] as const;

export default function HomePage() {
  const router = useRouter();
  const [demos, setDemos] = useState<DemoItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDemo()
      .then(setDemos)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Không tải được danh sách hồ sơ demo."));
  }, []);

  async function openDemo(personaId: string) {
    setLoadingId(personaId);
    setError(null);
    try {
      const { id } = await api.loadDemo(personaId);
      router.push(`/dashboard/${id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Không mở được hồ sơ demo.");
      setLoadingId(null);
    }
  }

  return (
    <div className="space-y-16">
      {/* ---------------------------------------------------------------- hero panel */}
      <section className="comic-panel relative isolate overflow-hidden rounded-2xl bg-card px-6 py-10 sm:px-10 sm:py-14">
        <div className="halftone absolute -top-10 -right-10 -z-10 size-72 rounded-full text-primary/25" aria-hidden />
        <div className="halftone absolute -bottom-16 -left-12 -z-10 size-56 rounded-full text-gold" aria-hidden />

        <div className="grid items-center gap-10 lg:grid-cols-[1.35fr_1fr]">
          <div className="space-y-6">
            <Eyebrow>Tập 1 · Tấm gương giao dịch</Eyebrow>
            <CoverTitle className="text-5xl sm:text-[4.2rem]">
              Nhìn lại hành vi giao dịch <span className="pop">của chính bạn!</span>
            </CoverTitle>
            <p className="max-w-xl text-lg text-muted-foreground">
              Tải lịch sử lệnh, trả lời bảng hỏi khẩu vị rủi ro và nhận các chỉ số hành vi do mã tính, kèm phần diễn giải do AI
              viết và được kiểm tra lại số liệu. Không khuyến nghị mua bán, không dự báo giá.
            </p>
            <div className="flex flex-wrap gap-4">
              <ButtonLink href="/onboarding">
                Tạo hồ sơ của tôi <ArrowRight aria-hidden />
              </ButtonLink>
              <ButtonLink href="#demo" variant="pop">
                Xem hồ sơ mẫu
              </ButtonLink>
            </div>
          </div>

          {/* the "cover art": a question, a burst and an answer, laid out in rows so nothing overlaps */}
          <div className="hidden flex-col gap-8 lg:flex" aria-hidden>
            <div className="flex items-start justify-between gap-4">
              <div className="comic-panel comic-bubble max-w-60 -rotate-3 rounded-2xl bg-card px-5 py-4 font-hand text-xl leading-snug">
                “Mình chốt lời có sớm quá không nhỉ?”
              </div>
              <div className="comic-burst flex size-28 shrink-0 rotate-12 items-center justify-center bg-ink">
                <div className="comic-burst flex size-[6.6rem] items-center justify-center bg-gold">
                  <span className="comic-title -rotate-6 text-center text-xl text-ink">Soi kỹ!</span>
                </div>
              </div>
            </div>
            <div className="comic-panel has-accent accent-gold ml-auto max-w-64 rotate-2 rounded-2xl bg-card px-5 py-4 font-hand text-lg leading-snug">
              PGR 31% so với PLR 4%: bạn bán mã lãi nhanh hơn mã lỗ gần 8 lần.
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- how it works: 3 panels */}
      <section aria-label="Cách hoạt động" className="grid gap-6 sm:grid-cols-3">
        {STEPS.map(({ icon: Icon, title, text, accent }, i) => (
          <Card key={title} accent={accent} corner className={cn("relative pt-7", i % 2 ? "sm:rotate-1" : "sm:-rotate-1")}>
            <span className="comic-title absolute -top-4 left-4 flex size-9 items-center justify-center rounded-full border-[2.5px] border-border bg-card text-2xl shadow-[2px_2px_0_0_var(--ink)]">
              {i + 1}
            </span>
            <span className={cn("mb-3 flex size-12 items-center justify-center rounded-xl border-[2.5px] border-border", ACCENT_CHIP[accent])}>
              <Icon className="size-6" aria-hidden />
            </span>
            <h2 className="comic-title text-[1.7rem]">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{text}</p>
          </Card>
        ))}
      </section>

      {/* ---------------------------------------------------------------- demo profiles */}
      <section id="demo" className="scroll-mt-24 space-y-6">
        <div className="space-y-2">
          <Eyebrow>Không cần nhập gì</Eyebrow>
          <Heading className="text-[2.6rem]">Dùng hồ sơ demo</Heading>
          <p className="text-sm text-muted-foreground">
            Dữ liệu giao dịch mô phỏng, có sẵn để xem thử toàn bộ luồng mà không cần nhập gì.
          </p>
          <div className="flex flex-wrap gap-2 pt-1 text-xs font-semibold text-muted-foreground">
            <span className="inline-flex items-center gap-1.5"><i className="size-3 rounded-sm border-2 border-border bg-mint" /> Thận trọng</span>
            <span className="inline-flex items-center gap-1.5"><i className="size-3 rounded-sm border-2 border-border bg-sky" /> Cân bằng</span>
            <span className="inline-flex items-center gap-1.5"><i className="size-3 rounded-sm border-2 border-border bg-pink" /> Tăng trưởng</span>
          </div>
        </div>
        {error && <ErrorBox message={error} />}
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {!demos && !error && Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-52 rounded-xl" />)}
          {demos?.map((d) => {
            const Icon = PERSONA_ICON[d.persona_id] ?? BarChart3;
            const accent = TIER_ACCENT[d.tier] ?? "indigo";
            return (
              <Card key={d.persona_id} accent={accent} corner className="group flex flex-col p-0 transition-transform hover:-translate-y-1">
                <div className="flex items-center justify-between gap-3 px-4 pt-4">
                  <span
                    className={cn(
                      "flex size-11 items-center justify-center rounded-xl border-[2.5px] border-border shadow-[2px_2px_0_0_var(--ink)] transition-transform group-hover:-rotate-6",
                      ACCENT_CHIP[accent],
                    )}
                  >
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <Badge tilt className="mr-6">{TIER_LABEL[d.tier] ?? d.tier}</Badge>
                </div>
                <div className="flex flex-1 flex-col gap-3 p-4">
                  <h3 className="text-lg font-bold leading-snug">{d.title}</h3>
                  <p className="flex-1 text-sm text-muted-foreground">{d.description}</p>
                  <Button variant="secondary" onClick={() => openDemo(d.persona_id)} disabled={loadingId !== null}>
                    {loadingId === d.persona_id ? "Đang mở…" : "Xem hồ sơ này"}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}
