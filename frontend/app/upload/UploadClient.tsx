"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { IssueTable } from "@/components/IssueTable";
import { CircleCheck, Download, FileUp } from "lucide-react";
import { Button, ButtonLink, Card, CoverTitle, ErrorBox, Eyebrow, Spinner } from "@/components/kit";
import { cn } from "@/lib/utils";
import { ApiError, type ValidationResult, api, templateCsvUrl } from "@/lib/api";

export function UploadClient() {
  const id = useSearchParams().get("id");
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rejected, setRejected] = useState<ValidationResult | null>(null);
  const [accepted, setAccepted] = useState<ValidationResult | null>(null);

  if (!id) {
    return (
      <ErrorBox
        message="Chưa có hồ sơ. Hãy trả lời bảng hỏi khẩu vị rủi ro trước khi tải dữ liệu."
        action={<ButtonLink href="/onboarding">Tạo hồ sơ</ButtonLink>}
      />
    );
  }

  async function send(file: File) {
    setBusy(true);
    setError(null);
    setRejected(null);
    setAccepted(null);
    try {
      const { ok, result } = await api.uploadTrades(id as string, file);
      if (!ok) setRejected(result);
      else if (result.warnings.length === 0) router.push(`/dashboard/${id}`);
      else setAccepted(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Không tải được tệp. Vui lòng thử lại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="space-y-2">
        <Eyebrow>Bước 2 / 2</Eyebrow>
        <CoverTitle className="text-5xl">Tải lịch sử giao dịch</CoverTitle>
        <p className="text-sm text-muted-foreground">
          Tệp CSV có các cột: trade_date, symbol, side, quantity, price (fee, tax có thể để trống).{" "}
          <a className="inline-flex items-center gap-1 font-bold text-primary underline decoration-2 underline-offset-2" href={templateCsvUrl()}>
            <Download className="size-3.5" aria-hidden />
            Tải tệp mẫu
          </a>
          . Số thứ tự dòng trong thông báo lỗi không tính dòng tiêu đề.
        </p>
      </div>

      <Card accent="sky" className="p-3">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) void send(file);
          }}
          className={cn(
            "relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-lg border-[2.5px] border-dashed px-6 py-12 text-center transition",
            dragging ? "border-primary bg-secondary/60" : "border-border/70",
          )}
        >
          <div className="halftone absolute -right-6 -bottom-6 size-32 rounded-full text-primary/15" aria-hidden />
          <span className={cn("flex size-16 items-center justify-center rounded-2xl border-[2.5px] border-border bg-sky text-ink shadow-[3px_3px_0_0_var(--ink)] transition-transform", dragging && "-rotate-6 scale-110")}>
            <FileUp className="size-7" aria-hidden />
          </span>
          <p className="comic-title text-2xl">Kéo và thả tệp CSV vào đây</p>
          <p className="text-sm font-medium text-muted-foreground">hoặc</p>
          <Button type="button" variant="pop" onClick={() => input.current?.click()} disabled={busy}>
            Chọn tệp
          </Button>
          <input
            ref={input}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            data-testid="file-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void send(file);
              e.target.value = "";
            }}
          />
          {busy && <Spinner label="Đang kiểm tra tệp…" />}
        </div>
      </Card>

      {error && <ErrorBox message={error} />}

      {rejected && (
        <div>
          <ErrorBox message="Tệp chưa hợp lệ nên chưa được lưu. Hãy sửa các lỗi dưới đây rồi tải lại." />
          <IssueTable title="Lỗi cần sửa" issues={rejected.errors} />
          <IssueTable title="Cảnh báo" issues={rejected.warnings} tone="warning" />
        </div>
      )}

      {accepted && (
        <div>
          <p className="comic-panel flex items-center gap-2 rounded-xl bg-mint p-4 text-sm font-semibold text-ink">
            <CircleCheck className="size-5 shrink-0" aria-hidden />
            Đã lưu {accepted.rows.length} lệnh. Có vài cảnh báo, không chặn việc phân tích.
          </p>
          <IssueTable title="Cảnh báo" issues={accepted.warnings} tone="warning" />
          <div className="mt-4">
            <ButtonLink href={`/dashboard/${id}`}>Xem bảng điều khiển</ButtonLink>
          </div>
        </div>
      )}
    </div>
  );
}
