---
id: concentration-hhi
title: "Đọc chỉ số HHI: đo mức tập trung của danh mục"
tags: [concentration]
level: experienced
---

# Đọc chỉ số HHI: đo mức tập trung của danh mục

HHI (Herfindahl-Hirschman Index) ban đầu được dùng để đo mức độ tập trung của một thị trường. Áp dụng cho danh mục, nó cho biết giá trị của bạn dồn vào ít hay nhiều mã.

## Công thức

Với tỷ trọng giá trị thị trường w của từng mã tại thời điểm cuối kỳ:

HHI = tổng của w bình phương

Vì bình phương làm phóng đại các tỷ trọng lớn, HHI nhạy hơn với một mã áp đảo so với việc chỉ đếm số mã.

## Ví dụ tính tay

- Danh mục 5 mã chia đều, mỗi mã 20%: HHI = 5 × 0,04 = 0,20.
- Danh mục ba mã với tỷ trọng 50%, 30%, 20%: HHI = 0,25 + 0,09 + 0,04 = 0,38.
- Một mã duy nhất: HHI = 1.

Giá trị nhỏ nhất là 1/n khi n mã chia đều. Vì thế một danh mục 4 mã chia đều đã có HHI là 0,25 và không thể thấp hơn mức đó, dù được phân bổ hoàn hảo.

## Cách đọc trong Investor Insight

Hệ thống đánh dấu tín hiệu tập trung khi HHI vượt 0,25 hoặc một mã chiếm hơn 40% danh mục. Đây là ngưỡng đề xuất ban đầu, được đặt trong tệp cấu hình và sẽ được hiệu chỉnh sau khi chạy đánh giá. Hai chỗ cần lưu ý:

1. **HHI đo tại ngày cuối kỳ.** Nó là ảnh chụp cuối cùng, không phải trung bình cả giai đoạn. Một người giao dịch thường xuyên có thể kết thúc kỳ với vài vị thế và cho HHI cao dù phần lớn thời gian đã đa dạng hơn.
2. **HHI không thấy tương quan.** Năm mã ngân hàng chia đều cho HHI thấp, nhưng chúng thường biến động cùng chiều. Vì vậy báo cáo còn hiển thị tỷ trọng theo ngành.

## So sánh với khẩu vị đã khai báo

Mỗi nhóm khẩu vị rủi ro trong bảng hỏi có một giới hạn HHI riêng, và nhóm thận trọng thấp hơn nhóm tăng trưởng. Khi HHI thực tế vượt giới hạn của nhóm bạn đã chọn, báo cáo ghi nhận tín hiệu lệch khẩu vị. Đó là chênh lệch giữa điều bạn nói về mình và điều danh mục đang thể hiện, không phải lời phán xét.

## Câu hỏi tự kiểm tra

1. HHI của tôi thay đổi thế nào qua từng tháng, và điều gì làm nó tăng?
2. Mức tập trung hiện tại có khớp với khoảng lỗ tối đa tôi chấp nhận không?
3. Nếu loại mã lớn nhất ra, danh mục còn lại có hợp lý không?

Nội dung nhằm giúp bạn đọc đúng một chỉ số, không phải khuyến nghị tái cơ cấu danh mục.
