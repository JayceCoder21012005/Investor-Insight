---
id: herding-lift
title: "Chỉ số lift: nhận diện việc bán theo thị trường chung"
tags: [herding]
level: experienced
---

# Chỉ số lift: nhận diện việc bán theo thị trường chung

Để biết bạn có bán theo đám đông hay không, cần một phép so sánh công bằng: tỷ lệ lệnh bán của bạn rơi vào các phiên thị trường giảm mạnh cao hơn bao nhiêu so với mức ngẫu nhiên? Chỉ số lift trả lời đúng câu hỏi đó.

## Định nghĩa

Gọi một phiên là phiên giảm mạnh nếu VN-Index giảm từ mức ngưỡng trở lên trong ngày. Hệ thống cũng tính phiên liền sau, vì phản ứng của nhà đầu tư thường chậm một nhịp. Khi đó:

lift = (tỷ lệ lệnh bán rơi vào các phiên này) chia cho (tỷ lệ các phiên này trong toàn bộ giai đoạn)

Lift bằng 1 nghĩa là bạn bán đúng như kỳ vọng ngẫu nhiên. Lift lớn hơn 1 nghĩa là các lệnh bán dồn vào những phiên đó nhiều hơn bình thường.

## Ví dụ tính tay

Giai đoạn có 9 phiên, trong đó có 2 phiên thuộc nhóm giảm mạnh (phiên giảm và phiên kế tiếp). Bạn có 4 lệnh bán, 2 lệnh rơi vào hai phiên đó.

- Tỷ lệ lệnh bán trong các phiên đó: 2/4 = 0,5.
- Tỷ lệ các phiên đó trong giai đoạn: 2/9, xấp xỉ 0,22.
- lift = 0,5 chia 0,22, xấp xỉ 2,25.

## Cách đọc và giới hạn

Ngưỡng đề xuất ban đầu để đánh dấu tín hiệu là lift từ 2 trở lên, và chỉ áp dụng khi có đủ số lệnh bán.

Có vài điều cần thận trọng khi diễn giải:

- **Lệnh bán dồn trong vài ngày.** Nếu bạn bán nhiều mã cùng một ngày, nhiều lệnh có thể dồn vào cùng một phiên và làm lift cao hơn thực chất. Việc đếm theo lệnh, không theo ngày, khiến chỉ số nhạy với điều này.
- **Số phiên giảm mạnh ít.** Mẫu nhỏ làm lift biến động mạnh; thêm hay bớt một phiên có thể đổi kết quả.
- **Nguyên nhân đúng.** Lift cao cho thấy sự trùng thời điểm, chưa cho thấy lý do. Bạn có thể đã bán vì nhu cầu tiền mặt hoặc vì quy tắc cắt lỗ đặt từ trước.
- **Dữ liệu mô phỏng.** Kiểm chứng trên dữ liệu mô phỏng chỉ cho biết công thức hoạt động đúng với đặc tả.

## Câu hỏi tự kiểm tra

1. Lift của tôi thay đổi thế nào nếu chỉ tính phiên giảm mà không tính phiên liền sau?
2. Các lệnh bán trong phiên giảm mạnh có cùng một lý do hay khác nhau?
3. Sau những lần bán đó, giá các mã này diễn biến ra sao so với lúc tôi bán, và tôi có đang nhìn lại kết quả một cách công bằng không?

Chỉ số này chỉ mô tả mối quan hệ giữa thời điểm bán và biến động thị trường chung, không phải khuyến nghị về cách giao dịch.
