# Ý tưởng đề tài

Chưa chốt gì. Mục này ghi các hướng đang bàn. Khi chốt thì chuyển thành quyết định trong `QUYET_DINH.md`.

## Nguồn 1: đoạn chat ChatGPT "Đề tài AWS tốt nghiệp" (người dùng gửi 29/10/2026)

Bản chia sẻ bắt đầu giữa chừng (lượt đầu là câu trả lời của ChatGPT), nên phần người dùng mô tả ý tưởng lớn ban đầu không có trong đó.

Những gì đọc được:

- **Đề tài lớn:** AI dự đoán ùn tắc giao thông + tìm đường cho shipper, dùng AWS và dữ liệu thật.
- **Mở rộng cho môn IoT:** thiết bị dẫn đường riêng gồm màn hình cảm ứng nối ESP32 + module GPS. Người dùng nhập điểm đi/đến, ESP32 gửi qua Wi-Fi tới server, server tính tuyến rồi trả về để vẽ lên màn hình. Không cần camera.
- **Công nghệ ChatGPT gợi ý:** ESP32 viết C++ (Arduino); server Python + FastAPI; bản đồ Leaflet + OpenStreetMap; tìm đường Dijkstra/A*; CSDL PostgreSQL/PostGIS; thời tiết Open-Meteo.
- **Chi phí phần cứng ChatGPT ước:** màn hình 2,8" tích hợp ESP32 khoảng 290k, GPS 130–210k, dây/nguồn/vỏ 100–300k, tổng khoảng 520–800k. ChatGPT khuyên màn hình 3,5–4,3" trở lên, và khuyên làm và thử trên máy trước, ổn rồi mới đưa lên AWS.

## Điểm cần kiểm chứng trước khi chốt

- **Dữ liệu giao thông thật lấy từ đâu, có được phép không.** Tải tự động ảnh camera giao thông từ trang web công cộng chưa chắc hợp lệ. Cần xác định nguồn cụ thể (dữ liệu của người dùng, API có giấy phép, hay dữ liệu lịch sử).
- **ESP32 không vẽ được bản đồ tương tác kiểu Google Maps.** Hướng khả thi: server dựng sẵn ảnh bản đồ + tuyến rồi gửi xuống, ESP32 chỉ hiển thị. Hoặc chọn ESP32-S3 / màn hình lớn hơn.
- **Máy chủ ảnh bản đồ OpenStreetMap có chính sách sử dụng riêng**, không dùng nặng được. Có thể phải tự dựng ảnh bản đồ hoặc dùng nhà cung cấp khác.
- **Chi phí AWS:** đặt AWS Budgets + cảnh báo từ ngày đầu. Chính sách gói miễn phí của AWS đã đổi năm 2025, cần đọc lại điều khoản hiện hành của tài khoản trước khi bật dịch vụ.

## Nguồn 2: người dùng trình bày (29/10/2026) — gộp thành MỘT đề tài

**Tên dự kiến (bản gửi thầy):** Xây dựng hệ thống định tuyến giao thông thông minh cho giao hàng đô thị dựa trên khai phá dữ liệu, học máy và phân tích hình ảnh camera trên nền tảng Hybrid Cloud AWS.

**Vấn đề:** app giao hàng chỉ quan tâm điểm đi, điểm đến. Chúng không xét đường có kẹt không, không dự báo ùn tắc hay thời tiết, và thường chỉ đường xa trong khi có đường gần hơn mà vẫn đúng luật. Ý chính: ngắn nhất ≠ nhanh nhất ≠ tối ưu (khi tính ùn tắc + thời tiết + luật giao thông).

**Các phần:**
1. Dự báo ùn tắc trên các tuyến.
2. Đề xuất đường ngắn nhất và tuyến thay thế tối ưu, ít ùn tắc.
3. Dự báo thời tiết.
4. Phân tích camera trên các tuyến để bổ trợ dự báo.
5. Triển khai Hybrid Cloud AWS.

Thiết bị ESP32 + màn hình (Nguồn 1) là phần cho môn IoT, dùng chung server.

## Đã kiểm chứng (29/10/2026)

- **Camera TP.HCM:** cổng giaothong.hochiminhcity.gov.vn + app "TTGT TP Hồ Chí Minh" (Trung tâm quản lý hầm sông Sài Gòn vận hành). Từ 01/2025 phát hình trực tiếp, tự tô màu ùn tắc đỏ/cam/xanh. Báo chí nêu khoảng 760 đến hơn 1.200 camera. Chưa xin phép thu tự động — cần xin.
- **AWS Free Tier:** tài khoản tạo từ 15/07/2025 nhận 100 USD tín dụng + tối đa 100 USD nữa. Gói Free hết sau 6 tháng hoặc khi hết tín dụng. Tài khoản tạo trước đó giữ chương trình cũ 12 tháng.

## Góp ý của Claude (chờ người dùng phản hồi)

- **Rủi ro số 1 là phạm vi rộng + dữ liệu.** Nên giới hạn 1–2 quận, xe máy, giờ cao điểm.
- **Camera chỉ phủ nút giao, không phủ hẻm.** Tốc độ các đoạn khác phải ước lượng (loại đường + khung giờ). Phải nói rõ trong phương pháp.
- **Cần cách chứng minh "tốt hơn":** sai số thời gian dự báo + chạy thử thực tế vài tuyến (ghi GPS điện thoại), so với đường ngắn nhất / bản đồ thông thường.
- **Luật giao thông:** OSM có một chiều, cấm rẽ, nhưng thiếu giờ cấm, cấm xe máy kiểu VN. Cho phép bổ sung luật thủ công cho khu vực thử.
- **Thời tiết ở TP.HCM = ngập:** danh sách điểm ngập, tránh khi dự báo mưa lớn.
- **Hybrid phải có lý do:** xử lý camera tại chỗ (on-prem), chỉ gửi số liệu đã đếm lên AWS (S3, API định tuyến). Huấn luyện ở máy để khỏi đốt tín dụng.

## Câu hỏi còn mở

- Thực tập ở công ty hay tự làm? Bao lâu? Yêu cầu nộp gì?
- "Dữ liệu thật" ngoài camera công cộng còn nguồn nào (GPS shipper, đơn hàng)?
- Thiết bị IoT có gộp vào đề tài thực tập không, hay chỉ cho môn IoT?
