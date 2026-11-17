---
id: disposition-pgr-plr
title: "PGR và PLR: đo hiệu ứng ngược vị thế như thế nào"
tags: [disposition]
level: experienced
---

# PGR và PLR: đo hiệu ứng ngược vị thế như thế nào

Để biến một cảm giác ("hình như tôi bán lãi sớm hơn bán lỗ") thành con số, Odean (1998) đề xuất so sánh hai tỷ lệ tính trên các ngày có lệnh bán.

## Định nghĩa

Vào mỗi ngày có ít nhất một lệnh bán, xét từng mã đang nắm giữ từ đầu ngày và phân loại:

- **Lãi đã chốt (RG):** mã được bán ở giá cao hơn giá vốn bình quân.
- **Lỗ đã chốt (RL):** mã được bán ở giá thấp hơn giá vốn bình quân.
- **Lãi trên giấy (PG):** mã không bán và giá thấp nhất trong ngày vẫn cao hơn giá vốn.
- **Lỗ trên giấy (PL):** mã không bán và giá cao nhất trong ngày vẫn thấp hơn giá vốn.

Mã có giá vốn nằm giữa giá thấp nhất và cao nhất của ngày không được tính vào bên nào, vì không thể biết nó đang lãi hay lỗ trong ngày đó.

Từ đó:

- PGR = RG / (RG + PG): trong các vị thế đang lãi, bao nhiêu phần được chốt.
- PLR = RL / (RL + PL): trong các vị thế đang lỗ, bao nhiêu phần được cắt.
- DE = PGR − PLR.

## Ví dụ tính tay

Một ngày bán có ba vị thế: A bán với giá cao hơn giá vốn, B không bán và đang lãi trên giấy, C không bán và đang lỗ trên giấy. Khi đó RG = 1, PG = 1, RL = 0, PL = 1. PGR = 1/2 = 0,5, PLR = 0/1 = 0 và DE = 0,5.

## Cách đọc

DE dương cho thấy bạn chốt lãi thường xuyên hơn cắt lỗ. Trong nghiên cứu gốc trên 10.000 tài khoản, PGR khoảng 0,148 và PLR khoảng 0,098, tức chênh lệch khoảng 0,05. Investor Insight dùng ngưỡng đề xuất ban đầu là DE lớn hơn 0,05, và chỉ kết luận khi có đủ số lệnh bán. Dưới mẫu tối thiểu, hệ thống hiển thị "chưa đủ dữ liệu".

## Những giới hạn cần nhớ

- Giá vốn bình quân gồm cả phí mua, nên một vị thế có thể "lãi" theo giá nhưng "lỗ" theo giá vốn.
- Lý do bán có thể không liên quan đến lãi lỗ, chẳng hạn cần tiền mặt hay cân bằng lại danh mục. Chỉ số không đọc được ý định.
- Với ít lệnh bán, một vài trường hợp đặc biệt có thể làm DE lệch mạnh.
- Dữ liệu mô phỏng chỉ chứng minh công thức chạy đúng đặc tả, không chứng minh hiệu quả trên nhà đầu tư thật.

## Câu hỏi tự kiểm tra

1. DE của tôi có ổn định khi tôi chia dữ liệu thành hai nửa theo thời gian không?
2. Thời gian nắm giữ trung bình của lệnh lãi và lệnh lỗ chênh nhau bao nhiêu ngày?
3. Có lệnh bán nào được thúc đẩy bởi nhu cầu tiền mặt hơn là bởi lãi lỗ?
