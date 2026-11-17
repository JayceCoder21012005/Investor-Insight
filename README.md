# Investor Insight

Ứng dụng web giúp nhà đầu tư cá nhân nhìn lại **hành vi giao dịch của chính mình**: mã Python tính mọi chỉ số bằng công thức cố định và có unit test, AI chỉ diễn giải bằng tiếng Việt, mọi con số AI viết ra đều bị kiểm tra lại với số liệu gốc. Không khuyến nghị mua/bán, không dự báo giá.

Đề tài thực tập: "Phân tích hành vi nhà đầu tư (Investor Insight)" tại DSC – Chi nhánh Đà Nẵng. Kế hoạch ở `contexts/`, đặc tả kỹ thuật ở `specs/`.

> **Lưu ý trung thực.** Dữ liệu giao dịch là **mô phỏng** (11 hồ sơ có nhãn hành vi). Giá cổ phiếu là **giá thật đã điều chỉnh** của VNINDEX và 20 mã, 247 phiên từ 03/11/2025 đến 30/10/2026, lấy từ API biểu đồ công khai của VNDIRECT (`backend/data/SOURCE.json` ghi `simulated: false`). Thư viện `vnstock` trong đặc tả không còn trên PyPI. Tự cài hành vi rồi tự phát hiện chỉ chứng minh mã chạy đúng đặc tả, không chứng minh hiệu quả trên nhà đầu tư thật.

## Luồng xử lý

```
CSV lệnh + bảng hỏi khẩu vị
   │ validate (từng dòng, tiếng Việt)      backend/app/core/validate.py
   ▼
phí/thuế → sổ lệnh (giá vốn bình quân) → danh mục & lợi suất TWR   core/{fees,ledger,portfolio}.py
   ▼
chỉ số hành vi (HHI, vòng quay, PGR/PLR, mua đuổi, lift…)          core/metrics.py
   ▼
cờ cảnh báo + kiểu nhà đầu tư (theo quy tắc, ngưỡng ở YAML)        core/flags.py, config/thresholds.yaml
   ▼
LLM diễn giải ──► guardrail (schema, khớp số, chặn khuyến nghị, độ phủ) ──► thử lại 1 lần ──► mẫu câu viết sẵn
   ▼                                                                         ai/{report,guardrails,templates}.py
Next.js: tổng quan · hành vi · báo cáo AI · kiến thức               frontend/
```

Nguyên tắc: `backend/app/core` là hàm thuần (không DB, HTTP, LLM); mọi con số hiển thị đến từ đó; mọi ngưỡng nằm trong `backend/config/thresholds.yaml`.

## Chạy trên máy

Yêu cầu: Python 3.11 + [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# Backend
cd backend
cp .env.example .env                  # điền khóa; giá trị KHÔNG đặt trong dấu nháy
uv sync
uv run python scripts/fetch_prices.py --source VNDIRECT  # giá thật; --synthetic để dùng giá mô phỏng khi không có mạng
uv run python scripts/generate_personas.py --seeds 3
uv run alembic upgrade head           # dùng DATABASE_URL_DIRECT (suy ra từ DATABASE_URL nếu để trống)
uv run uvicorn app.main:app --reload  # http://localhost:8000/docs

# Frontend (terminal khác)
cd frontend
cp .env.example .env.local
npm install
npm run dev                           # http://localhost:3000
```

LLM: đặt **một** trong `GEMINI_API_KEY` (mặc định `gemini-3.5-flash`, tự chuyển sang `gemini-3.1-flash-lite` rồi `gemini-3.5-flash-lite` khi hết hạn mức; đổi bằng `LLM_FALLBACK_MODELS`) hoặc `LLM_API_KEY` (Anthropic, mặc định `claude-opus-5-5`); `LLM_MODEL` ghi đè model. Báo cáo dự phòng sinh ra vì lỗi API không được lưu đệm, nên sẽ tự sinh lại khi API hoạt động. Không có khóa thì mọi chức năng vẫn chạy trừ "Tạo báo cáo AI" (trả 503 kèm thông báo).

Chạy thử không cần khóa và không cần Neon: `uv run python scripts/e2e_server.py` (SQLite tạm + LLM thay thế trả văn bản mẫu, có ghi rõ tên).

## Kiểm thử

```bash
cd backend  && uv run pytest              # core, API, AI, eval, personas (SQLite; không bao giờ chạm .env)
cd frontend && npm test && npm run typecheck && npm run lint && npm run build
cd backend  && uv run python scripts/run_eval.py --runs 3        # cần khóa LLM; --skip-llm để bỏ phần AI
```

`npm run gen:api` sinh lại `frontend/lib/api-types.ts` từ OpenAPI của backend.

## Kết quả đánh giá

Xem `eval/results.md` (sinh từ `eval/results.json`, giữ lần chạy "Trước hiệu chỉnh"). Ngày chạy, mô hình, `formula_version` và nguồn giá nằm ở đầu tệp.

Tóm tắt lần chạy 2026-11-17 (33 tệp tổng hợp P01–P11 × 3 seed, `formula_version 0.3`, **giá thật** VNDIRECT):

| Khuynh hướng | Precision | Recall | Trước (0.2, giá mô phỏng) |
|---|---|---|---|
| overtrading | 100% | 83% | 55% / 100% |
| concentration | 43% | 100% | 29% / 67% |
| disposition | 67% | 100% | 75% / 100% |
| chasing | 100% | 67% | 100% / 67% |
| herding | 100% | 100% | 100% / 100% |
| risk_mismatch | 50% | 100% | 33% / 100% |
| overconfidence | 100% | 80% | 0% (chưa có quy tắc nhãn) |

Thay đổi từ 0.2 lên 0.3:

- Sửa hai lỗi của bộ sinh persona: P08 bỏ sót các mã giá cao vì không đủ tiền mua 1 lô; P07 bị mua đuổi làm loãng mã chính.
- Biến động của `risk_mismatch` giờ so với VN-Index cùng kỳ (`vol_ratio_max` 1,3/1,6/2,0), thay cho ngưỡng tuyệt đối.
- `hhi_max` của nhóm thận trọng tăng từ 0,20 lên 0,25.
- Tháng "tăng đột biến" phải tự vượt `monthly_warn`.
- Nhãn `overconfidence` là nhãn phái sinh: có nhãn `overtrading` và lợi suất thấp hơn VN-Index.

Các ngưỡng này được chỉnh trên chính bộ persona dùng để đo, nên số liệu có phần lạc quan.

AI bám số liệu (`gemini-3.1-flash-lite`, 33 tệp × 3 lần = 99 báo cáo, 0 lỗi API): qua guardrail ngay lần đầu **95%**, sau một lần thử lại **98%**; 2 báo cáo phải dùng mẫu câu thay thế cho phần lỗi. Lỗi ở lần đầu: 3 `number_not_found` (một trong số đó là guardrail đọc nhầm "0,4139 tỷ trọng" thành 0,4139 tỷ đồng; lỗi đọc này đã sửa sau lần đo), 1 `advice`, 1 `schema`. Thời gian sinh p50 2,8 s, lớn nhất 41,6 s.

Trước khi sửa prompt, lần đầu chỉ đạt 55%. Đối chiếu từng vi phạm cho thấy guardrail chặn đúng: một số không có trong số liệu (40%), và hai số có thật nhưng không được khai trong `evidence_keys`. Mẫu vi phạm nằm ở `ai.violation_examples` trong `eval/results.json`.

Khóa Gemini miễn phí có hạn mức theo ngày cho từng model, nên mỗi tệp mới chạy 1 lần chứ chưa chạy nhiều lần. Backend tự chuyển sang model nhẹ hơn khi model chính hết hạn mức (`LLM_FALLBACK_MODELS`).

## Giới hạn

- Dữ liệu giao dịch mô phỏng (giá thì là giá thật). Nguồn VNDIRECT là API công khai không chính thức, có thể đổi hoặc chặn; `--synthetic` là phương án dự phòng.
- Giá điều chỉnh; chưa xử lý cổ tức và chia tách cổ phiếu.
- HHI đo tại ngày cuối kỳ (đã thử bình quân theo thời gian: không tốt hơn). Cờ `concentration` vẫn bật trên P01/P05, vốn thực sự chỉ giữ 2–4 mã nhưng không được gắn nhãn tập trung.
- Khảo sát 5 người dùng chỉ mang tính tham khảo và nhập tay ở mục 4 của `eval/results.md`.
- Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư.

## Triển khai

1. Neon: `uv run alembic upgrade head` với `DATABASE_URL_DIRECT` trên nhánh `main`.
2. Backend: `docker build -t investor-insight-backend backend` (Dockerfile dựng bằng uv; đã build và smoke test với SQLite và với Neon thật: health, nạp demo, metrics, bài viết). Biến môi trường: `DATABASE_URL` (pooled), `GEMINI_API_KEY` hoặc `LLM_API_KEY`, `LLM_MODEL`, `CORS_ORIGIN`. Giá và bài viết nằm sẵn trong image.
3. Frontend: triển khai Next.js với `NEXT_PUBLIC_API_BASE` trỏ tới backend (giá trị được nhúng lúc build).
4. Smoke test: `/api/health`, nạp hồ sơ demo P03, tạo báo cáo.

## Cấu trúc

```
backend/   app/{core,ai,api}, config/thresholds.yaml, content/articles (20 bài), data/, migrations/, scripts/, tests/
frontend/  Next.js (App Router, TypeScript, Tailwind, Recharts)
eval/      results.json, results.md, baseline.json
specs/     đặc tả kỹ thuật; contexts/ kế hoạch MVP và tài liệu thực tập
```
