import { ShieldCheck } from "lucide-react";

export function Footer() {
  return (
    <footer className="mt-16 border-t-[2.5px] border-border bg-secondary py-5 text-xs text-secondary-foreground">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 sm:flex-row">
        <p className="inline-flex items-center gap-1.5 font-semibold">
          <ShieldCheck className="size-4" aria-hidden />
          <span>Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư.</span>
        </p>
        <p className="font-medium">Chỉ số tính bằng công thức cố định · AI chỉ diễn giải</p>
      </div>
    </footer>
  );
}
