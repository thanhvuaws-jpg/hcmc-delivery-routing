# Thực tập tốt nghiệp

Thư mục làm đề tài thực tập tốt nghiệp (kỳ sau). Đề tài có dùng dịch vụ AWS và dữ liệu thật.

Đồ án chuyên ngành (Royal Restaurant POS) nằm ở `../doanchuyennganh` và đang **tạm gác**. Khi làm việc ở đây thì không sửa gì bên đó, trừ khi người dùng nói rõ.

## Trước khi bắt tay vào việc

1. Đọc `note/README.md`, rồi tới `note/CAN_NHO.md`.
2. Đọc phần đầu `note/NHAT_KY.md` để biết phiên trước dừng ở đâu.
3. Gặp việc đã có quyết định trong `note/QUYET_DINH.md` thì làm theo quyết định đó. Muốn đổi thì hỏi người dùng rồi ghi quyết định mới, không lặng lẽ làm khác.

## Sau mỗi phiên có thay đổi

- `note/NHAT_KY.md`: thêm một mục mới lên đầu (ngày, làm gì, tệp nào, còn dở gì).
- `note/QUYET_DINH.md`: thêm quyết định mới (lý do, phương án đã bỏ).
- `note/CAN_NHO.md`: thêm bẫy hoặc lỗi vừa gặp, để phiên sau khỏi lặp lại.

## Bí mật

Khóa truy cập AWS, mật khẩu, token, IP máy chủ, chuỗi kết nối CSDL **không bao giờ** được ghi vào tệp trong thư mục này, kể cả `note/`. Dùng `aws configure` / biến môi trường / AWS Secrets Manager. Dữ liệu thật có thông tin cá nhân thì không đưa lên git.
