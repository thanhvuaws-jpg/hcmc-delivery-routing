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

## Dẫn đường khi mất GPS — đừng "đứng im rồi giật" như Google Maps (người dùng nêu 13/11/2026, làm SAU phần train)

- Người dùng: Google Maps khi đi xe hay báo mất GPS, người dùng phải tự mò; lúc có lại thì vị trí giật về chỗ đang đứng → khó chịu. Hỏi dự án có tối ưu được không, "nhưng trước hết phải hoàn thành việc train đã".
- Hướng làm (lợi thế của đề tài: biết tốc độ dự kiến từng cạnh theo giờ / dự báo):
  1. Mất GPS → xe tiếp tục chạy DỌC TUYẾN đã lập theo tốc độ dự kiến từng cạnh (ước vị trí theo quãng đường), có vòng sai số lớn dần, thay vì đứng im.
  2. Có GPS lại → bám vị trí vào đường (map matching trên đồ thị OSM, ưu tiên cạnh thuộc tuyến), kéo mượt về vị trí thật thay vì nhảy.
  3. Bỏ lần đọc GPS có bán kính sai số lớn hoặc nhảy phi lý (vượt tốc độ tối đa của xe máy); lọc làm mượt (Kalman).
  4. Lưu sẵn tuyến + chỉ dẫn trên máy để mất mạng vẫn dẫn được (app Android, QĐ-018).
  5. Android: dùng Fused Location Provider (GPS + Wi-Fi + cảm biến) thay vì chỉ GPS.
- Đánh giá không cần thực địa (QĐ-002): trên web demo đã có xe ảo chạy theo tốc độ thật. Giả lập mất GPS (vd 30–120 s ở đoạn nhà cao tầng / dưới cầu vượt), so độ lệch vị trí: (a) đứng im như Maps, (b) chạy theo tốc độ dự kiến, (c) chạy theo dự báo. Số liệu được thành một mục nhỏ trong báo cáo.

## Cảnh báo sửa đường / né làn như Google Maps (người dùng nêu 13/11/2026, làm SAU phần train)

- Người dùng thấy Google Maps nói "đi né qua bên trái vì bên phải đang sửa đường", hỏi app mình làm được không.
- Kiểm dữ liệu sự cố TomTom 29/10–12/11, vùng trung tâm: 20.056 kẹt xe, 103 đóng đường ("Closed"), 14 công trình ("Roadworks; New roadworks layout"), **0 đóng làn (iconCategory 7), 0 mô tả nhắc tới làn**. TomTom ở TP.HCM KHÔNG cho biết làn nào bị sửa.
- Làm được bằng dữ liệu hiện có:
  - cảnh báo "phía trước sửa đường / đóng đường" ở mức ĐOẠN, kèm né (bộ tìm đường đã cấm đường đóng hẳn và tính chậm hơn khi đóng một phần);
  - chỉ thiếu câu báo trên màn hình dẫn đường.
- Né theo làn: cần nguồn mới. Hướng khả thi là **người dùng tự báo**, kiểu Google / Waze:
  1. nút "báo: sửa đường bên trái / phải / cả đường";
  2. lưu kèm vị trí, hướng, giờ, tự hết hạn;
  3. người đi sau tới gần thì nhắc "đi bên trái";
  4. bộ tìm đường cộng phạt.
  - Bản demo ít người dùng nên ít báo cáo; đánh giá bằng giả lập.
  - Số làn đường có sẵn ở OSM (đặc trưng `so_lan` của tầng vàng) cho một phần đường.
- Xe máy len được nên né làn ít gấp hơn ô tô; giá trị chính là an toàn và đỡ bất ngờ.

## Nhập địa chỉ đi / đến, dẫn vào đúng hẻm (người dùng hỏi 13/11/2026)

- Người dùng: cần nhập địa chỉ hiện tại và địa chỉ đến; đi được vào hẻm, tới gần số nhà; "không cần chính xác 100%, chỉ cần cách đó tí, đúng đường đúng hẻm".
- Bằng chứng từ dữ liệu đang có (đo 13/11):
  - Đồ thị có ~7.400 km service + residential, gồm hẻm.
  - 17.637 tên hẻm khác nhau, 97% đúng mẫu "Hẻm <số>[/<số>…] <tên đường>": 10.167 cấp 1, 5.939 cấp 2, 1.014 cấp 3, 76 cấp 4.
  - 2.030 điểm giao hàng thật (Zenodo) trong vùng cách nút đường gần nhất: trung vị 10 m, 84% ≤ 30 m, 95% ≤ 50 m.
- Cách làm (không cần dịch vụ ngoài):
  1. Tách địa chỉ "a/b/c/d Tên đường" → tìm hẻm "Hẻm a/b/c Tên đường"; không có thì lùi "Hẻm a/b …", rồi "Hẻm a …", rồi đường chính. Đích = điểm giữa hoặc đầu hẻm (chưa biết vị trí căn trong hẻm). → đúng hẻm.
  2. Nhà mặt tiền "N Tên đường": đầu các hẻm "Hẻm k Tên đường" là mốc số nhà; nội suy theo cùng dãy chẵn / lẻ giữa hai mốc gần N. → lệch vài chục mét, phải đo.
  3. Tên địa điểm: POI OSM (D16); muốn tốt hơn thì dịch vụ bản đồ Việt Nam (Goong, VietMap… người dùng tự đăng ký khóa).
  4. Bỏ qua phường / quận khi khớp (đổi tên sau sắp xếp hành chính 2025), chỉ dùng để phân biệt tên trùng ("Đường số 13").
- Đánh giá: lấy mẫu địa chỉ hẻm từ chính tên hẻm OSM rồi đo tỉ lệ tìm đúng hẻm; nhà mặt tiền thì so với số nhà OSM nơi có (addr:housenumber), để lại một phần làm mốc kiểm.

## Trợ lý luật giao thông cho shipper — RAG đa nguồn (thầy hướng dẫn gợi ý trong nhóm lớp TTTN, người dùng hỏi 13/11/2026)

> **Đã chốt thành QĐ-030** (thầy: "nếu được thì có thể làm vô"); làm sau khi xong train + chỉnh chu + app. Chi tiết ở QĐ-030.

- Thầy gợi ý đề tài cho các nhóm CHƯA có đề tài (02/11/2026):
  - RAG xử lý ngôn ngữ tự nhiên (y tế, giáo dục, pháp luật), ví dụ "chatbot vi phạm đi ngược chiều, xử phạt bao nhiêu? dựa vào văn bản pháp luật";
  - Video RAG;
  - ML.
  - Kèm chuỗi tutorial RAG Advanced #18–#26 (người dùng tải #25 Multi-source RAG và #26 RAG pháp luật về Downloads).
- Nhóm đã có đề tài (thầy đồng ý 07/11). Người dùng hỏi: có làm thêm được gì không.
- Ý tưởng: module "trợ lý giao thông" trong app, RAG ĐA NGUỒN kiểu #25, có bộ phân luồng câu hỏi:
  - luật / mức phạt → văn bản pháp luật chính thức (luật giao thông đường bộ + nghị định xử phạt hiện hành; chia theo Điều / khoản);
  - tình hình đường → API của dự án (`/tinh-trang`, `/du-bao`, `/tuyen`), cho LLM GỌI API thay vì tự sinh SQL (#25 cảnh báo exec / Text-to-SQL);
  - kết hợp → bản đồ OSM (một chiều, cấm xe máy đã có trong đồ thị) + văn bản luật.
- Ý của #26: luật hay sửa đổi → lưu phiên bản + ngày hiệu lực; trả lời trích Điều / khoản / văn bản kèm miễn trừ "đối chiếu văn bản chính thức".
- Đánh giá: bộ 50–100 câu hỏi thử. Đo phân luồng đúng, tìm đúng điều luật, trả lời đúng (kiểm tay với văn bản).
- AWS: có thể dùng Amazon Bedrock (Knowledge Bases) để phần "AWS" của đề tài chắc hơn. Phải xem giá trước (ngân sách 2 USD).
- Thứ tự đề xuất: xong train → API lên VPS → app → module này là mở rộng ĐẦU TIÊN, trước mất GPS / báo sửa đường. Nên hỏi thầy trước khi làm.
- Video RAG: không hợp, vì đã bỏ camera (QĐ-004).
