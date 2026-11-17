import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ArticleModal } from "./dashboard/ArticleModal";
import { ReportView } from "./dashboard/ReportView";
import { TendencyCard } from "./dashboard/TendencyCard";
import { Footer } from "./Footer";
import { IssueTable } from "./IssueTable";
import { METRICS, REPORT, THRESHOLDS } from "@/lib/fixtures";
import { TENDENCIES } from "@/lib/tendencies";

describe("Footer", () => {
  it("shows the investment-disclaimer on every page", () => {
    render(<Footer />);
    expect(
      screen.getByText("Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư."),
    ).toBeInTheDocument();
  });
});

describe("IssueTable", () => {
  it("lists each issue with its row number and Vietnamese message", () => {
    render(
      <IssueTable
        title="Lỗi cần sửa"
        issues={[
          { row: 2, field: "quantity", message: "Dòng 2: Bán 500 FPT nhưng chỉ đang nắm giữ 100" },
          { row: 0, field: "file", message: "Thiếu cột bắt buộc: price" },
        ]}
      />,
    );
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(3); // header + 2
    expect(within(rows[1]).getByText("2")).toBeInTheDocument();
    expect(within(rows[1]).getByText(/Bán 500 FPT/)).toBeInTheDocument();
    expect(within(rows[2]).getByText("Cả tệp")).toBeInTheDocument();
  });

  it("renders nothing when there is nothing to report", () => {
    const { container } = render(<IssueTable title="Cảnh báo" issues={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ReportView", () => {
  it("labels AI content and shows a passing guardrail badge", () => {
    render(<ReportView report={REPORT} />);
    expect(screen.getByText("Nội dung do AI tạo")).toBeInTheDocument();
    expect(screen.getByText("Kiểm tra số liệu: đạt")).toBeInTheDocument();
  });

  it("shows 'không đạt' when a template had to replace AI text", () => {
    render(<ReportView report={{ ...REPORT, passed: false }} />);
    expect(screen.getByText("Kiểm tra số liệu: không đạt")).toBeInTheDocument();
  });

  it("renders summary, insight with its self-check question, strengths and limitations", () => {
    render(<ReportView report={REPORT} />);
    expect(screen.getByText("Danh mục có hai dấu hiệu cần xem lại.")).toBeInTheDocument();
    expect(screen.getByText("Chốt lời sớm, giữ lỗ lâu")).toBeInTheDocument();
    expect(screen.getByText(/dựa vào tiêu chí nào/)).toBeInTheDocument();
    expect(screen.getByText(/cao hơn VN-Index/)).toBeInTheDocument();
    expect(screen.getByText(/Dữ liệu mô phỏng/)).toBeInTheDocument();
  });

  it("shows the generation time and model so a report can be reproduced", () => {
    render(<ReportView report={REPORT} />);
    expect(screen.getByText(/claude-opus-5-5/)).toBeInTheDocument();
    expect(screen.getByText(/công thức 0.2/i)).toBeInTheDocument();
  });
});

describe("TendencyCard", () => {
  const disposition = TENDENCIES.find((t) => t.id === "disposition")!;

  it("shows the label, the value, the threshold and a status", () => {
    render(<TendencyCard tendency={disposition} metrics={METRICS} thresholds={THRESHOLDS} />);
    expect(screen.getByText("Chốt lời sớm, giữ lỗ lâu")).toBeInTheDocument();
    expect(screen.getByText("0,3")).toBeInTheDocument();
    expect(screen.getByText(/Ngưỡng: DE trên 0,05/)).toBeInTheDocument();
    expect(screen.getByText("Cần chú ý")).toBeInTheDocument();
  });

  it("shows 'Bình thường' when the API raised no flag for it", () => {
    const chasing = TENDENCIES.find((t) => t.id === "chasing")!;
    render(<TendencyCard tendency={chasing} metrics={METRICS} thresholds={THRESHOLDS} />);
    expect(screen.getByText("Bình thường")).toBeInTheDocument();
  });

  it("shows 'Chưa đủ dữ liệu' when the sample gate failed", () => {
    const m = {
      ...METRICS,
      flags: [{ id: "insufficient_data", severity: "warn", evidence_keys: ["herding.n_sells"] }],
    } as typeof METRICS;
    const herding = TENDENCIES.find((t) => t.id === "herding")!;
    render(<TendencyCard tendency={herding} metrics={m} thresholds={THRESHOLDS} />);
    expect(screen.getByText("Chưa đủ dữ liệu")).toBeInTheDocument();
  });

  it("reveals the formula and the exact inputs in the 'Cách tính' popover", async () => {
    render(<TendencyCard tendency={disposition} metrics={METRICS} thresholds={THRESHOLDS} />);
    expect(screen.queryByText(/Odean/)).not.toBeVisible();
    await userEvent.click(screen.getByText("Cách tính"));
    expect(screen.getByText(/Odean/)).toBeVisible();
    expect(screen.getByText(/PGR \(tỷ lệ chốt lời\)/)).toBeVisible();
    expect(screen.getByText("40%")).toBeVisible();
  });

  it("renders the chart passed as children", () => {
    render(
      <TendencyCard tendency={disposition} metrics={METRICS} thresholds={THRESHOLDS}>
        <div>biểu đồ nhỏ</div>
      </TendencyCard>,
    );
    expect(screen.getByText("biểu đồ nhỏ")).toBeInTheDocument();
  });
});

describe("ArticleModal", () => {
  const article = {
    id: "a1",
    title: "Vì sao ta chốt lời sớm?",
    tags: ["disposition"],
    level: "beginner",
    body: "# Tiêu đề bài\n\nĐoạn **quan trọng** của bài.\n\n- ý một\n- ý hai",
  } as never;

  it("renders the markdown body", () => {
    render(<ArticleModal article={article} onClose={() => {}} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tiêu đề bài" })).toBeInTheDocument();
    expect(screen.getByText("quan trọng").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("closes from the button and from Escape", async () => {
    const onClose = vi.fn();
    render(<ArticleModal article={article} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: "Đóng" }));
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
