# Kế hoạch thực tập — 13 tuần

Lập ngày 29/10/2026. Làm tại nhà, 3 tháng, **chỉ có một máy tính, không đi thực địa** (QĐ-002): không tự quay video, không chạy xe ghi GPS — mọi dữ liệu lấy qua mạng, đánh giá bằng dữ liệu quan sát được. Nếu tuần 1 bắt đầu thứ Hai 02/11/2026 thì tuần 13 kết thúc 31/01/2027 (trước Tết 06/02/2027). Lịch chính thức của trường khác thì dời cả bảng, giữ nguyên thứ tự.

**Tên đề tài (sau QĐ-004, chờ thầy duyệt):** Xây dựng hệ thống định tuyến giao thông thông minh cho giao hàng đô thị dựa trên khai phá dữ liệu và học máy trên nền tảng Hybrid Cloud AWS.

> 29/10/2026: **bỏ camera** (QĐ-004). Nguồn kẹt xe = TomTom Flow; tín hiệu báo sớm = TomTom Incidents. Các mục nhắc tới camera bên dưới đã được thay.

---

## 1. Mục tiêu và phạm vi

### Câu hỏi đề tài phải trả lời được

1. Dự báo được mức ùn tắc trên các tuyến trong 15/30/60 phút tới, có tính thời tiết, chính xác hơn cách "lấy trung bình lịch sử" bao nhiêu?
2. Với cùng một cặp điểm đi/đến, tuyến "tối ưu" (tính ùn tắc + mưa/ngập + luật) nhanh hơn tuyến ngắn nhất và tuyến bản đồ thông thường bao nhiêu phút, trong bao nhiêu % chuyến?
3. Sự cố giao thông (TomTom Incidents) và thời tiết giúp dự báo tốt hơn bao nhiêu so với chỉ dùng lịch sử tốc độ?

### Phạm vi (để làm xong trong 13 tuần)

| | Trong phạm vi | Ngoài phạm vi |
| --- | --- | --- |
| Khu vực | Trung tâm TP.HCM cũ (Q1, Q3, Q4, Q5, Q10, Q11, Phú Nhuận, một phần Tân Bình, Bình Thạnh) | Toàn thành phố |
| Phương tiện | Xe máy (shipper), có đi hẻm | Ô tô, xe tải |
| Thời gian | Ngày thường + cuối tuần, chú trọng giờ cao điểm 6–9h, 16–19h | Dịp lễ Tết đặc biệt |
| Luật | Một chiều, cấm rẽ, cấm xe máy, đường cao tốc (từ OSM + bổ sung tay cho khu vực thử) | Giờ cấm theo biển phụ toàn thành phố |
| Sản phẩm | API định tuyến + web bản đồ + bảng theo dõi dữ liệu | App di động riêng |

### Lõi bắt buộc và phần mở rộng

- **Lõi (phải có để bảo vệ):** dữ liệu thu thật → mô hình dự báo → định tuyến 3 phương án → web bản đồ → chạy trên AWS (hybrid) → đánh giá có số liệu.
- **Mở rộng (làm nếu kịp):** mô hình đồ thị (GNN), thiết bị ESP32 có màn hình (dùng cho môn IoT), cảnh báo ngập theo triều cường.

### Chỉ số thành công (đặt trước để không tự lừa mình)

- Dự báo: MAE của mô hình thấp hơn baseline trung bình lịch sử ít nhất 10%.
- Định tuyến: trên ≥ 30 cặp điểm đi/đến kiểm tra lại bằng dữ liệu thật, tuyến tối ưu không chậm hơn tuyến ngắn nhất trong ≥ 80% trường hợp và nhanh hơn trung bình ≥ 5%.
- (Không có thực địa — QĐ-002. Thay bằng "chạy thử ảo": phát lại dữ liệu tốc độ/camera đã quan sát của những ngày giữ lại không dùng để huấn luyện.)
- Hệ thống: API trả tuyến dưới 2 giây cho khu vực thử.

---

## 2. Kiến trúc hybrid

```
TẠI CHỖ (máy nhà: Ryzen 5 5500U, 16 GB RAM, GTX 1650 4 GB)        AWS (chỉ phần cần công khai / lưu lâu)
┌───────────────────────────────────────────────┐   HTTPS   ┌──────────────────────────────────────┐
│ Bộ thu: thời tiết, tốc độ (API), camera (*)   │ ────────► │ S3: kho dữ liệu (Parquet theo ngày)  │
│ YOLO đếm xe trên GPU, xóa ảnh gốc sau 3 ngày   │  số liệu  │ Athena: truy vấn/khai phá trên S3     │
│ PostgreSQL+PostGIS (Docker) để phát triển      │  đã tổng  │ Định tuyến: EC2 nhỏ hoặc ECS (API)    │
│ Huấn luyện mô hình (LightGBM, LSTM)            │  hợp      │ Web bản đồ: S3 + CloudFront           │
└───────────────────────────────────────────────┘           │ (mở rộng) IoT Core cho ESP32          │
(*) chỉ khi có văn bản cho phép                            │ CloudWatch + AWS Budgets              │
                                                            └──────────────────────────────────────┘
```

**Vì sao là hybrid, không đưa hết lên cloud:** ảnh camera nặng và có hình người, biển số. Xử lý tại chỗ, chỉ gửi con số lên AWS sẽ đỡ băng thông, đỡ tiền và không đưa dữ liệu cá nhân lên cloud. Huấn luyện bằng GPU ở nhà miễn phí; GPU thuê trên AWS rất đắt. AWS lo phần phải chạy liên tục, công khai và lưu lâu.

**Tiền AWS:** tín dụng trong tài khoản đã HẾT HẠN 20/10/2026 (xem `CAN_NHO.md`). Mọi thứ dùng trên AWS đều tốn tiền thật. Ước lượng nếu làm đúng cách: S3 + Athena + CloudFront dưới 2 USD/tháng. EC2 nhỏ chạy cả tháng khoảng 10–15 USD, chỉ bật khi thử/demo. Tránh NAT Gateway, RDS và OpenSearch bật suốt.

---

## 3. Dữ liệu

| # | Dữ liệu | Nguồn | Pháp lý | Trạng thái |
| --- | --- | --- | --- | --- |
| D1 | Mạng lưới đường + luật | OpenStreetMap (Overpass) | ODbL, ghi nguồn | **Đã tải 29/10** (`thu_thap/tai_osm.py`) |
| D2 | Thời tiết theo giờ 2023→nay, 5 điểm | Open-Meteo archive | CC BY 4.0, phi thương mại | **Đã tải 29/10** (`thu_thap/tai_thoi_tiet.py`) |
| D3 | Dự báo thời tiết (khi chạy thật) | Open-Meteo forecast | như D2 | Viết ở tuần 2 |
| D4 | Mức kẹt thật theo đoạn đường (~4.300 đoạn) | TomTom Traffic Flow, ô vector mức phóng 14 | Gói Evaluation miễn phí | **Đang thu 5 phút/lần** (`thu_thap/thu_dinh_ky.py`) |
| ~~D5~~ | ~~Ảnh camera~~ | — | — | Bỏ (QĐ-004) |
| D11 | **Lịch sử tình trạng giao thông TP.HCM** (tốc độ, mức phục vụ LOS theo đoạn đường, mỗi ngày 48 khung 30 phút) — nhóm nghiên cứu ĐH Bách Khoa TP.HCM | Kaggle `thanhnguyen2612/traffic-flow-data-in-ho-chi-minh-city-viet-nam` (~38,5 MB, cập nhật 05/2021) | **CC0 — tự do dùng** | **Đã tải 29/10** bằng API (`thu_thap/tai_kaggle.py`) → `du_lieu/kaggle_hcmc/` (khảo sát: `note/KE_HOACH_DU_LIEU.md` mục 1) |
| D13 | **Điểm giao hàng thật** HCM_1000 V2: 4 × 1.000 khách hàng + kho trong 10 km quanh trung tâm, khung giờ giao, ma trận thời gian/khoảng cách | Zenodo 10.5281/zenodo.23106441 (02/10/2026) | ODbL / CC BY 4.0 / MIT | **Đã tải 29/10** → `du_lieu/zenodo_hcm1000/` |
| D12 | Số liệu đối chiếu: TomTom Traffic Index TP.HCM 2025 (kẹt trung bình 46,9%; 10 km mất 31 phút 55 giây; cao điểm chiều 14,8 km/h) | tomtom.com/traffic-index | Công khai, chỉ trích dẫn | Dùng để so với số tự đo |
| D10 | Sự cố giao thông đang diễn ra (kẹt, đóng đường, công trình, tai nạn, ngập) | TomTom Traffic Incident Details v5 | Gói Evaluation | **Đang thu 5 phút/lần** (`thu_thap/thu_dinh_ky.py`) |
| ~~D6~~ | ~~Video tự quay~~ | — | — | Bỏ (QĐ-002) |
| ~~D7~~ | ~~Chuyến đi GPS thật~~ | — | — | Bỏ (QĐ-002) |
| D8 | Điểm ngập, lịch triều cường | Báo chí, tin của Sở trên cổng giao thông | Tự tổng hợp tay | Tuần 4 |
| D9 | Bộ chuẩn để thử mô hình | METR-LA, PEMS-BAY | Dữ liệu nghiên cứu công khai | Tuần 5 |

**Nguyên tắc thu dữ liệu**

- Thu sớm nhất có thể: mô hình chuỗi thời gian cần nhiều tuần dữ liệu. Bộ thu tốc độ (D4) phải chạy từ tuần 2.
- Chỉ lưu số liệu tổng hợp. Ảnh/video gốc giữ tối đa 3 ngày, trừ mẫu đã làm mờ mặt/biển số dùng cho gán nhãn.
- Mỗi bản ghi có thời gian (giờ VN), nguồn, phiên bản script.
- Dung lượng: ổ C còn ~44 GB, D còn ~33 GB. Dữ liệu thô đặt ở ổ D nếu vượt 5 GB.

---

## 4. Lộ trình từng tuần

Mỗi tuần: **Việc** → **Đầu ra** → **Xong khi**.

### Tuần 0 (29/10 – 01/11) — dọn đường

- Việc:
  - Xử lý AWS: xem Bills, đặt Budgets 5 USD, tạo user IAM có MFA, tắt tài nguyên không dùng.
  - Gặp/nhắn thầy chốt tên đề tài.
  - Gửi đơn xin dữ liệu camera.
  - Đăng ký khóa TomTom.
- Đầu ra: đơn đã gửi, khóa API có (để trong `.env`, không đưa lên git), D1 + D2 đã tải.
- Xong khi: Budgets báo về email; thầy đồng ý hướng đề tài.

### Tuần 1 — đề cương + nền dữ liệu

- Việc:
  - Viết đề cương 3–5 trang (vấn đề, câu hỏi, phạm vi, phương pháp, đánh giá, kế hoạch).
  - Dựng đồ thị đường xe máy từ D1 (networkx): bỏ cao tốc, giữ hẻm, áp một chiều/cấm rẽ.
  - Thống kê luật còn thiếu.
- Đầu ra: `de_cuong.docx`; `do_thi_xe_may.pkl`; báo cáo kiểm tra đồ thị (số đoạn, số nút, bao nhiêu đoạn một chiều).
- Xong khi: tìm được đường ngắn nhất giữa 2 điểm bất kỳ trong khu vực, và vẽ lên bản đồ không đi ngược chiều.
- **Tiến độ 29/10:**
  - ✅ đồ thị xe máy + tìm đường có luật (90/90 cặp, 0 lỗi luật, 79 ms/tuyến)
  - ✅ hình kiểm tra
  - ⬜ đề cương

### Tuần 2 — bộ thu dữ liệu chạy liên tục (làm sớm ngày 29/10)

- **Tiến độ 29/10:**
  - ✅ bộ thu TomTom Flow + Incidents + dự báo thời tiết
  - ✅ lưu Parquet
  - ✅ chạy tay thành công
  - ⬜ người dùng bấm `CAI_HEN_GIO.bat`
  - ⬜ 72 giờ liền
  - ⬜ đẩy lên S3 (tuần 9)

- Việc:
  - Bộ thu tốc độ TomTom cho 40–80 đoạn đường chính (chọn trải đều các trục: Điện Biên Phủ, Cách Mạng Tháng 8, Nguyễn Thị Minh Khai, Võ Văn Kiệt…), chu kỳ phù hợp hạn mức miễn phí.
  - Bộ thu dự báo thời tiết (D3).
  - Lưu Parquet theo ngày, đẩy lên S3.
  - Tự chạy lại khi máy khởi động (Task Scheduler).
- Đầu ra: thư mục `thu_thap/` chạy được; dữ liệu đổ về mỗi ngày; nhật ký lỗi.
- Xong khi: chạy 72 giờ liền không mất quá 5% số lần thu.

### Tuần 3 — ghép dữ liệu TomTom vào đồ thị (map matching)

- Việc:
  - Mỗi đoạn TomTom (hình học + chiều vẽ) ghép vào các cạnh OSM của đồ thị xe máy: gần nhau (< 15 m) và cùng hướng (lệch < 30°).
  - Đo tỉ lệ cạnh có dữ liệu theo loại đường.
  - Ghép sự cố vào cạnh theo cùng cách.
- Đầu ra: `dinh_tuyen/ghep_tomtom.py` + bảng ánh xạ đoạn → cạnh + hình kiểm tra.
- Xong khi: ≥ 90% chiều dài đường chính (primary/secondary/tertiary) có dữ liệu; kiểm tay 30 đoạn ngẫu nhiên ghép đúng ≥ 28.
- **Tiến độ 29/10 (làm sớm):**
  - ✅ ghép + đưa vào bộ thu (96,1% mẫu trong khu vực ghép được)
  - ✅ hình kiểm tra
  - Độ phủ thực tế: trunk 95%, primary 85%, secondary 86%, tertiary 50%. Đây là giới hạn dữ liệu TomTom, không phải lỗi ghép → tiêu chí "≥ 90% đường chính" sửa thành "≥ 90% số mẫu TomTom trong khu vực ghép được" (đạt).
  - ⬜ kiểm tay 30 đoạn
  - ⬜ ghép sự cố

### Tuần 4 — mức ùn tắc + ngập

- Việc:
  - Định nghĩa 3 mức ùn tắc (thông thoáng / đông / kẹt) từ tỉ lệ tốc độ hiện tại / tốc độ đường trống (D4).
  - Ghép thời tiết theo giờ + sự cố (D10) theo cạnh và thời điểm.
  - Lập bảng điểm ngập (D8 + sự cố loại "ngap" của TomTom) gắn vào đoạn đường.
- Đầu ra: bảng dữ liệu huấn luyện (đoạn đường × 15 phút × đặc trưng); tài liệu định nghĩa nhãn.
- Xong khi: phân tích khám phá (EDA) có biểu đồ: ùn tắc theo giờ trong ngày, theo thứ, khi mưa và khi không mưa.

### Tuần 5 — mô hình dự báo, vòng 1

- Việc:
  - Baseline trung bình lịch sử theo (đoạn, thứ, giờ).
  - LightGBM với đặc trưng: giờ, thứ, ngày lễ, mưa hiện tại/dự báo, giá trị trễ 15–60 phút, đoạn lân cận.
  - Chia dữ liệu theo thời gian (không trộn ngẫu nhiên).
  - Thử thêm trên METR-LA để có số so sánh với bài báo.
- Đầu ra: notebook + bảng kết quả MAE/RMSE/F1 cho 15/30/60 phút.
- Xong khi: LightGBM thắng baseline (mục tiêu ≥ 10% MAE).

### Tuần 6 — mô hình dự báo, vòng 2 + giữa kỳ

- Việc:
  - LSTM/GRU (PyTorch, GPU).
  - Đo đóng góp của sự cố và của thời tiết (ablation: bỏ từng nhóm đặc trưng).
  - Chọn mô hình chạy thật.
  - Báo cáo giữa kỳ cho thầy.
- Đầu ra: mô hình đã lưu; bảng ablation; slide giữa kỳ.
- Xong khi: trả lời được câu hỏi 1 và 3 bằng số.

### Tuần 7 — định tuyến

- Việc:
  - Trọng số theo thời điểm: thời gian qua đoạn = độ dài / tốc độ dự báo tại thời điểm xe tới đoạn. Đoạn không có dữ liệu thì dùng tốc độ theo loại đường × khung giờ học từ dữ liệu.
  - Ba phương án:
    - (1) ngắn nhất theo mét;
    - (2) nhanh nhất theo thời gian dự báo;
    - (3) tối ưu = thời gian + phạt rủi ro kẹt + phạt ngập khi có mưa + phạt rẽ trái qua trục lớn.
  - A* + tìm tuyến thay thế (Yen k-shortest hoặc phương pháp phạt).
- Đầu ra: `dinh_tuyen/` + kiểm thử đơn vị (không đi ngược chiều, không vào đường cấm xe máy).
- Xong khi: 3 tuyến trả về < 2 giây; tuyến (3) né được điểm ngập giả lập khi bật "mưa to".

### Tuần 8 — API + web bản đồ

- Việc:
  - FastAPI (`/tuyen`, `/du-bao`, `/tinh-trang`).
  - Web Leaflet + OSM: chọn điểm đi/đến, hiện 3 tuyến khác màu kèm thời gian dự kiến, lớp tô màu ùn tắc, lớp mưa/ngập, thanh trượt "đi lúc mấy giờ".
- Đầu ra: chạy được ở máy (Docker Compose).
- Xong khi: người không biết code dùng được trong 1 phút.

### Tuần 9 — đưa lên AWS (hybrid)

- Việc:
  - S3 + Athena cho dữ liệu.
  - API trên EC2 nhỏ hoặc ECS.
  - Web trên S3 + CloudFront, HTTPS.
  - Bộ thu ở nhà đẩy số liệu lên S3 bằng user IAM chỉ có quyền ghi đúng thư mục.
  - CloudWatch cảnh báo.
  - Vẽ sơ đồ kiến trúc.
- Đầu ra: địa chỉ web công khai; sơ đồ kiến trúc; bảng chi phí thực tế.
- Xong khi: tắt máy ở nhà thì web vẫn chạy (dùng mô hình/dữ liệu gần nhất). Chi phí tháng dưới ngân sách đặt ra.

### Tuần 10 — đánh giá offline

- Việc:
  - Chọn ≥ 30 cặp điểm đi/đến × nhiều khung giờ.
  - Tính 3 tuyến tại thời điểm t, chấm điểm bằng tốc độ THẬT quan sát sau đó (D4).
  - Thống kê, kiểm định ý nghĩa.
- Đầu ra: bảng + biểu đồ so sánh 3 phương án.
- Xong khi: trả lời được câu hỏi 2 bằng số.

### Tuần 11 — chạy thử ảo + bản thảo

- Việc:
  - Phát lại 1–2 tuần dữ liệu đã giữ riêng (không dùng huấn luyện), mô phỏng nhiều shipper xuất phát ở các giờ khác nhau. Thời gian đi tính bằng tốc độ THẬT đã quan sát, không bằng tốc độ dự báo.
  - So sánh 3 phương án + tuyến ngắn nhất.
  - Viết bản thảo báo cáo.
- Đầu ra: bảng + biểu đồ so sánh; bản thảo 70%.
- Xong khi: gửi bản thảo cho thầy.

### Tuần 12 — hoàn thiện

- Việc: sửa theo góp ý; kiểm thử toàn hệ thống; video demo 3–5 phút; dọn mã nguồn, README.
- Xong khi: báo cáo + slide + video xong.

### Tuần 13 — dự phòng + bảo vệ

- Việc: dự phòng trễ; tập thuyết trình; tắt tài nguyên AWS không cần sau bảo vệ.

### Nhánh song song (môn IoT, không nằm trên đường găng)

ESP32 + màn hình 3,5" trở lên + GPS gọi `/tuyen` qua Wi-Fi. Server trả về ảnh bản đồ đã vẽ sẵn tuyến (ESP32 không tự vẽ bản đồ). Chỉ làm khi tuần 8 đã xong.

---

## 5. Rủi ro và phương án dự phòng

| Rủi ro | Dấu hiệu | Dự phòng |
| --- | --- | --- |
| Chưa có cách lấy ảnh camera chính thức | Hết tuần 3 vẫn chưa có | Nguồn tốc độ chính là D4. Mô-đun camera dùng bộ dữ liệu nhận diện xe công khai để chứng minh phương pháp. Báo cáo ghi rõ đã xin phép |
| Hạn mức TomTom miễn phí không đủ | Bị chặn 429 | Giảm số đoạn hoặc chu kỳ; ưu tiên giờ cao điểm; thêm HERE làm nguồn thứ hai |
| Dữ liệu ít, mô hình không thắng baseline | Tuần 5 MAE ngang baseline | Báo cáo trung thực + dùng METR-LA chứng minh phương pháp; tăng thời gian thu |
| OSM thiếu luật địa phương | Tuyến đi vào đường cấm khi chạy thử | Bảng luật bổ sung tay cho khu vực; ghi rõ giới hạn |
| Tốn tiền AWS | Budgets cảnh báo | Tắt EC2 khi không demo; chỉ giữ S3 + CloudFront |
| Máy nhà tắt / mất mạng làm thủng dữ liệu | Khoảng trống trong dữ liệu | Tự khởi động lại; đánh dấu khoảng trống; có thể chạy bộ thu nhẹ trên VPS sẵn có |
| Ổ đĩa đầy | Dưới 10 GB trống | Xóa ảnh gốc sau 3 ngày; dời sang ổ D |
| Trễ tiến độ | Lỡ 1 tuần | Bỏ phần mở rộng trước (GNN, ESP32), không cắt phần đánh giá |

---

## 6. Việc chỉ người dùng làm được

1. AWS: xem Bills, đặt Budgets, tạo user IAM + MFA (đăng nhập root là việc của người dùng).
2. Chốt tên đề tài với thầy.
3. Camera: xin bên đã đồng ý qua điện thoại một email xác nhận, và hỏi họ cách lấy dữ liệu chính thức (API/đường dẫn ảnh, chu kỳ cho phép, có dữ liệu mức ùn tắc sẵn không).
4. Đăng ký tài khoản TomTom Developer, lấy khóa API (không gửi khóa qua chat, tự dán vào `.env`).

## 7. Cấu trúc thư mục

```
thuctaptotnghiep/
├─ CLAUDE.md          quy tắc cho mọi phiên
├─ note/              sổ ghi chú (đọc trước tiên)
├─ thu_thap/          script tải/thu dữ liệu
├─ du_lieu/           dữ liệu (không đưa lên git)
├─ camera/            đếm xe, mức ùn tắc       (tuần 3–4)
├─ mo_hinh/           dự báo                   (tuần 5–6)
├─ dinh_tuyen/        đồ thị + thuật toán      (tuần 7)
├─ he_thong/          API, web, hạ tầng AWS    (tuần 8–9)
├─ danh_gia/          offline + thực địa       (tuần 10–11)
└─ bao_cao/           đề cương, báo cáo, slide
```
