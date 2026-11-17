import Link from "next/link";
import { ArrowUp, Bot, Calculator, Download, ShieldCheck, type LucideIcon } from "lucide-react";
import { LogoMark } from "@/components/Logo";
import { templateCsvUrl } from "@/lib/api";

const EXPLORE: { href: string; label: string; external?: boolean }[] = [
  { href: "/", label: "Trang chủ" },
  { href: "/#demo", label: "Hồ sơ mẫu" },
  { href: "/onboarding", label: "Tạo hồ sơ khẩu vị rủi ro" },
];

const PRINCIPLES: { icon: LucideIcon; title: string; body: string; chip: string }[] = [
  { icon: Calculator, title: "Số liệu do mã tính", body: "Mọi chỉ số dùng công thức cố định, xem được cách tính.", chip: "bg-sky" },
  { icon: Bot, title: "AI chỉ diễn giải", body: "AI không tự tạo con số, câu chữ được kiểm tra trước khi hiển thị.", chip: "bg-mint" },
  { icon: ShieldCheck, title: "Không gợi ý mua bán", body: "Không có mã nào được khuyên mua, bán hay nắm giữ.", chip: "bg-pink" },
];

// Styles live here (not in globals.css) so the footer renders correctly even when a dev server serves a
// cached stylesheet. Colours come from the theme variables on :root.
const INK_PAGE = {
  backgroundColor: "var(--ink)",
  backgroundImage: "radial-gradient(oklch(1 0 0 / 6%) 1.2px, transparent 1.3px)",
  backgroundSize: "14px 14px",
};
// A gently rising, wobbly price line across the footer's top edge (viewBox 1200 x 40).
const PRICE_LINE =
  "M0 30 L60 27 L110 32 L170 24 L230 28 L290 19 L340 25 L400 21 L460 29 L520 20 L580 23 L640 14 " +
  "L700 21 L760 17 L820 24 L880 13 L940 18 L1000 10 L1060 16 L1120 8 L1200 11";
const LINK =
  "rounded text-white/85 underline decoration-transparent decoration-2 underline-offset-4 transition-colors " +
  "hover:text-gold hover:decoration-gold focus-visible:outline-gold";

/** Comic "last page": ink background, colour-strip edge, brand + links + principles, and the disclaimer panel. */
export function Footer() {
  return (
    <footer className="relative mt-20 text-card" style={INK_PAGE}>
      {/* the top edge is a price line: the page "ends" on a chart, filled with ink below it */}
      <svg
        className="pointer-events-none absolute inset-x-0 -top-10 h-10 w-full"
        viewBox="0 0 1200 40"
        preserveAspectRatio="none"
        aria-hidden
      >
        <path d={`${PRICE_LINE} L1200 40 L0 40 Z`} fill="var(--ink)" />
        <path d={PRICE_LINE} fill="none" stroke="var(--gold)" strokeWidth="3" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="relative overflow-hidden">
        <div className="halftone pointer-events-none absolute -right-10 -top-10 size-56 rounded-full text-white/10" aria-hidden />

        <div className="relative mx-auto max-w-6xl px-4 pb-6 pt-12">
          <div className="grid gap-10 md:grid-cols-12">
            {/* Brand */}
            <div className="md:col-span-5">
              <Link href="/" className="group inline-flex items-center gap-2.5 rounded-md">
                <span className="grid size-12 place-items-center rounded-lg border-[2.5px] border-ink bg-card shadow-[3px_3px_0_0_var(--gold)]">
                  <LogoMark className="size-9 transition-transform group-hover:-rotate-6" />
                </span>
                <span className="comic-title text-3xl">
                  Investor <span className="text-gold">Insight</span>
                </span>
              </Link>
              <p className="mt-4 max-w-sm font-hand text-lg leading-snug text-white/85">
                Nhìn lại hành vi đầu tư của chính bạn bằng số liệu rõ ràng, không phán xét.
              </p>
              <Link
                href="/onboarding"
                className="mt-5 border-[2.5px] border-ink shadow-[3px_3px_0_0_var(--card)] transition-[transform,box-shadow] duration-100 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[5px_5px_0_0_var(--card)] active:translate-x-[3px] active:translate-y-[3px] active:shadow-none inline-flex items-center rounded-md bg-gold px-4 py-2 text-sm font-bold text-ink"
              >
                Bắt đầu soi hồ sơ →
              </Link>
            </div>

            {/* Links */}
            <nav aria-label="Liên kết chân trang" className="md:col-span-3">
              <h2 className="comic-title text-xl text-gold">Khám phá</h2>
              <ul className="mt-3 space-y-2 text-sm font-semibold">
                {EXPLORE.map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className={LINK}>
                      {l.label}
                    </Link>
                  </li>
                ))}
                <li>
                  <a href={templateCsvUrl()} className={`${LINK} inline-flex items-center gap-1.5`}>
                    <Download className="size-3.5" aria-hidden />
                    Tải tệp CSV mẫu
                  </a>
                </li>
              </ul>
            </nav>

            {/* Principles */}
            <div className="md:col-span-4">
              <h2 className="comic-title text-xl text-gold">Nguyên tắc</h2>
              <ul className="mt-3 space-y-3">
                {PRINCIPLES.map(({ icon: Icon, title, body, chip }) => (
                  <li key={title} className="flex gap-3">
                    <span
                      className={`grid size-8 shrink-0 place-items-center rounded-md border-2 border-card text-ink ${chip}`}
                    >
                      <Icon className="size-4" aria-hidden />
                    </span>
                    <span className="text-sm">
                      <span className="block font-bold">{title}</span>
                      <span className="text-white/70">{body}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Disclaimer panel */}
          <div className="mt-10 flex flex-col gap-3 rounded-xl border-[2.5px] border-ink bg-gold p-4 text-ink shadow-[5px_5px_0_0_var(--card)] sm:flex-row sm:items-center">
            <span className="comic-burst grid size-12 shrink-0 place-items-center bg-pink font-comic text-xl text-ink" aria-hidden>
              !
            </span>
            <p className="text-sm">
              <span className="font-bold">
                <ShieldCheck className="mr-1.5 inline size-4 -translate-y-px align-middle" aria-hidden />
                <span>Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư.</span>
              </span>{" "}
              <span className="font-medium">
                Kết quả phản ánh dữ liệu bạn tải lên. Mọi quyết định mua bán là của bạn.
              </span>
            </p>
          </div>

          {/* Bottom bar */}
          <div className="mt-8 flex flex-col items-center justify-between gap-3 border-t-2 border-dashed border-white/25 pt-5 text-xs text-white/70 sm:flex-row">
            <p>
              © {new Date().getFullYear()} Investor Insight · Dữ liệu giá tham chiếu từ VNDIRECT
            </p>
            <a href="#" className={`${LINK} inline-flex items-center gap-1 font-semibold`}>
              <ArrowUp className="size-3.5" aria-hidden />
              Lên đầu trang
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
