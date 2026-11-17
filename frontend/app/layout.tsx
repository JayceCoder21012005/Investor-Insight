import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";
import { LogoMark } from "@/components/Logo";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

// Fonts are self-hosted from npm (@fontsource): no request to Google at build or run time. Each file is split
// by unicode-range, so a browser downloads only the Latin + Vietnamese pieces it needs.
// Bangers = comic-cover headings, Grandstander = playful but readable UI text, Patrick Hand = speech bubbles.
import "@fontsource/bangers/400.css";
import "@fontsource/grandstander/400.css";
import "@fontsource/grandstander/500.css";
import "@fontsource/grandstander/600.css";
import "@fontsource/grandstander/700.css";
import "@fontsource/grandstander/800.css";
import "@fontsource/patrick-hand/400.css";

export const metadata: Metadata = {
  title: "Investor Insight – Nhìn lại hành vi đầu tư của chính bạn",
  description:
    "Tải lịch sử giao dịch của bạn, nhận các chỉ số hành vi do mã tính và phần diễn giải bằng AI, không khuyến nghị mua bán.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className="font-sans">
      <body className="flex min-h-screen flex-col">
        <TooltipProvider>
          <header className="sticky top-0 z-40 border-b-[2.5px] border-border bg-background/90 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-2.5">
              <Link href="/" className="group flex items-center gap-2.5 rounded-md">
                <LogoMark className="size-9 transition-transform group-hover:-rotate-6" />
                <span className="comic-title text-2xl">
                  Investor <span className="text-primary">Insight</span>
                </span>
              </Link>
              <nav className="flex items-center gap-2 text-sm font-semibold">
                <Link href="/#demo" className="hidden rounded-md px-3 py-1.5 hover:bg-secondary sm:inline">
                  Hồ sơ mẫu
                </Link>
                <Link href="/onboarding" className="comic-press rounded-md bg-secondary px-3 py-1.5 text-secondary-foreground">
                  Tạo hồ sơ
                </Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:py-10">{children}</main>
          <Footer />
        </TooltipProvider>
      </body>
    </html>
  );
}
