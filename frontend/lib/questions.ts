// The five risk-questionnaire questions (spec 05). Answer values 1-4 map to the options in order.
export type Question = { prompt: string; options: [string, string, string, string] };

export const QUESTIONS: Question[] = [
  { prompt: "Thời gian dự định đầu tư", options: ["Dưới 1 năm", "1–3 năm", "3–5 năm", "Trên 5 năm"] },
  { prompt: "Kinh nghiệm đầu tư chứng khoán", options: ["Dưới 1 năm", "1–3 năm", "3–5 năm", "Trên 5 năm"] },
  { prompt: "Danh mục giảm 20% trong một tháng, bạn sẽ", options: ["Bán hết", "Bán bớt", "Giữ nguyên", "Mua thêm"] },
  { prompt: "Mục tiêu chính của bạn", options: ["Bảo toàn vốn", "Thu nhập ổn định", "Tăng trưởng", "Tăng trưởng mạnh"] },
  { prompt: "Mức lỗ tối đa chấp nhận trong một năm", options: ["Dưới 5%", "5–15%", "15–30%", "Trên 30%"] },
];
