"use client";

import { Bot, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, ErrorBox, Spinner } from "@/components/kit";
import { ApiError, type ReportOut, api } from "@/lib/api";
import { ReportView } from "./ReportView";

export function ReportTab({ profileId }: { profileId: string }) {
  const [report, setReport] = useState<ReportOut | null>(null);
  const [loadingLatest, setLoadingLatest] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getLatestReport(profileId)
      .then((r) => !cancelled && setReport(r))
      .catch((e: unknown) => !cancelled && setError(e instanceof ApiError ? e.message : "Không tải được báo cáo gần nhất."))
      .finally(() => !cancelled && setLoadingLatest(false));
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      setReport(await api.createReport(profileId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Không tạo được báo cáo. Vui lòng thử lại.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="comic-panel flex flex-wrap items-center gap-4 rounded-xl bg-card px-5 py-4">
        <div className="flex size-11 items-center justify-center rounded-full border-[2.5px] border-border bg-secondary text-secondary-foreground">
          <Bot className="size-5" aria-hidden />
        </div>
        <p className="min-w-56 flex-1 text-sm font-medium text-muted-foreground">
          AI chỉ diễn giải các chỉ số đã được tính sẵn. Mọi con số trong văn bản đều được kiểm tra lại với số liệu gốc.
        </p>
        <Button onClick={generate} disabled={generating || loadingLatest}>
          <Sparkles aria-hidden />
          {report ? "Cập nhật báo cáo" : "Tạo báo cáo"}
        </Button>
      </div>
      {generating && <Spinner label="Đang tạo báo cáo, có thể mất vài chục giây…" />}
      {loadingLatest && !generating && <Spinner />}
      {error && <ErrorBox message={error} />}
      {report && <ReportView report={report} />}
    </div>
  );
}
