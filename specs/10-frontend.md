# 10 — Frontend

## Goal
Next.js app for onboarding, upload, and the dashboard. Vietnamese UI.

## Files
`frontend/app/{page.tsx, onboarding/, upload/, dashboard/[id]/}`, `frontend/components/`, `frontend/lib/api.ts`

## Pages
- `/` — one-line pitch; "Dùng hồ sơ demo" (select from `GET /demo`, then `POST /demo/{id}/load` → dashboard); "Tạo hồ sơ của tôi" → onboarding.
- `/onboarding` — 5 questions from spec 05, one per step; submit → `POST /profiles` → upload.
- `/upload?id=` — link to `/template.csv`; drag-and-drop CSV; on 422 show a table of errors and warnings by row; on success → dashboard.
- `/dashboard/[id]` — tabs:
  1. Tổng quan: stat cards (TWR, VN-Index, chênh lệch, lãi/lỗ đã thực hiện, phí + thuế); line chart portfolio vs VN-Index (rebased to 100); bar charts of weights by symbol and by sector.
  2. Hành vi: one card per tendency (7): value, threshold, status (Bình thường / Cần chú ý / Chưa đủ dữ liệu), "Cách tính" popover with formula and inputs, one small chart (turnover by month; PGR vs PLR; holding days win vs loss).
  3. Báo cáo AI: "Tạo báo cáo" button with loading state; summary; insight cards with self-check question; strengths; limitations; badge "Nội dung do AI tạo" and "Kiểm tra số liệu: đạt / không đạt".
  4. Kiến thức: 3 article cards; open in a modal rendering markdown.
- Footer on every page: "Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư."

## Rules
- Types are generated, not hand-written: `npx openapi-typescript $NEXT_PUBLIC_API_BASE/openapi.json -o lib/api-types.ts`. All API calls go through `lib/api.ts` using those types.
- Number formatting: `Intl.NumberFormat('vi-VN')`; percentages 1 decimal.
- No business logic in the frontend; display what the API returns.

## Acceptance
- Demo flow from `/` to a generated AI report works without typing anything.
- Upload error table shows Vietnamese messages with row numbers.
