import { Bot, CircleCheck, HelpCircle, Info, ShieldAlert, Sparkles, ThumbsUp } from "lucide-react";
import { type Accent, ACCENT_CHIP, Badge, Card } from "@/components/kit";
import type { ReportOut } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCENTS: Accent[] = ["pink", "sky", "gold", "mint", "orange", "indigo"];

/** The AI's report as a comic strip: the summary is the AI's speech bubble, each insight its own panel. */
export function ReportView({ report }: { report: ReportOut }) {
  const { content } = report;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="info">
          <Sparkles className="size-3.5" aria-hidden />
          Nội dung do AI tạo
        </Badge>
        <Badge tone={report.passed ? "good" : "warn"}>
          {report.passed ? <CircleCheck className="size-3.5" aria-hidden /> : <ShieldAlert className="size-3.5" aria-hidden />}
          Kiểm tra số liệu: {report.passed ? "đạt" : "không đạt"}
        </Badge>
        {!report.passed && (
          <span className="text-xs font-medium text-muted-foreground">Một phần nội dung được thay bằng mẫu câu viết sẵn.</span>
        )}
      </div>

      {/* summary: the AI "speaks" */}
      <div className="flex items-end gap-3 pb-4">
        <div className="comic-panel comic-bubble flex-1 rounded-2xl bg-card px-5 py-4">
          <h3 className="comic-title mb-1 text-2xl">Tóm tắt</h3>
          <p className="font-hand text-xl leading-snug">{content.summary}</p>
        </div>
      </div>
      <div className="-mt-6 ml-2 flex size-12 items-center justify-center rounded-full border-[2.5px] border-border bg-primary text-primary-foreground shadow-[3px_3px_0_0_var(--ink)]" aria-hidden>
        <Bot className="size-6" />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {content.insights.map((insight, i) => (
          <Card key={insight.flag_id} accent={ACCENTS[i % ACCENTS.length]} corner className="flex flex-col gap-3">
            <div className="flex items-start gap-3">
              <span className={cn("comic-title flex size-8 shrink-0 items-center justify-center rounded-md border-2 border-border text-lg", ACCENT_CHIP[ACCENTS[i % ACCENTS.length]])}>
                {i + 1}
              </span>
              <h3 className="text-base leading-snug font-extrabold">{insight.title}</h3>
            </div>
            <p className="leading-relaxed">{insight.observation}</p>
            <p className="mt-auto rotate-[-0.6deg] rounded-lg border-2 border-border bg-secondary p-3 text-sm text-secondary-foreground shadow-[2px_2px_0_0_var(--ink)]">
              <HelpCircle className="mr-1 inline size-4 align-[-3px]" aria-hidden />
              <span className="font-bold">Câu hỏi để tự suy ngẫm: </span>
              {insight.self_check_question}
            </p>
            <p className="text-xs text-muted-foreground">Số liệu dẫn chứng: {insight.evidence_keys.join(", ")}</p>
          </Card>
        ))}
      </div>

      {content.strengths.length > 0 && (
        <Card accent="mint">
          <h3 className="comic-title mb-2 flex items-center gap-2 text-2xl">
            <ThumbsUp className="size-5" aria-hidden /> Điểm tích cực
          </h3>
          <ul className="list-disc space-y-1 pl-5 font-medium">
            {content.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="border-dashed">
        <h3 className="mb-2 flex items-center gap-2 text-base font-extrabold">
          <Info className="size-4.5" aria-hidden /> Giới hạn của báo cáo
        </h3>
        <p className="text-sm text-muted-foreground">{content.limitations}</p>
      </Card>

      <p className="text-xs text-muted-foreground">
        Tạo lúc {new Date(report.created_at).toLocaleString("vi-VN")} · mô hình {report.model} · công thức {report.formula_version}
      </p>
    </div>
  );
}
