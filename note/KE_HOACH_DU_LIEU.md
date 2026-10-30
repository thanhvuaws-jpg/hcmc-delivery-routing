# Kế hoạch dữ liệu: thu thập → tiền xử lý → khai phá → bộ dữ liệu sạch

Lập 29/10/2026. Mục tiêu: gộp mọi nguồn (lịch sử 2020–2021 + thời gian thực từ 29/10/2026) thành MỘT bộ dữ liệu sạch, chuẩn, có kiểm định, dùng cho mô hình dự báo và định tuyến. Mọi quyết định ở đây chưa thành QĐ cho tới khi chạy thử và đo được.

---

## 0. Nguyên tắc (người dùng chốt 29/10/2026)

1. **Phần lõi trước:** thu thập → tiền xử lý → khai phá → học máy/học sâu. Giao diện/web để kế hoạch sau.
2. **Ưu tiên độ mới:** dữ liệu thời gian thực đang thu (2026) là trung tâm. Dữ liệu gần đây xếp sau, lâu năm (2020–21) xếp cuối. Dữ liệu cũ dùng để học "kiểu kẹt" lâu dài và làm tiền huấn luyện, không được lấn át dữ liệu mới. Khi gộp, cho trọng số giảm dần theo tuổi dữ liệu, và kiểm định luôn trên dữ liệu MỚI NHẤT.
3. **Cào hết cái có ích (đúng giấy phép), xử lý sau:** dữ liệu gốc vào tầng đồng, không sửa. Mọi xử lý tái lập được bằng script.
4. **Chính xác là đo được:** mỗi bước làm sạch/bù thiếu/mô hình phải có con số kiểm định (che dữ liệu, chia theo thời gian), so với mốc đơn giản. Không tuyên bố "tốt hơn" khi chưa đo.
5. **Ghi hết vào `note/`.**

## 1. Kho dữ liệu hiện có

| Mã | Nguồn | Thời gian | Hạt (không gian / thời gian) | Giấy phép | Vai trò |
|---|---|---|---|---|---|
| D1 | OpenStreetMap (Overpass) | ảnh chụp 29/10/2026 | đường + nút + luật | ODbL | Khung không gian chung (đồ thị xe máy, ~28k cạnh có hướng) |
| D2 | Open-Meteo lưu trữ | 01/2020 → nay (mở rộng 30/10/2026) | 5 điểm / giờ | CC BY 4.0 | Đặc trưng thời tiết lịch sử |
| D3 | Open-Meteo dự báo | 29/10/2026 → (mỗi giờ) | 5 điểm / giờ, 48 giờ tới | CC BY 4.0 | Thời tiết "đúng như lúc dự báo" cho mô hình chạy thật |
| D4 | TomTom Traffic Flow | 29/10/2026 → (5 phút/lần) | ~28k cạnh / 5 phút | Evaluation | **Nhãn + đặc trưng chính** (tỉ lệ tốc độ) |
| D10 | TomTom Incidents | 29/10/2026 → (5 phút/lần) | sự cố (đường gấp khúc) / 5 phút | Evaluation | Tín hiệu báo kẹt sớm; loại "ngap" |
| D11 | Kaggle — ĐH Bách Khoa TP.HCM | 03/07/2020 → 22/04/2021 | ~10k đoạn (mã nút OSM) / báo cáo rời + LOS 30 phút | CC0 | Lịch sử dài; so sánh 2020–21 với 2026; tiền huấn luyện |
| D12 | TomTom Traffic Index TP.HCM 2025 | năm 2025 | toàn thành phố / năm | trích dẫn | Đối chiếu số tự đo (kẹt TB 46,9%; cao điểm chiều 14,8 km/h) |
| D13 | Zenodo HCM_1000 V2 (**bạc xong 30/10**: `bac_zenodo.py`) | công bố 02/10/2026 | 4 × 1.000 điểm giao hàng + kho, khung giờ, ma trận thời gian/khoảng cách | ODbL / CC BY / MIT | **Điểm đi–đến thật để đánh giá định tuyến giao hàng**; ma trận = mốc so sánh |
| D8 | Điểm ngập CSGT TP.HCM (83 do mưa + 39 do triều) | 06/10/2026 | điểm / đoạn | dữ kiện công bố trên báo | **Chép xong 30/10** (`thu_thap/chep_tay/`), ghép 30 điểm → 2.127 cạnh (`bac_ngap.py`). Phạt ngập khi mưa |
| D14 | Lịch: ngày lễ, Tết, cuối tuần, đợt COVID, ngày đi học | 2020 → 2027 | ngày | tự lập | **Xong 30/10** (`xu_ly/lich.py`). Cờ ngày đặc biệt; loại/gắn nhãn giai đoạn bất thường |
| D15 | TomTom Flow kiểu `absolute` | 30/10/2026 04:11 → (5 phút, chỉ bộ thu AWS) | ~28k cạnh / 5 phút | Evaluation | **km/h thật** (bước 5 km/h) → thời gian đi qua cạnh, tốc độ đường trống mỗi cạnh |
| D16 | OSM điểm thu hút giao thông (trường, chợ, bệnh viện, TTTM, trạm buýt) | ảnh chụp khi tải | điểm | ODbL | Đặc trưng tĩnh mỗi cạnh: mật độ/khoảng cách tới trường, chợ… (`tai_osm.py poi`) |
| D9 | METR-LA (207 cảm biến Los Angeles) + PEMS-BAY (325 cảm biến vùng Vịnh) — **tải 30/10** vào `du_lieu/metr_la/` | 03–06/2012; 01–06/2017 | cảm biến / 5 phút | phát hành kèm repo DCRNN (mã MIT; dữ liệu không ghi giấy phép riêng → chỉ dùng nghiên cứu, không phát tán lại) | **Bộ chuẩn có số công bố**: kiểm đường ống dự báo + mô hình học sâu (`mo_hinh/chuan_metr_la.py`, `hoc_sau.py`) trong lúc dữ liệu TP.HCM còn ít ngày |

### Khảo sát nhanh D11 (29/10/2026)

- `segment_status`: 90.938 báo cáo tốc độ, 10.027 đoạn. Giờ lưu UTC ("Z") → đổi sang giờ VN.
- **Bất thường cần xử lý:**
  - **Phân bố tháng lệch:** 08/2020 có 37.457 báo cáo, 12/2020 có 30.836, 02/2021 chỉ 1.
  - **Khung 7h có 31.576 báo cáo**, 6h có 8.126, các giờ khác ~2–5 nghìn. Nghi nhập hàng loạt.
  - **Tốc độ tối đa 200 km/h**, phi thực tế.
- `max_velocity` là **tốc độ giới hạn biển báo**, KHÔNG phải tốc độ đường trống → không dùng thẳng làm mẫu số.
- Không trùng đợt phong tỏa 09/07–30/09/2021. Có trùng đợt dịch thứ hai (07–09/2020): gắn cờ, phân tích độ nhạy.
- Khớp đồ thị: 4.005/10.027 đoạn có cả hai nút trong khu vực; 2.425 khớp đúng một cạnh. Phần còn lại nối bằng đường đi ngắn giữa hai nút.

---

## 2. Kiến trúc dữ liệu: ba tầng (medallion)

```
du_lieu/
  dong/      (bronze) — dữ liệu GỐC, KHÔNG BAO GIỜ sửa:
             tomtom/tho, tomtom/su_co, thoi_tiet*, kaggle_hcmc, zenodo_hcm1000, ban_do
  bac/       (silver) — đã làm sạch + chuẩn hóa, cùng khóa (cạnh, thời điểm), có cột cờ chất lượng
  vang/      (gold)   — bảng đặc trưng cho mô hình: cạnh × khung 15 phút × đặc trưng + nhãn
  bao_cao/   báo cáo chất lượng dữ liệu mỗi ngày (HTML/PNG)
```

- **Không sửa tầng đồng:** mọi bước sau tái lập được từ đồng bằng script (`xu_ly/`). Sai thì sửa script, chạy lại.
- **Parquet** phân vùng theo ngày. Mỗi tệp silver/gold ghi siêu dữ liệu: phiên bản đồ thị, mã commit script, thời điểm tạo (truy vết nguồn gốc).
- **Lên AWS (tuần 9):** cùng cấu trúc trên S3. Truy vấn bằng Athena (phần "khai phá dữ liệu trên cloud" của đề tài hybrid).

---

## 3. Chuẩn hóa (đưa mọi nguồn về một hệ quy chiếu)

### 3.1 Không gian: khóa chung = cạnh cố định của đồ thị xe máy

| Nguồn | Cách đưa về cạnh |
|---|---|
| D4 TomTom Flow | Đã làm: lấy mẫu 10 m, gần ≤ 15 m, lệch hướng ≤ 35° (96,1% mẫu trong khu vực khớp). Thêm: bỏ cạnh có `phu_m` < 30% chiều dài cạnh. |
| D10 Incidents | Cùng thuật toán ghép. Mỗi sự cố → tập cạnh + vị trí trên tuyến (đầu/cuối hàng kẹt). |
| D11 Kaggle | Mã nút là mã OSM. (1) Hai nút kề nhau → đúng cạnh đó, đúng chiều s→e. (2) Không kề → đường đi ngắn nhất giữa hai nút, chấp nhận nếu dài ≤ 1,5 × `length` của họ. (3) Nút đã bị xóa khỏi OSM → ghép hình học (như TomTom) theo toạ độ trong `nodes.csv`. |
| D2/D3 Thời tiết | Mỗi cạnh lấy điểm thời tiết gần nhất (Voronoi 5 điểm). Lưới thời tiết thô, nên ghi rõ giới hạn. |
| D8 Điểm ngập | Tên đường + đoạn → tập cạnh (khớp tên OSM + chặn đầu/cuối); cờ `de_ngap_mua`, `de_ngap_trieu`. |
| D13 Điểm giao hàng | Mỗi điểm → nút gần nhất trong thành phần liên thông lớn nhất (như `BanDo.nut_gan_nhat`). |

### 3.2 Thời gian

- Mọi thời điểm về **giờ Việt Nam, không múi giờ** (Kaggle đang là UTC).
- Hạt gốc 5 phút (TomTom) → tầng bạc giữ 5 phút; tầng vàng **15 phút** (đủ mịn cho dự báo 15/30/60 phút, đỡ nhiễu). So với Kaggle thì gộp lên 30 phút.
- Lịch D14: thứ, cuối tuần, ngày lễ, Tết (± 7 ngày), giờ cao điểm, đợt COVID.

### 3.3 Giá trị: một thang chung

- **Đại lượng chuẩn:** `r` = tốc độ hiện tại / tốc độ đường trống của chính cạnh đó (0–1, có thể > 1).
  - TomTom cho sẵn `r`.
  - Kaggle chỉ có km/h: ước lượng tốc độ đường trống mỗi cạnh = phân vị 85 của tốc độ quan sát ngoài giờ cao điểm (cần ≥ 10 báo cáo; ít hơn thì lấy theo loại đường). Kiểm chứng trên các cạnh có cả hai nguồn: so `r` Kaggle (2020–21) với `r` TomTom (2026) cùng khung giờ.
- **Mức rời rạc (nhãn phân loại):** thông (r ≥ 0,75) / đông (0,4–0,75) / kẹt (< 0,4). Thêm bảng ánh xạ sang LOS A–F (theo tỉ lệ tốc độ đường trống của HCM 2010 cho đường đô thị) để so với nhãn LOS của Kaggle.
- **Định nghĩa "kẹt xe" chính thức TP.HCM** (< 5 km/h liên tục > 30 phút, hàng xe ≥ 200 m) dùng làm nhãn "kẹt nghiêm trọng" thứ tư khi có km/h.

---

## 4. Làm sạch: phát hiện → GẮN CỜ, không xóa thầm lặng

Mỗi dòng ở tầng bạc có cột `co_chat_luong` (bitmask) để mô hình và báo cáo biết dòng nào bị nghi ngờ.

| # | Lỗi | Cách phát hiện | Xử lý |
|---|---|---|---|
| L1 | Ngoài miền giá trị | km/h > 80 hoặc < 0; r > 1,5 | Cờ + loại khỏi huấn luyện |
| L2 | Trùng lặp | cùng cạnh, cùng thời điểm (±60 s), cùng giá trị | Gộp |
| L3 | Nhập hàng loạt (Kaggle 6–7h) | Đếm báo cáo/phút trên toàn mạng; đỉnh bất thường so với phân phối theo giờ (z-score của số báo cáo/phút > 4); nhiều đoạn cùng giây | Cờ `nghi_nhap_hang_loat`; huấn luyện có/không để đo ảnh hưởng |
| L4 | Nhảy bất thường theo thời gian | **Bộ lọc Hampel** mỗi cạnh: trung vị trượt ± 3 × MAD (cửa sổ 1 giờ) | Cờ; thay bằng trung vị nếu là điểm đơn lẻ |
| L5 | Bất thường đa chiều | **Isolation Forest** trên (giờ, thứ, loại đường, r, thời tiết, sự cố) | Cờ để xem tay; không tự xóa |
| L6 | Khoảng trống thu thập (máy tắt/ngủ) | Lượt chụp liền nhau cách > 10 phút | Bảng `khoang_trong`; không nội suy qua khoảng > 30 phút |
| L7 | Ghép kém | `phu_m` < 30% chiều dài cạnh; cạnh khớp nhiều đoạn TomTom mâu thuẫn (độ lệch r > 0,3) | Cờ; trọng số thấp |
| L8 | Giai đoạn bất thường | Lịch D14 (COVID, Tết, bão lớn) | Cờ `giai_doan`; phân tích độ nhạy |

---

## 5. Bù dữ liệu thiếu (impute)

Thiếu theo hai kiểu, xử lý khác nhau:

1. **Thiếu theo thời gian** (một cạnh mất vài lượt chụp): nội suy tuyến tính nếu ≤ 15 phút. Dài hơn thì để trống + cờ (mô hình học được việc thiếu).
2. **Thiếu theo không gian** (cạnh không bao giờ có dữ liệu — hẻm, residential): thử và **so bằng kiểm định che dữ liệu** (che ngẫu nhiên 10% giá trị đã biết, xem cách nào đoán gần nhất):
   - (a) Hồ sơ theo loại đường × giờ × thứ: mốc đơn giản.
   - (b) **Lan truyền trên đồ thị** (graph Laplacian smoothing / label propagation): lấy từ cạnh lân cận có dữ liệu, giảm theo khoảng cách.
   - (c) **Hoàn thiện ma trận hạng thấp** (cạnh × thời gian, SVD/ALS): khai thác việc các con đường kẹt theo vài "kiểu" chung.
   - (d) Mở rộng nếu kịp: mạng nơ-ron đồ thị cho bù dữ liệu (họ GRIN/SPIN).
   - Chọn cách có sai số kiểm định thấp nhất, ghi số liệu vào báo cáo.

---

## 6. Khai phá dữ liệu (data mining): câu hỏi → kỹ thuật → kết quả cho báo cáo

| # | Câu hỏi | Kỹ thuật | Đầu ra |
|---|---|---|---|
| M1 | Kẹt lúc nào, ở đâu? | Thống kê mô tả; bản đồ nhiệt giờ × thứ | Biểu đồ giờ cao điểm thật của khu trung tâm |
| M2 | Điểm nóng ùn tắc có ý nghĩa thống kê? | **Getis-Ord Gi\*** / **Local Moran's I** trên đồ thị cạnh (tự tương quan không gian) | Bản đồ điểm nóng/điểm lạnh, mức ý nghĩa p |
| M3 | Đường nào "kẹt giống nhau"? | Phân cụm chuỗi hồ sơ ngày (k-means trên hồ sơ chuẩn hóa; DTW + phân cụm phân cấp) | Các nhóm đường: kẹt sáng / kẹt chiều / kẹt cả ngày / thông |
| M4 | Kẹt lặp lại hay bất thường? | **Phân rã STL** (xu hướng + mùa ngày/tuần + phần dư); phần dư lớn ghép với sự cố/mưa | Tỉ lệ kẹt "thường ngày" và kẹt "do sự cố/mưa" |
| M5 | Kẹt lan ra sao? | Tương quan chéo có độ trễ giữa cạnh thượng–hạ nguồn; **Granger causality** | Tốc độ lan kẹt (phút/km) — cơ sở cho đặc trưng lân cận |
| M6 | Mưa / sự cố làm kẹt thêm bao nhiêu? | So sánh có điều kiện (cùng cạnh, cùng giờ, mưa và không mưa); **luật kết hợp** (sự cố ⇒ kẹt trong 30 phút, support/confidence/lift) | Con số "mưa > 5 mm/h làm r giảm X%" |
| M7 | 2020–21 và 2026 khác nhau thế nào? | So `r` theo cạnh/giờ giữa D11 và D4 trên cạnh chung; kiểm định thống kê | "Giao thông trung tâm sau 5 năm" — mục phân tích riêng |
| M8 | Số tự đo có đáng tin? | So với D12 (TomTom Index 2025) | Bảng đối chiếu trong báo cáo |
| M9 | Tuyến ngắn nhất có hay bị kẹt? | Trên điểm giao hàng D13: tỉ lệ tuyến ngắn nhất đi qua cạnh kẹt theo giờ | Số liệu cho phần "vấn đề" (tiếp nối con số 85/90) |

---

## 7. Đặc trưng cho mô hình (tầng vàng)

- **Thời gian:** sin/cos giờ trong ngày và thứ trong tuần; cuối tuần; lễ/Tết; cao điểm.
- **Trễ:** r ở t−5, −10, −15, −30, −60 phút; trung bình/độ lệch chuẩn trượt 30 và 60 phút; r cùng giờ hôm qua và tuần trước.
- **Lân cận đồ thị:** trung bình r của cạnh thượng nguồn/hạ nguồn trong 1–2 bước, có trọng số khoảng cách (từ M5).
- **Thời tiết:** mưa hiện tại và mưa DỰ BÁO (D3, đúng thứ có lúc chạy thật), xác suất mưa, cờ dễ ngập × mưa.
- **Sự cố:** số sự cố, tổng độ trễ, khoảng cách tới sự cố gần nhất ở thượng nguồn trong 2 km; loại (kẹt/đóng đường/công trình/ngập).
- **Tĩnh:** loại đường, chiều dài, một chiều, số làn (nếu OSM có), cụm từ M3.
- **Nhãn:** r ở t+15, t+30, t+60 (hồi quy) và mức thông/đông/kẹt (phân loại).

## 8. Chia dữ liệu và chống rò rỉ

- **Chia theo thời gian, không chia ngẫu nhiên:** train = các tuần đầu, validation = tuần kế, test = 2 tuần cuối. Giữ riêng 1–2 tuần cho "chạy thử ảo" (tuần 11).
- Đặc trưng chỉ dùng thông tin **trước** thời điểm dự báo. Thời tiết tương lai chỉ được lấy từ DỰ BÁO (D3), không lấy từ thời tiết thật.
- Chuẩn hóa (mean/std) học trên train rồi áp sang validation/test.

## 9. Kiểm soát chất lượng

- Kiểm tra lược đồ mỗi tầng: tên cột, kiểu, miền giá trị, khóa không trùng.
- Báo cáo chất lượng mỗi ngày: % lượt chụp thành công, % cạnh có dữ liệu theo loại đường, số cờ L1–L8, khoảng trống.
- Kiểm thử cho từng hàm biến đổi (dữ liệu giả nhỏ, kết quả biết trước), giống `kiem_tra_tuan1.py`.

## 10. Lịch làm (khớp `KE_HOACH.md`)

| Tuần | Việc dữ liệu |
|---|---|
| 3 (đang làm) | Ghép D11 vào cạnh; lịch D14; khảo sát + phát hiện L3 trong D11 |
| 4 | Tầng bạc cho D4, D10, D11, D2/D3; cờ L1–L8; D8 điểm ngập; báo cáo chất lượng ngày; M1, M2, M4 |
| 5 | Tầng vàng 15 phút; bù dữ liệu thiếu (so 4 cách); M3, M5, M6, M7, M8 |
| 6 | Cập nhật tầng vàng với dữ liệu mới; ablation dùng các nhóm đặc trưng |
| 9–10 | Đưa tầng đồng/bạc/vàng lên S3 + Athena; M9 trên điểm giao hàng D13 |
