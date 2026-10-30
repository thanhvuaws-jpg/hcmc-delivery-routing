# Dữ liệu chép tay

Dữ liệu không tải tự động được (nằm trong ảnh, văn bản). Chép một lần, lưu trong git vì không tải lại được.

## ngap_pc08_2026-10-06.csv — D8 điểm nguy cơ ngập TP.HCM

- **Nguồn:** danh sách cảnh báo của Phòng CSGT (PC08) Công an TP.HCM, qua infographic trong bài Tiền Phong ngày 06/10/2026 ("122 điểm có nguy cơ ngập tại TPHCM, CSGT cảnh báo 'khẩn'").
  - Ảnh ghi: "Danh sách nguy cơ ngập, không phản ánh tình trạng ngập theo thời gian thực".
- **Chép:** 30/10/2026, Claude đọc ảnh gốc (1390×6338 px) theo 8 phần + soi các mép cắt.
  - Đủ 83 điểm do mưa (stt 1–83) + 39 điểm do triều cường (stt 84–122).
  - Mỗi gạch đầu dòng con trong ảnh là một điểm, giữ đúng thứ tự trong ảnh.
- **Cột:**
  - `duong`: đường chính.
  - `giao`: đường giao, nhiều đường thì cách nhau bằng `;`.
  - `tu`, `den`: hai đầu đoạn, chỉ khi là tên đường.
  - `khu_vuc`: phường/xã nếu ảnh ghi.
  - `mo_ta`: nguyên văn dòng trong ảnh.
- **Suy luận thêm (ghi rõ trong mo_ta / khu_vuc):**
  - stt 2 "Ngã tư Bảy Hiền": nút Lý Thường Kiệt – Cách Mạng Tháng Tám – Hoàng Văn Thụ – Trường Chinh.
  - stt 78–83: thuộc nhóm Bà Rịa – Vũng Tàu cũ theo thứ tự trong danh sách. Không ghép vào đường cùng tên ở TP.HCM cũ (Nguyễn An Ninh, Trương Công Định…).
- Ghép vào cạnh đồ thị: `xu_ly/bac_ngap.py`.
