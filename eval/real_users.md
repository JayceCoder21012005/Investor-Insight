# Đánh giá trên dữ liệu giao dịch thật của 5 người dùng

Ngày chạy: 21/11/2026 · `formula_version` 0.3 · Giá VNDIRECT (dchart, giá điều chỉnh) 01/11/2025 – 20/11/2026 · Mô hình AI: gemini-3.5-flash-lite (tự chuyển sang từ chuỗi dự phòng)

Người dùng được ẩn danh thành U1–U5. Người dùng thật không làm bảng hỏi khẩu vị rủi ro, nên cả 5 người được gán cùng bộ trả lời mặc định `[2, 2, 3, 3, 2]`, tức mức **Cân bằng**. Số liệu chi tiết nằm ở `eval/real_users.json`. Script chạy lại nằm ở `backend/scripts/real_users/`.

## 1. Mô tả dữ liệu

| Người dùng | Số lệnh | Mua / Bán | Giai đoạn | Số mã | Mã giao dịch | Đặc điểm tệp |
|---|---|---|---|---|---|---|
| U1 | 8 | 8 / 0 | 01/04 – 18/11/2026 | 6 | DXG, DIG, FPT, HPG, VCB, MBB | Giá có dấu phẩy ngăn cách hàng nghìn |
| U2 | 10 | 8 / 2 | 06/04 – 18/11/2026 | 7 | VCB, HPG, MWG, VNM, SSI, PNJ, GAS | Giá có dấu phẩy ngăn cách hàng nghìn |
| U3 | 17 | 17 / 0 | 09/09 – 10/11/2026 | 3 | MBB, BID, VIW | Lệnh xếp từ mới đến cũ |
| U4 | 9 | 9 / 0 | 09/03 – 12/10/2026 | 4 | MBB, TCB, TPB, PNJ | Lệnh xếp từ mới đến cũ |
| U5 | 9 | 6 / 3 | 21/07 – 05/11/2026 | 7 | MBB, HPG, SSI, FPT, TCB, MWG, PNJ | Có dòng trống cuối tệp; 3 lệnh bán mã chưa mua trong tệp |

## 2. Kết quả kiểm tra dữ liệu đầu vào

Vòng 1 dùng dữ liệu giá hiện có của hệ thống: 20 mã, đến 31/10/2026. Vòng 2 bổ sung giá đến 20/11/2026 và 5 mã còn thiếu (BID, TPB, DXG, DIG, VIW).

| Người dùng | Vòng 1: kết quả | Lý do bị từ chối | Vòng 2: kết quả | Cảnh báo giá lệch (±5%) |
|---|---|---|---|---|
| U1 | Từ chối | Mã DXG, DIG ngoài danh mục; 1 lệnh sau 31/10 | **Chấp nhận** | 3 |
| U2 | Từ chối | 1 lệnh sau 31/10 | **Chấp nhận** | 0 |
| U3 | Từ chối | Mã BID, VIW ngoài danh mục; 5 lệnh tháng 11 (14 lỗi) | **Chấp nhận** | 0 |
| U4 | Từ chối | Mã TPB ngoài danh mục | **Chấp nhận** | 8 |
| U5 | Từ chối | 3 lệnh bán mã không có lệnh mua trước đó; 1 lệnh sau 31/10 | Từ chối (3 lỗi bán vượt số đang giữ) | 4 |

Nhận xét:

- Các định dạng khác nhau đều được đọc đúng: dấu phẩy ngăn cách hàng nghìn, lệnh xếp ngược thời gian, dòng trống cuối tệp.
- Hệ thống chặn đúng các lệnh bán không có vị thế (U5) thay vì âm thầm tính sai.
- Để phân tích được U5, 3 lệnh bán đó (dòng 2, 3, 7) được loại thủ công, ngoài hệ thống. Kết quả của U5 vì vậy chỉ phản ánh các lệnh còn lại.
- Cảnh báo giá lệch có tỷ lệ rất đều theo từng mã: MBB khoảng 1,25 lần, TCB khoảng 1,5 lần, FPT khoảng 1,1 lần. Đây là dấu hiệu của **giá điều chỉnh sau chia cổ phiếu thưởng hoặc cổ tức bằng cổ phiếu**, không phải người dùng nhập sai. Ví dụ, giá MBB ngày 01/04 trong dữ liệu là 21.225 đồng, không đúng bước giá 50 đồng của HOSE.

## 3. Ảnh hưởng của giá điều chỉnh

Lệnh thật dùng giá danh nghĩa, còn dữ liệu giá đã điều chỉnh. Tệp CSV cũng không ghi số cổ phiếu thưởng người dùng nhận được. Hai điều này khiến lãi/lỗ của các lệnh cũ bị tính thấp hơn thực tế.

- **Bản thô:** giữ nguyên giá lệnh.
- **Bản quy đổi:** lệnh nằm ngoài khoảng giá phiên ±5% được đưa về giá đóng cửa đã điều chỉnh, và khối lượng được nhân tương ứng để giữ nguyên giá trị lệnh.

| Người dùng | Số lệnh được quy đổi | Lợi suất TWR (thô) | Lợi suất TWR (quy đổi) | Lãi/lỗ (thô) | Lãi/lỗ (quy đổi) |
|---|---|---|---|---|---|
| U1 | 3 / 8 | -36,0% | -29,2% | -10.728.824 đ | -9.062.794 đ |
| U2 | 0 / 10 | -15,4% | -15,4% | -3.397.377 đ | -3.397.377 đ |
| U3 | 0 / 17 | -20,2% | -20,2% | -8.944.030 đ | -8.944.030 đ |
| U4 | 8 / 9 | -46,4% | **-8,0%** | -10.867.061 đ | -3.157.492 đ |
| U5 | 3 / 6 | -33,5% | **-8,2%** | -6.492.693 đ | -3.191.153 đ |

U2 và U3 chỉ có lệnh gần đây nên hai bản trùng nhau, đúng như kỳ vọng. Lãi/lỗ bản thô cũng được đối chiếu với một phép tính tay độc lập (giá trị nắm giữ hiện tại cộng dòng tiền) và khớp đến từng đồng ở cả 5 người. Như vậy bộ tính toán đúng; sai lệch chỉ đến từ cơ sở giá. **Các bảng sau dùng bản quy đổi.**

## 4. Chỉ số danh mục (bản quy đổi)

| Người dùng | Vốn mua | Lãi/lỗ trên vốn | TWR | VN-Index cùng kỳ | Chênh lệch | Biến động năm (danh mục / VN-Index) | HHI | Mã lớn nhất | Ngành lớn nhất | Lệnh / tháng | Phân loại |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U1 | 49,3 tr | -18,4% | -29,2% | -0,8% | -28,4 điểm % | 27,7% / 16,5% | 0,21 | FPT 36% | Công nghệ 36% | 1,00 | Cân bằng |
| U2 | 35,4 tr | -9,6% | -15,4% | +0,8% | -16,3 điểm % | 21,1% / 16,7% | 0,22 | GAS 31% | Năng lượng 31% | 1,25 | Nắm giữ dài hạn |
| U3 | 62,8 tr | -14,2% | -20,2% | -7,6% | -12,7 điểm % | 20,4% / 14,4% | 0,35 | BID 45% | Ngân hàng 72% | 5,67 | Tập trung |
| U4 | 41,8 tr | -7,6% | -8,0% | +2,2% | -10,1 điểm % | 21,5% / 17,9% | 0,61 | MBB 77% | Ngân hàng 97% | 1,00 | Tập trung |
| U5 | 31,8 tr | -10,0% | -8,2% | -2,4% | -5,8 điểm % | 22,3% / 16,8% | 0,25 | MBB 34% | Ngân hàng 57% | 1,20 | Cân bằng |

TWR (lợi suất theo thời gian) loại bỏ ảnh hưởng của việc nạp thêm tiền. Vì vậy TWR khác "lãi/lỗ trên vốn" khi người dùng mua rải rác: các khoản lỗ ở giai đoạn đầu, khi vốn còn nhỏ, có trọng số lớn hơn.

## 5. Khuynh hướng hành vi được phát hiện

Ký hiệu: **⚠** = cảnh báo · **–** = không có dấu hiệu · **?** = chưa đủ dữ liệu (dưới 10 lệnh mua hoặc dưới 10 lệnh bán).

| Người dùng | Giao dịch quá nhiều | Tập trung danh mục | Chốt lời sớm, giữ lỗ lâu | Mua đuổi | Bán theo đám đông | Lệch khẩu vị rủi ro | Tự tin thái quá |
|---|---|---|---|---|---|---|---|
| U1 | – | – | ? | ? | ? | ⚠ biến động 27,7% > 1,6 × 16,5% | – |
| U2 | – | – | ? | ? | ? | – | – |
| U3 | – | ⚠ HHI 0,35; BID 45% | ? | – (0/17 lệnh mua đuổi) | ? | ⚠ HHI 0,35 > 0,30 | – |
| U4 | – | ⚠ HHI 0,61; MBB 77% | ? | ? | ? | ⚠ HHI 0,61 > 0,30 | – |
| U5 | – | – (HHI 0,246, sát ngưỡng 0,25) | ? | ? | ? | – | – |

Nhận xét:

- Kết quả khớp với những gì đọc được trực tiếp từ dữ liệu. U3 và U4 dồn vốn vào nhóm ngân hàng (72% và 97%). Không ai giao dịch dày: vòng quay mỗi tháng đều dưới 10%, xa ngưỡng 100%.
- Với mẫu nhỏ (8–17 lệnh, nhiều nhất 2 lệnh bán), các khuynh hướng cần nhiều lệnh bán được báo **"chưa đủ dữ liệu" ở 5/5 người**, thay vì đưa ra kết luận thiếu căn cứ. Đây đúng là hành vi đã thiết kế.
- **Độ nhạy với cơ sở giá:** ở bản thô, U5 bị gắn thêm "Tập trung" (HHI 0,2505) và "Lệch khẩu vị rủi ro" (biến động 41,7%). Cả hai biến mất ở bản quy đổi. Những cờ nằm sát ngưỡng nên được đọc cùng con số thực tế.

## 6. Báo cáo AI

Mỗi người dùng được tạo 3 báo cáo, tổng cộng 15 báo cáo. Chỉ các chỉ số được gửi tới mô hình, không gửi tên hay tệp gốc.

| Tiêu chí | Kết quả |
|---|---|
| Lỗi gọi API | 0 / 15 |
| Qua guardrail ngay lần đầu | **15 / 15 (100%)** |
| Qua guardrail sau thử lại | 15 / 15 (100%) |
| Số liệu không có trong chỉ số (`number_not_found`) | 0 |
| Lời khuyên mua/bán (`advice`) | 0 |
| Nhận định khớp đúng các cờ hệ thống phát hiện | 15 / 15 |
| Độ trễ trung vị / lớn nhất | 6,8 giây / 39,8 giây |

Đánh giá chất lượng câu chữ (đọc thủ công):

| Khía cạnh | Đánh giá | Ví dụ |
|---|---|---|
| Đúng số liệu, không khuyên đầu tư | Đạt | Mọi con số đều có trong chỉ số; câu hỏi tự vấn dạng "Bạn có thoải mái với mức dao động…?" |
| Dễ hiểu với nhà đầu tư cá nhân | **Chưa đạt** | Cả 15/15 báo cáo dùng tên biến kỹ thuật (`n_sells`, `vol_annual`, `benchmark_vol`) và 13/15 báo cáo dùng số thập phân thô ("HHI đạt 0.2121", "tỷ trọng 0.7666") thay vì phần trăm |
| Mạch lạc | Có lỗi nhỏ | U1: "số lệnh mua n_sells tương ứng n_buys" |
| Phần "Điểm mạnh" | Đôi khi gượng | U5: coi việc tập trung vào ngân hàng là điểm mạnh |
| Phần "Giới hạn" | Chưa phù hợp | Ghi "dữ liệu do người dùng cung cấp hoặc mô phỏng" dù đây là dữ liệu thật |

Guardrail đảm bảo **tính trung thực** (không bịa số, không khuyên mua bán), nhưng chưa kiểm tra **tính dễ đọc**.

## 7. Phát hiện và đề xuất

| # | Phát hiện | Mức ảnh hưởng | Đề xuất |
|---|---|---|---|
| 1 | Dữ liệu giá giới hạn ở 20 mã và cố định đến 31/10, nên cả 5/5 người dùng thật bị từ chối ở lần đầu | Cao | Cập nhật giá định kỳ (hằng ngày); mở rộng danh mục mã, ưu tiên mã phổ biến như BID và TPB |
| 2 | Giá điều chỉnh làm sai lợi suất các lệnh cũ tới 38 điểm % (U4: -46,4% so với -8,0%) | Cao | Dùng giá chưa điều chỉnh kèm lịch sự kiện quyền, hoặc tự quy đổi giá lệnh về cùng cơ sở như bản quy đổi ở mục 3 |
| 3 | Lịch sử bị cắt (bán mã mua trước kỳ) là tình huống thường gặp với dữ liệu thật | Trung bình | Cho người dùng khai báo số dư đầu kỳ (mã, khối lượng, giá vốn) |
| 4 | Mẫu nhỏ: 3/7 khuynh hướng "chưa đủ dữ liệu" ở cả 5 người | Thấp (đúng thiết kế) | Khuyến khích tải lịch sử dài hơn (12 tháng trở lên) |
| 5 | Khẩu vị rủi ro được giả định, không lấy từ bảng hỏi thật | Trung bình | Thu thập bảng hỏi khi khảo sát người dùng |
| 6 | Báo cáo AI dùng tên biến và số thập phân thô | Trung bình | Đổi tên khóa thành nhãn tiếng Việt trước khi gửi cho mô hình; thêm quy tắc định dạng phần trăm trong prompt; thêm kiểm tra "không chứa tên biến" vào guardrail |

## 8. Hạn chế của đợt đánh giá

- Mẫu chỉ có 5 người, mỗi người 8–17 lệnh, trong 3–9 tháng. Kết quả mang tính minh họa, không đại diện thống kê.
- Không có nhãn chuẩn (ground truth) về hành vi của người dùng thật, nên không tính được precision/recall như với bộ persona tổng hợp. Mục 5 được đối chiếu bằng cách đọc trực tiếp dữ liệu.
- Bản quy đổi giá là xấp xỉ: lệnh lệch dưới 5% (ví dụ cổ tức tiền mặt nhỏ) không được quy đổi.
- U5 được phân tích sau khi loại 3 lệnh bán ngoài hệ thống.
