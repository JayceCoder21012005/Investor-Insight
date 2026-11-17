import type { RowIssue } from "@/lib/api";
import { FIELD_LABEL } from "@/lib/labels";

export function IssueTable({ title, issues, tone = "error" }: { title: string; issues: RowIssue[]; tone?: "error" | "warning" }) {
  if (issues.length === 0) return null;
  const head = tone === "error" ? "bg-destructive text-white" : "bg-warning-soft text-ink";
  return (
    <div className="mt-6">
      <h3 className={`mb-[-2.5px] inline-block rounded-t-lg border-[2.5px] border-border px-3 py-1 text-sm font-extrabold ${head}`}>
        {title} ({issues.length})
      </h3>
      <div className="comic-panel overflow-x-auto rounded-lg rounded-tl-none bg-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b-[2.5px] border-border bg-muted text-xs font-bold uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Dòng</th>
              <th className="px-3 py-2">Trường</th>
              <th className="px-3 py-2">Thông báo</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, i) => (
              <tr key={`${issue.row}-${issue.field}-${i}`} className="border-t border-dashed border-border/40 even:bg-muted/40">
                <td className="px-3 py-2 font-bold tabular-nums">{issue.row === 0 ? "Cả tệp" : issue.row}</td>
                <td className="px-3 py-2">{FIELD_LABEL[issue.field] ?? issue.field}</td>
                <td className="px-3 py-2">{issue.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
